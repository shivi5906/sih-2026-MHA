from __future__ import annotations
import time
import logging
from typing import Callable, Optional
from decimal import Decimal
import heapq

from vaultx.models.trace import TraceConfig, TraceHop, TraceLeaf, TraceResult, StopReason
from vaultx.models.transaction import Chain
from vaultx.chains.base import ChainAdapter
from vaultx.chains.detection import detect_chain
from vaultx.tracing.taint import TaintTracker
from vaultx.tracing.graph import TraceGraph

logger = logging.getLogger(__name__)

# Unique counter for heap tie-breaking (heapq needs total ordering)
_counter = 0


def _next_counter() -> int:
    global _counter
    _counter += 1
    return _counter


class TracingEngine:
    """BFS Forward Tracing Engine for analyzing flow of funds on blockchain.
    
    The engine produces FACTS: normalised transactions, a graph, traced paths,
    and honest stop-points with reasons.  It does NOT produce verdicts (e.g.
    "this is Binance") — that is Track B's job.
    
    An optional *label_fn* can be injected to mark addresses that should be
    treated as terminal (e.g. known exchange hot-wallets).  The engine records
    the label on the resulting ``TraceLeaf`` but does not interpret it.
    """
    
    def __init__(
        self,
        adapters: dict[Chain, ChainAdapter],
        config: TraceConfig | None = None,
        label_fn: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the tracing engine.
        
        Args:
            adapters: Dictionary mapping Chain enum to instantiated ChainAdapters.
            config: Trace configuration limits.
            label_fn: Optional callable that takes an address and returns a label
                      string (e.g. "Binance") if the address is known, or None.
                      Labeled addresses are treated as terminal.
        """
        self.adapters = adapters
        self.config = config or TraceConfig()
        self.label_fn = label_fn
        
    async def trace(
        self, 
        start_address: str, 
        initial_value: Decimal | None = None, 
        chain: Chain | None = None,
        on_progress: Callable[[int, str, int, int], None] | None = None
    ) -> TraceResult:
        """Perform a priority-ordered forward trace starting from a given address.
        
        Args:
            start_address: The address to begin tracing from.
            initial_value: The initial tainted value. If None, uses total received.
            chain: The chain the address belongs to. If None, will attempt to detect.
            on_progress: Optional callback(hop_num, address, total_txs, outgoing_txs).
            
        Returns:
            A TraceResult containing the trace path, leaves, graph, and metadata.
        """
        if chain is None:
            chain = detect_chain(start_address)
            if chain is None:
                raise ValueError(f"Could not detect chain for address {start_address}")
                
        tracker = TaintTracker()
        graph = TraceGraph()
        
        # Priority queue: (-taint_amount, counter, address, taint_fraction, hop_number, after_timestamp)
        # Negative taint_amount so highest-taint items come first.
        heap: list[tuple[float, int, str, Decimal, int, int]] = []
        heapq.heappush(heap, (0.0, _next_counter(), start_address, Decimal('1.0'), 0, 0))
        
        # Visited tracking to prevent infinite loops
        visited: set[str] = set()
        
        start_time = time.time()
        terminated_reason = "completed"
        leaves: list[TraceLeaf] = []
        hops: list[TraceHop] = []
        
        if initial_value is not None:
            tracker.record_incoming(start_address, initial_value, initial_value)
            
        while heap:
            elapsed = time.time() - start_time
            if elapsed > self.config.max_duration_seconds:
                terminated_reason = "timeout"
                logger.warning(f"Trace timeout after {elapsed:.2f}s")
                # Mark remaining queued addresses as TIMEOUT leaves
                while heap:
                    _, _, addr, _, _, _ = heapq.heappop(heap)
                    if addr not in visited:
                        leaves.append(TraceLeaf(address=addr, reason=StopReason.TIMEOUT))
                break
            
            if len(visited) >= self.config.max_addresses:
                terminated_reason = "max_addresses"
                while heap:
                    _, _, addr, _, _, _ = heapq.heappop(heap)
                    if addr not in visited:
                        leaves.append(TraceLeaf(address=addr, reason=StopReason.MAX_HOPS))
                break
                
            neg_taint, _, address, current_taint_fraction, hop_num, after_ts = heapq.heappop(heap)
            
            if address in visited:
                continue
                
            if hop_num > self.config.max_hops:
                leaves.append(TraceLeaf(address=address, reason=StopReason.MAX_HOPS))
                continue
                
            if current_taint_fraction < self.config.min_taint_fraction:
                leaves.append(TraceLeaf(address=address, reason=StopReason.TAINT_BELOW))
                continue
                
            visited.add(address)
            
            # Check label_fn (injected by caller — e.g. exchange lookup)
            label = self.label_fn(address) if self.label_fn else None
            if label:
                graph.mark_labeled(address, label)
                leaves.append(TraceLeaf(address=address, reason=StopReason.LABELED, label=label))
                # Don't trace into labeled addresses
                continue

            adapter = self.adapters.get(chain)
            if not adapter:
                logger.error(f"No adapter found for chain {chain}")
                leaves.append(TraceLeaf(
                    address=address, reason=StopReason.FETCH_FAILED,
                    error_detail=f"No adapter for chain {chain}"
                ))
                continue
                
            try:
                txs = await adapter.get_transactions(address)
            except Exception as e:
                logger.warning(f"Failed to get transactions for {address}: {e}")
                leaves.append(TraceLeaf(
                    address=address, reason=StopReason.FETCH_FAILED,
                    error_detail=str(e)
                ))
                continue
            
            # --- Taint accounting: use ALL incoming txs we already fetched ---
            # This gives accurate total_received at zero extra API cost.
            if hop_num == 0 and initial_value is None:
                incoming_txs = [tx for tx in txs if tx.direction(address) == 'incoming']
                total_incoming = sum((tx.value_native for tx in incoming_txs), Decimal('0'))
                tracker.record_incoming(address, total_incoming, total_incoming)
            elif hop_num > 0:
                # For intermediate addresses, record clean (non-traced) inflows
                # so the taint fraction reflects the real ratio.
                incoming_txs = [tx for tx in txs if tx.direction(address) == 'incoming']
                total_incoming = sum((tx.value_native for tx in incoming_txs), Decimal('0'))
                already_recorded = tracker.get_total_received(address)
                clean_delta = total_incoming - already_recorded
                if clean_delta > Decimal('0'):
                    tracker.record_incoming(address, clean_delta, Decimal('0'))
                
            # Filter and sort outgoing
            outgoing_txs = [
                tx for tx in txs 
                if tx.direction(address) == 'outgoing' and tx.timestamp > after_ts
            ]
            outgoing_txs.sort(key=lambda x: x.timestamp)
            
            if on_progress:
                on_progress(hop_num, address, len(txs), len(outgoing_txs))
            
            if not outgoing_txs:
                if hop_num > 0:
                    leaves.append(TraceLeaf(address=address, reason=StopReason.NO_OUTFLOWS))
                continue
            
            # Fan-out limiting: trace only top-N by value
            fanout_limited = False
            if len(outgoing_txs) > self.config.max_fanout:
                outgoing_txs.sort(key=lambda x: x.value_native, reverse=True)
                outgoing_txs = outgoing_txs[:self.config.max_fanout]
                fanout_limited = True
            
            children_enqueued = 0
            for tx in outgoing_txs:
                if tx.value_native < self.config.min_value_native:
                    continue
                    
                taint_amount_carried, new_taint_fraction = tracker.calculate_outgoing_taint(
                    address, tx.value_native
                )
                
                if new_taint_fraction < self.config.min_taint_fraction:
                    continue
                    
                hop = TraceHop(
                    from_address=address,
                    to_address=tx.to_address,
                    tx_id=tx.tx_id,
                    value_native=tx.value_native,
                    taint_amount=taint_amount_carried,
                    taint_fraction=new_taint_fraction,
                    hop_number=hop_num + 1,
                    chain=chain,
                    timestamp=tx.timestamp
                )
                
                graph.add_hop(hop)
                hops.append(hop)
                
                tracker.record_incoming(tx.to_address, tx.value_native, taint_amount_carried)
                
                # Check label on destination
                dest_label = self.label_fn(tx.to_address) if self.label_fn else None
                if dest_label:
                    graph.mark_labeled(tx.to_address, dest_label)
                    leaves.append(TraceLeaf(
                        address=tx.to_address, reason=StopReason.LABELED,
                        label=dest_label, arriving_hop=hop
                    ))
                    visited.add(tx.to_address)
                    # Do not enqueue — labeled address is terminal
                else:
                    if tx.to_address not in visited:
                        heapq.heappush(heap, (
                            -float(taint_amount_carried),
                            _next_counter(),
                            tx.to_address,
                            new_taint_fraction,
                            hop_num + 1,
                            tx.timestamp
                        ))
                        children_enqueued += 1
                        
            if fanout_limited:
                leaves.append(TraceLeaf(
                    address=address, reason=StopReason.FANOUT_LIMITED
                ))
                        
        duration = time.time() - start_time
        result = TraceResult(
            start_address=start_address,
            chain=chain,
            hops=hops,
            leaves=leaves,
            total_hops=len(hops),
            duration_seconds=duration,
            terminated_reason=terminated_reason,
            graph=graph,
        )
        return result
