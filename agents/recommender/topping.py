"""Topping recommender: kết hợp co-purchase + similarity."""
from __future__ import annotations

from neo4j import Driver

CO_PURCHASE = """
MATCH (p:Product {product_id: $pid})<-[:OF_PRODUCT]-(:OrderLine)<-[:HAS_LINE]-(o:Order)-[:HAS_LINE]->(l:OrderLine)-[:WITH_TOPPING]->(t:Topping)
WITH t, count(DISTINCT o) AS cnt
RETURN t.topping_id AS topping_id, t.name AS name, cnt
ORDER BY cnt DESC LIMIT $k
"""

PERSONAL_BIAS = """
MATCH (c:Customer {customer_id: $cid})-[:PLACED]->(o:Order)-[:HAS_LINE]->(:OrderLine)-[:WITH_TOPPING]->(t:Topping)
WITH t, count(*) AS personal
RETURN t.topping_id AS topping_id, personal
"""


def recommend(driver: Driver, database: str, product_id: str, customer_id: str | None = None, k: int = 10) -> list[dict]:
    with driver.session(database=database) as s:
        co = {r["topping_id"]: dict(r) for r in s.run(CO_PURCHASE, pid=product_id, k=k * 2)}
        if customer_id:
            for r in s.run(PERSONAL_BIAS, cid=customer_id):
                if r["topping_id"] in co:
                    co[r["topping_id"]]["personal"] = int(r["personal"])
    ranked = sorted(
        co.values(),
        key=lambda x: (x.get("personal", 0) * 0.4) + (int(x["cnt"]) * 0.6),
        reverse=True,
    )
    return ranked[:k]
