"""Tests for Phase 2-7 features: outflow tracking, fan-out limits, token
transfers, checksum validation, MultiDiGraph, tree output, co-spend metadata."""
from __future__ import annotations
import pytest
from decimal import Decimal

from vaultx.models.transaction import Chain, TxType
from vaultx.models.trace import TraceConfig, StopReason
from vaultx.tracing.taint import TaintTracker
from vaultx.tracing.graph import TraceGraph
from vaultx.tracing.engine import TracingEngine
from vaultx.exchanges.known import is_exchange
from vaultx.chains.detection import (
    verify_eth_checksum, verify_base58check, verify_bech32,
)
from vaultx.models.trace import TraceHop


# ── Phase 2: Taint outflow tracking ─────────────────────────────────────────

def test_outflow_deducts_taint():
    """After an outgoing tx, remaining taint fraction should stay the same
    (proportional model) but remaining taint *amount* should decrease."""
    t = TaintTracker()
    t.record_incoming('A', Decimal('100'), Decimal('50'))  # 50% tainted

    # First outflow of 40 → carries 20 taint
    amt1, frac1 = t.calculate_outgoing_taint('A', Decimal('40'))
    assert frac1 == Decimal('0.5')
    assert amt1 == Decimal('20')

    # After spending 40, remaining balance=60, remaining taint=30 → still 50%
    assert t.get_remaining_balance('A') == Decimal('60')
    assert t.get_remaining_taint('A') == Decimal('30')

    # Second outflow of 60 → carries 30 taint (rest of taint budget)
    amt2, frac2 = t.calculate_outgoing_taint('A', Decimal('60'))
    assert frac2 == Decimal('0.5')
    assert amt2 == Decimal('30')

    # Balance should be exhausted
    assert t.get_remaining_balance('A') == Decimal('0')
    assert t.get_remaining_taint('A') == Decimal('0')


def test_taint_conservation_invariant():
    """Total taint out should never exceed total taint in."""
    t = TaintTracker()
    t.record_incoming('A', Decimal('100'), Decimal('100'))  # fully tainted

    # Spend 60, then 60 (total 120 > balance of 100)
    t.calculate_outgoing_taint('A', Decimal('60'))
    t.calculate_outgoing_taint('A', Decimal('60'))

    # taint_spent is clamped to tainted_amount
    assert t.get_remaining_taint('A') >= Decimal('0')


def test_get_total_received():
    t = TaintTracker()
    assert t.get_total_received('X') == Decimal('0')
    t.record_incoming('X', Decimal('10'), Decimal('5'))
    assert t.get_total_received('X') == Decimal('10')
    t.record_incoming('X', Decimal('20'), Decimal('0'))
    assert t.get_total_received('X') == Decimal('30')


# ── Phase 3: Fan-out and priority ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_fanout_limit(eth_adapter):
    """With max_fanout=1, only the highest-value outgoing tx should be traced."""
    config = TraceConfig(
        max_hops=10,
        max_fanout=1,  # Only follow 1 outgoing tx per address
        min_taint_fraction=Decimal('0.001'),
        min_value_native=Decimal('0.0001'),
    )
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, config, label_fn=is_exchange)

    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM,
    )

    # 0xbbb has 2 outgoing txs (3 ETH + 2 ETH), with max_fanout=1 only
    # the 3 ETH tx should be followed.  Check we have a FANOUT_LIMITED leaf.
    fanout_leaves = [l for l in result.leaves if l.reason == StopReason.FANOUT_LIMITED]
    # 0xbbb should appear as fanout-limited since it had >1 outgoing
    assert len(fanout_leaves) >= 1


@pytest.mark.asyncio
async def test_max_addresses_limit(eth_adapter):
    """With max_addresses=2, engine should stop after visiting 2 addresses."""
    config = TraceConfig(
        max_hops=10,
        max_addresses=2,
        min_taint_fraction=Decimal('0.0001'),
        min_value_native=Decimal('0.00001'),
    )
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, config, label_fn=is_exchange)

    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM,
    )

    assert result.terminated_reason == 'max_addresses'


# ── Phase 5: Address checksum verification ──────────────────────────────────

def test_eth_checksum_valid():
    """Known Binance hot-wallet with correct EIP-55 checksum."""
    assert verify_eth_checksum('0x28C6c06298d514Db089934071355E5743bf21d60') is True


def test_eth_checksum_lowercase_passes():
    """All-lowercase (no checksum info) should pass."""
    assert verify_eth_checksum('0x28c6c06298d514db089934071355e5743bf21d60') is True


def test_eth_checksum_invalid_format():
    assert verify_eth_checksum('0x123') is False
    assert verify_eth_checksum('not_an_address') is False


def test_base58check_valid_bitcoin():
    """Real Bitcoin P2SH address with valid checksum."""
    assert verify_base58check('34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo') is True


def test_base58check_invalid():
    """Mangled address should fail checksum."""
    assert verify_base58check('34xp4vRoCGJym3xR7yCVPFHoCNxv4TwsXX') is False


def test_bech32_valid():
    """Real Bech32 address."""
    assert verify_bech32('bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h') is True


def test_bech32_invalid():
    """Fixture address with invalid bech32 checksum should fail."""
    assert verify_bech32('bc1qsuspect11111111111111111111111111111') is False


# ── Phase 6: MultiDiGraph + tree output ─────────────────────────────────────

def _make_hop(from_addr, to_addr, tx_id='tx1', value=Decimal('1'),
              taint=Decimal('1'), fraction=Decimal('1'), hop=1, ts=1000):
    return TraceHop(
        from_address=from_addr,
        to_address=to_addr,
        tx_id=tx_id,
        value_native=value,
        taint_amount=taint,
        taint_fraction=fraction,
        hop_number=hop,
        chain=Chain.ETHEREUM,
        timestamp=ts
    )


def test_multigraph_preserves_parallel_edges():
    """Two txs between the same pair should both be stored."""
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B', tx_id='tx1'))
    graph.add_hop(_make_hop('A', 'B', tx_id='tx2'))

    assert graph.node_count == 2
    assert graph.edge_count == 2  # two parallel edges

    edges = graph.get_edge_data('A', 'B')
    assert len(edges) == 2
    tx_ids = {e['tx_id'] for e in edges}
    assert tx_ids == {'tx1', 'tx2'}


def test_to_tree_basic():
    """Tree should be a nested dict with addresses and edges."""
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B', tx_id='tx1'))
    graph.add_hop(_make_hop('B', 'C', tx_id='tx2', hop=2))
    graph.mark_exchange('C', 'Binance')

    tree = graph.to_tree('A')

    assert tree['address'] == 'A'
    assert len(tree['edges']) == 1
    child_b = tree['edges'][0]['child']
    assert child_b['address'] == 'B'
    assert len(child_b['edges']) == 1
    child_c = child_b['edges'][0]['child']
    assert child_c['address'] == 'C'
    assert child_c['is_exchange'] is True
    assert child_c['label'] == 'Binance'


def test_to_tree_handles_cycles():
    """Cycles should be detected and not cause infinite recursion."""
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B', tx_id='tx1'))
    graph.add_hop(_make_hop('B', 'A', tx_id='tx2', hop=2))  # back-edge

    tree = graph.to_tree('A')
    child_b = tree['edges'][0]['child']
    # B links back to A, which should be marked as cycle
    back_edge = child_b['edges'][0]['child']
    assert back_edge['address'] == 'A'
    assert back_edge['edges'] == '(cycle)'


# ── Phase 7: Bitcoin co-spend metadata ──────────────────────────────────────

@pytest.mark.asyncio
async def test_bitcoin_co_spend_metadata(btc_adapter):
    """Each normalized BTC tx should include co-spent addresses in metadata."""
    txs = await btc_adapter.get_transactions('bc1qsuspect11111111111111111111111111111')

    for tx in txs:
        assert tx.metadata is not None, f"metadata missing on {tx.tx_id}"
        co_spent = tx.metadata.get('co_spent_addresses')
        assert co_spent is not None, f"co_spent_addresses missing on {tx.tx_id}"
        assert isinstance(co_spent, list)
        # Every input address should be in the co-spent list
        assert tx.from_address in co_spent


@pytest.mark.asyncio
async def test_bitcoin_single_input_co_spend(btc_adapter):
    """For a 1-input tx, co_spent_addresses should be a list with just that input."""
    txs = await btc_adapter.get_transactions('bc1qsuspect11111111111111111111111111111')

    # btc_tx2 has 1 input (the suspect address) → co_spent should be [suspect]
    btc_tx2_txs = [t for t in txs if t.raw_tx_id == 'btc_tx2']
    for tx in btc_tx2_txs:
        assert len(tx.metadata['co_spent_addresses']) == 1


# ── Phase 4: Token field presence on native txs ─────────────────────────────

@pytest.mark.asyncio
async def test_native_txs_have_none_token_fields(eth_adapter):
    """Native ETH transfers should have None token fields."""
    txs = await eth_adapter.get_transactions('0xaaa1111111111111111111111111111111111111')
    for tx in txs:
        if tx.tx_type == TxType.TRANSFER:
            assert tx.token_contract is None
            assert tx.token_symbol is None
            assert tx.token_decimals is None


@pytest.mark.asyncio
async def test_tron_native_txs_no_token_fields(tron_adapter):
    """Native TRX transfers should have None token fields."""
    txs = await tron_adapter.get_transactions('TRXcKoEvHr6Y38VMcDYGBEYKznvH3XUX4g')
    for tx in txs:
        if tx.tx_type == TxType.TRANSFER:
            assert tx.token_contract is None
            assert tx.token_symbol is None
            assert tx.token_decimals is None
