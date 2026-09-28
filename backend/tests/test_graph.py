from __future__ import annotations
import pytest
from decimal import Decimal
from vaultx.models.trace import TraceHop
from vaultx.models.transaction import Chain
from vaultx.tracing.graph import TraceGraph


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


def test_add_hop_creates_nodes_and_edges():
    graph = TraceGraph()
    hop = _make_hop('A', 'B')
    graph.add_hop(hop)
    
    assert graph.node_count == 2
    assert graph.edge_count == 1
    assert graph.get_node_data('A') is not None
    assert graph.get_node_data('B') is not None


def test_mark_exchange():
    graph = TraceGraph()
    hop = _make_hop('A', 'B')
    graph.add_hop(hop)
    graph.mark_exchange('B', 'Binance')
    
    node_data = graph.get_node_data('B')
    assert node_data['is_exchange'] is True
    assert node_data['exchange_name'] == 'Binance'


def test_shortest_path():
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B', tx_id='tx1'))
    graph.add_hop(_make_hop('B', 'C', tx_id='tx2', hop=2))
    
    path = graph.shortest_path('A', 'C')
    assert path == ['A', 'B', 'C']


def test_shortest_path_no_path():
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B'))
    path = graph.shortest_path('B', 'A')  # no reverse path
    assert path == []


def test_paths_to_exchanges():
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B', tx_id='tx1'))
    graph.add_hop(_make_hop('B', 'C', tx_id='tx2', hop=2))
    graph.mark_exchange('C', 'Binance')
    
    paths = graph.paths_to_exchanges('A')
    assert 'Binance' in paths
    assert len(paths['Binance']) == 1
    assert paths['Binance'][0] == ['A', 'B', 'C']


def test_json_roundtrip():
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B'))
    graph.mark_exchange('B', 'Kraken')
    
    json_str = graph.to_json()
    restored = TraceGraph.from_json(json_str)
    
    assert restored.node_count == 2
    assert restored.edge_count == 1


def test_summary_contains_info():
    graph = TraceGraph()
    graph.add_hop(_make_hop('A', 'B'))
    graph.mark_exchange('B', 'Coinbase')
    
    summary = graph.summary()
    assert 'Total Nodes: 2' in summary
    assert 'Total Edges: 1' in summary
    assert 'Coinbase' in summary
