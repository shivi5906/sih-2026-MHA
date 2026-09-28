from __future__ import annotations
import json
import networkx as nx
from typing import Any
from vaultx.models.trace import TraceHop

class TraceGraph:
    """Graph representation of a trace, allowing path finding and analysis.
    
    Uses a MultiDiGraph so multiple transfers between the same address pair
    are preserved (e.g. A sends to B twice in different transactions).
    """
    
    def __init__(self) -> None:
        """Initialize an empty directed multi-graph."""
        self.graph = nx.MultiDiGraph()
        
    def add_hop(self, hop: TraceHop) -> None:
        """Add a TraceHop to the graph as edge and nodes.
        
        Args:
            hop: The TraceHop to add.
        """
        # Ensure nodes exist with some attributes
        if not self.graph.has_node(hop.from_address):
            self.graph.add_node(hop.from_address, is_exchange=False, chain=hop.chain.value if hop.chain else None)
            
        if not self.graph.has_node(hop.to_address):
            self.graph.add_node(hop.to_address, is_exchange=False, chain=hop.chain.value if hop.chain else None)
            
        # Add edge (MultiDiGraph allows duplicates between same pair)
        self.graph.add_edge(
            hop.from_address, 
            hop.to_address,
            key=hop.tx_id,
            tx_id=hop.tx_id,
            value_native=float(hop.value_native),
            taint_amount=float(hop.taint_amount),
            taint_fraction=float(hop.taint_fraction),
            timestamp=hop.timestamp,
            hop_number=hop.hop_number
        )
        
    def mark_exchange(self, address: str, exchange_name: str) -> None:
        """Mark a specific node as a known exchange.
        
        Args:
            address: The address to mark.
            exchange_name: The name of the exchange.
        """
        self.mark_labeled(address, exchange_name)
            
    def mark_labeled(self, address: str, label: str) -> None:
        """Mark a node with a label (e.g. exchange name, service name).
        
        This is the generic version used by the engine.  The label is stored
        as both ``label`` and ``exchange_name`` (for backward compat).
        
        Args:
            address: The address to mark.
            label: The label string.
        """
        if self.graph.has_node(address):
            self.graph.nodes[address]['is_exchange'] = True
            self.graph.nodes[address]['exchange_name'] = label
            self.graph.nodes[address]['label'] = label
        else:
            self.graph.add_node(address, is_exchange=True, exchange_name=label, label=label)
            
    def shortest_path(self, source: str, target: str) -> list[str]:
        """Find the shortest path between two addresses.
        
        Args:
            source: Starting address.
            target: Destination address.
            
        Returns:
            List of addresses forming the shortest path, or empty list if no path.
        """
        try:
            return nx.shortest_path(self.graph, source=source, target=target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
            
    def paths_to_exchanges(self, source: str) -> dict[str, list[list[str]]]:
        """Find all paths from source to any known exchange nodes.
        
        Args:
            source: Starting address.
            
        Returns:
            Dictionary mapping exchange names to lists of paths.
        """
        result: dict[str, list[list[str]]] = {}
        if not self.graph.has_node(source):
            return result
            
        exchange_nodes = [
            n for n, attr in self.graph.nodes(data=True)
            if attr.get('is_exchange')
        ]
        
        for ex_node in exchange_nodes:
            ex_name = self.graph.nodes[ex_node].get('exchange_name', 'Unknown')
            if ex_name not in result:
                result[ex_name] = []
                
            try:
                paths = list(nx.all_simple_paths(self.graph, source, ex_node))
                result[ex_name].extend(paths)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass
                
        return result
        
    def get_edge_data(self, from_addr: str, to_addr: str) -> list[dict[str, Any]]:
        """Get all edge attributes between two nodes.
        
        Returns a list of edge-data dicts (one per parallel edge).
        """
        if self.graph.has_edge(from_addr, to_addr):
            edge_dict = self.graph[from_addr][to_addr]
            return [dict(data) for data in edge_dict.values()]
        return []
        
    def get_node_data(self, address: str) -> dict[str, Any]:
        """Get attributes for a specific node."""
        if self.graph.has_node(address):
            return dict(self.graph.nodes[address])
        return {}
    
    def to_tree(self, root: str) -> dict[str, Any]:
        """Return a nested dict representing the trace tree from *root*.
        
        Each node in the tree has:
        - ``address``: the wallet address
        - ``label``: exchange/service label if any, else None
        - ``edges``: list of outgoing edges, each with ``tx_id``, ``value``,
          ``taint_amount``, ``taint_fraction``, and ``child`` (recursive tree)
        
        Visited-set prevents cycles from producing infinite recursion.
        """
        visited: set[str] = set()
        
        def _build(addr: str) -> dict[str, Any]:
            visited.add(addr)
            node_data = self.get_node_data(addr) or {}
            node: dict[str, Any] = {
                "address": addr,
                "label": node_data.get("label"),
                "is_exchange": node_data.get("is_exchange", False),
                "edges": [],
            }
            if addr not in self.graph:
                return node
                
            for _, to_addr, data in self.graph.out_edges(addr, data=True):
                edge_entry: dict[str, Any] = {
                    "tx_id": data.get("tx_id", ""),
                    "value": data.get("value_native", 0),
                    "taint_amount": data.get("taint_amount", 0),
                    "taint_fraction": data.get("taint_fraction", 0),
                    "hop_number": data.get("hop_number", 0),
                }
                if to_addr not in visited:
                    edge_entry["child"] = _build(to_addr)
                else:
                    # Back-edge / already visited — just reference
                    to_data = self.get_node_data(to_addr) or {}
                    edge_entry["child"] = {
                        "address": to_addr,
                        "label": to_data.get("label"),
                        "is_exchange": to_data.get("is_exchange", False),
                        "edges": "(cycle)",
                    }
                node["edges"].append(edge_entry)
            return node
        
        return _build(root)
        
    def to_json(self) -> str:
        """Serialize graph to JSON string."""
        data = nx.node_link_data(self.graph)
        return json.dumps(data)
        
    @classmethod
    def from_json(cls, data: str) -> TraceGraph:
        """Deserialize graph from JSON string."""
        parsed = json.loads(data)
        g = nx.node_link_graph(parsed)
        instance = cls()
        instance.graph = g
        return instance
        
    def save(self, filepath: str) -> None:
        """Save graph to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
            
    @classmethod
    def load(cls, filepath: str) -> TraceGraph:
        """Load graph from file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = f.read()
        return cls.from_json(data)
        
    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()
        
    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()
        
    def summary(self) -> str:
        """Return a human-readable multi-line summary of the graph."""
        lines = []
        lines.append("Trace Graph Summary:")
        lines.append(f"Total Nodes: {self.node_count}")
        lines.append(f"Total Edges: {self.edge_count}")
        
        exchange_nodes = [
            (n, attr.get('exchange_name', 'Unknown'))
            for n, attr in self.graph.nodes(data=True)
            if attr.get('is_exchange')
        ]
        
        lines.append(f"Exchanges Found: {len(exchange_nodes)}")
        for n, name in exchange_nodes:
            lines.append(f"  - {name} ({n})")
            
        return "\n".join(lines)
