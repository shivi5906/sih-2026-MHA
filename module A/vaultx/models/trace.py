from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from .transaction import Chain


class StopReason(Enum):
    """Why the trace stopped at a particular address."""
    LABELED = auto()        # label_fn returned a label (e.g., exchange)
    MAX_HOPS = auto()       # depth limit reached
    TAINT_BELOW = auto()    # taint fraction dropped below threshold
    FETCH_FAILED = auto()   # API call failed — trace incomplete here
    NO_OUTFLOWS = auto()    # address has no outgoing txs — trail ends
    TIMEOUT = auto()        # global time budget exhausted
    FANOUT_LIMITED = auto() # too many outgoing txs, only top-N traced


@dataclass
class TraceConfig:
    """Configuration for a specific trace operation."""
    max_hops: int = 10
    max_duration_seconds: int = 300
    min_taint_fraction: Decimal = Decimal('0.001')
    min_value_native: Decimal = Decimal('0.0001')
    max_fanout: int = 100
    max_addresses: int = 1000
    chains_to_trace: Optional[List[Chain]] = None


@dataclass
class TraceHop:
    """A single hop in a trace path."""
    from_address: str
    to_address: str
    tx_id: str
    value_native: Decimal
    taint_amount: Decimal
    taint_fraction: Decimal
    hop_number: int
    chain: Chain
    timestamp: int


@dataclass
class TraceLeaf:
    """A terminal point in the trace tree and why the trace stopped there."""
    address: str
    reason: StopReason
    label: Optional[str] = None          # from label_fn, if any
    arriving_hop: Optional[TraceHop] = None  # the hop that reached this leaf
    error_detail: Optional[str] = None   # for FETCH_FAILED


@dataclass
class TraceResult:
    """The result of a tracing operation."""
    start_address: str
    chain: Chain
    hops: List[TraceHop]
    leaves: List[TraceLeaf]
    total_hops: int
    duration_seconds: float
    terminated_reason: str
    # graph is set by the engine after construction; optional to avoid
    # circular import at module level (TraceGraph imports TraceHop).
    graph: Any = None
