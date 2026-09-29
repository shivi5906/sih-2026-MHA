from __future__ import annotations
import os
import logging
from neo4j import GraphDatabase, exceptions

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        auth_str = os.getenv("NEO4J_AUTH", "neo4j/vaultx-dev")
        if "/" in auth_str:
            user, password = auth_str.split("/", 1)
        else:
            user, password = "neo4j", "password"
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            self._available = True
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}. Graph operations will be mocked or skipped.")
            self.driver = None
            self._available = False

    def close(self):
        if self.driver:
            self.driver.close()

    def store_trace_graph(self, case_id: str, hops: list, chain: str):
        if not self._available:
            return
        
        try:
            with self.driver.session() as session:
                for hop in hops:
                    session.execute_write(self._merge_hop, case_id, hop, chain)
        except Exception as e:
            logger.warning(f"Failed to store trace graph in Neo4j: {e}")

    @staticmethod
    def _merge_hop(tx, case_id: str, hop, chain: str):
        query = """
        MERGE (from:Address {address: $from_addr, chain: $chain, case_id: $case_id})
        MERGE (to:Address {address: $to_addr, chain: $chain, case_id: $case_id})
        MERGE (from)-[r:SENT_TO {tx_id: $tx_id, case_id: $case_id}]->(to)
        ON CREATE SET r.amount = $amount,
                      r.taint_fraction = $taint,
                      r.hop_number = $hop_number,
                      r.timestamp = $timestamp
        """
        tx.run(query, 
               from_addr=hop.from_address,
               to_addr=hop.to_address,
               chain=chain,
               case_id=case_id,
               tx_id=hop.tx_id,
               amount=str(hop.value_native),
               taint=float(hop.taint_fraction),
               hop_number=hop.hop_number,
               timestamp=hop.timestamp)

    def store_exchange_label(self, address: str, exchange_name: str):
        if not self._available:
            return
        
        query = """
        MATCH (a:Address {address: $address})
        SET a:Exchange, a.exchange_name = $exchange_name
        """
        try:
            with self.driver.session() as session:
                session.run(query, address=address, exchange_name=exchange_name)
        except Exception as e:
            logger.warning(f"Failed to store exchange label in Neo4j: {e}")

    def get_shortest_path(self, from_addr: str, to_addr: str) -> list[dict]:
        if not self._available:
            return []
        
        query = """
        MATCH path = shortestPath((start:Address {address: $from_addr})-[:SENT_TO*..10]->(end:Address {address: $to_addr}))
        RETURN nodes(path) AS nodes, relationships(path) AS rels
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, from_addr=from_addr, to_addr=to_addr).single()
                if not result:
                    return []
                
                nodes = [{"address": n["address"], "chain": n["chain"]} for n in result["nodes"]]
                rels = [{"tx_id": r["tx_id"], "amount": r["amount"], "source": r.start_node["address"], "target": r.end_node["address"]} for r in result["rels"]]
                return [{"nodes": nodes, "edges": rels}]
        except Exception as e:
            logger.warning(f"Failed to get shortest path: {e}")
            return []

    def get_neighborhood(self, address: str, depth: int = 2) -> dict:
        if not self._available:
            return {"nodes": [], "edges": []}
            
        query = """
        MATCH path = (start:Address {address: $address})-[:SENT_TO*1..%d]-(neighbor:Address)
        RETURN nodes(path) AS nodes, relationships(path) AS rels
        """ % depth
        
        try:
            with self.driver.session() as session:
                result = session.run(query, address=address)
                nodes_map = {}
                edges_list = []
                for record in result:
                    for n in record["nodes"]:
                        nodes_map[n["address"]] = dict(n)
                    for r in record["rels"]:
                        edge_id = r["tx_id"]
                        edges_list.append({
                            "id": edge_id,
                            "source": r.start_node["address"],
                            "target": r.end_node["address"],
                            "amount": r.get("amount")
                        })
                
                # Deduplicate edges
                unique_edges = {e["id"]: e for e in edges_list}.values()
                return {"nodes": list(nodes_map.values()), "edges": list(unique_edges)}
        except Exception as e:
            logger.warning(f"Failed to get neighborhood: {e}")
            return {"nodes": [], "edges": []}

    def get_case_graph(self, case_id: str) -> dict:
        if not self._available:
            return {"nodes": [], "edges": []}
            
        query = """
        MATCH (n:Address {case_id: $case_id})
        OPTIONAL MATCH (n)-[r:SENT_TO {case_id: $case_id}]->(m:Address)
        RETURN n, r, m
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, case_id=case_id)
                nodes_map = {}
                edges_map = {}
                for record in result:
                    n = record["n"]
                    if n:
                        nodes_map[n["address"]] = dict(n)
                    
                    r = record["r"]
                    m = record["m"]
                    if r and m:
                        nodes_map[m["address"]] = dict(m)
                        edges_map[r["tx_id"]] = {
                            "id": r["tx_id"],
                            "source": n["address"],
                            "target": m["address"],
                            "amount": r.get("amount"),
                            "chain": n["chain"]
                        }
                return {"nodes": list(nodes_map.values()), "edges": list(edges_map.values())}
        except Exception as e:
            logger.warning(f"Failed to get case graph: {e}")
            return {"nodes": [], "edges": []}

    def find_common_counterparties(self, addr1: str, addr2: str) -> list[str]:
        if not self._available:
            return []
            
        query = """
        MATCH (a1:Address {address: $addr1})-[:SENT_TO|<-[:SENT_TO]-(common:Address)-[:SENT_TO|<-[:SENT_TO]-(a2:Address {address: $addr2})
        RETURN DISTINCT common.address AS address
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, addr1=addr1, addr2=addr2)
                return [record["address"] for record in result]
        except Exception as e:
            logger.warning(f"Failed to find common counterparties: {e}")
            return []


_client = None

def get_neo4j_client() -> Neo4jClient:
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client
