from __future__ import annotations
import pytest
from decimal import Decimal
from vaultx.models.transaction import Chain
from vaultx.models.trace import TraceConfig, StopReason
from vaultx.tracing.engine import TracingEngine
from vaultx.exchanges.known import is_exchange


@pytest.mark.asyncio
async def test_ethereum_trace_finds_exchange(eth_adapter, trace_config):
    """End-to-end: trace from suspect should reach Binance within 3 hops."""
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, trace_config, label_fn=is_exchange)
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    # Should have found Binance via leaves
    labeled_leaves = [l for l in result.leaves if l.reason == StopReason.LABELED]
    assert len(labeled_leaves) > 0
    labels = {l.label for l in labeled_leaves}
    assert 'Binance' in labels
    assert result.total_hops > 0
    assert result.terminated_reason == 'completed'


@pytest.mark.asyncio  
async def test_ethereum_trace_hop_limit(eth_adapter):
    """With max_hops=1, trace should NOT reach the exchange (it's 3 hops away)."""
    config = TraceConfig(
        max_hops=1,
        max_duration_seconds=300,
        min_taint_fraction=Decimal('0.001'),
        min_value_native=Decimal('0.0001')
    )
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, config, label_fn=is_exchange)
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    # Binance is 3 hops away, should not be found with max_hops=1
    labeled_leaves = [l for l in result.leaves if l.reason == StopReason.LABELED]
    labels = {l.label for l in labeled_leaves}
    assert 'Binance' not in labels


@pytest.mark.asyncio
async def test_trace_preserves_taint_fractions(eth_adapter, trace_config):
    """Verify taint fractions are reasonable (between 0 and 1) throughout trace."""
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, trace_config, label_fn=is_exchange)
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    for hop in result.hops:
        assert Decimal('0') <= hop.taint_fraction <= Decimal('1')
        assert hop.taint_amount >= Decimal('0')
        assert hop.value_native > Decimal('0')


@pytest.mark.asyncio
async def test_trace_without_label_fn(eth_adapter, trace_config):
    """Without label_fn, engine traces through everything — no LABELED leaves."""
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, trace_config)  # no label_fn
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    labeled_leaves = [l for l in result.leaves if l.reason == StopReason.LABELED]
    assert len(labeled_leaves) == 0
    # Should still have hops
    assert result.total_hops > 0


@pytest.mark.asyncio
async def test_trace_returns_graph(eth_adapter, trace_config):
    """TraceResult should include the populated graph."""
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, trace_config, label_fn=is_exchange)
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    assert result.graph is not None
    assert result.graph.node_count > 0
    assert result.graph.edge_count > 0


@pytest.mark.asyncio
async def test_trace_leaves_have_stop_reasons(eth_adapter, trace_config):
    """Every leaf should have a valid StopReason."""
    adapters = {Chain.ETHEREUM: eth_adapter}
    engine = TracingEngine(adapters, trace_config, label_fn=is_exchange)
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    for leaf in result.leaves:
        assert isinstance(leaf.reason, StopReason)
        if leaf.reason == StopReason.LABELED:
            assert leaf.label is not None
        if leaf.reason == StopReason.FETCH_FAILED:
            assert leaf.error_detail is not None
