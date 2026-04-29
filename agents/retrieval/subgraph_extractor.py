"""Subgraph extractor: mở rộng từ entity hạt giống theo policy."""
from __future__ import annotations

from dataclasses import dataclass

from neo4j import Driver


@dataclass(frozen=True)
class Subgraph:
    nodes: list[dict]
    edges: list[dict]
    evidence_cypher: str


class SubgraphExtractor:
    def __init__(self, driver: Driver, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    def around_customer(self, customer_id: str, days: int = 90, max_nodes: int = 200) -> Subgraph:
        cypher = """
        MATCH (c:Customer {customer_id: $cid})
        OPTIONAL MATCH (c)-[:PLACED]->(o:Order)
        WHERE o.ts > datetime() - duration({days: $days})
        OPTIONAL MATCH (o)-[:HAS_LINE]->(l:OrderLine)-[:OF_PRODUCT]->(p:Product)
        OPTIONAL MATCH (l)-[:WITH_TOPPING]->(t:Topping)
        WITH c, collect(DISTINCT o) AS orders, collect(DISTINCT p) AS products,
             collect(DISTINCT t) AS toppings, collect(DISTINCT l) AS lines
        RETURN c, orders, products, toppings, lines LIMIT 1
        """
        nodes: list[dict] = []
        edges: list[dict] = []
        with self._driver.session(database=self._database) as s:
            record = s.run(cypher, cid=customer_id, days=days).single()
            if record is None:
                return Subgraph(nodes=[], edges=[], evidence_cypher=cypher)
            nodes.append({"label": "Customer", **dict(record["c"])})
            for o in record["orders"][: max_nodes // 4]:
                nodes.append({"label": "Order", **dict(o)})
            for p in record["products"][: max_nodes // 4]:
                nodes.append({"label": "Product", **dict(p)})
            for t in record["toppings"][: max_nodes // 4]:
                nodes.append({"label": "Topping", **dict(t)})
        return Subgraph(nodes=nodes, edges=edges, evidence_cypher=cypher)

    def around_product(self, product_id: str, depth: int = 2, max_nodes: int = 200) -> Subgraph:
        # Depth được cố định ở 2 cho an toàn (chỉ allowlist 1/2/3).
        if depth not in (1, 2, 3):
            raise ValueError("depth must be 1, 2 or 3")
        cypher = f"""
        MATCH (p:Product {{product_id: $pid}})
        OPTIONAL MATCH path=(p)-[*1..{depth}]-(other)
        WITH p, collect(DISTINCT other)[..$max] AS neighbors
        RETURN p, neighbors
        """
        nodes: list[dict] = []
        with self._driver.session(database=self._database) as s:
            record = s.run(cypher, pid=product_id, max=max_nodes).single()
            if record is None:
                return Subgraph(nodes=[], edges=[], evidence_cypher=cypher)
            nodes.append({"label": "Product", **dict(record["p"])})
            for n in record["neighbors"]:
                nodes.append({"label": list(n.labels)[0] if n.labels else "Unknown", **dict(n)})
        return Subgraph(nodes=nodes, edges=[], evidence_cypher=cypher)
