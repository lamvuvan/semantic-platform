from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_database, get_driver

CYPHER = """
MATCH (c:Customer {customer_id: $cid})-[:PLACED]->(o:Order)
WHERE o.ts > datetime() - duration({days: $days})
OPTIONAL MATCH (o)-[:HAS_LINE]->(l:OrderLine)-[:OF_PRODUCT]->(p:Product)
RETURN o.order_id AS order_id, o.ts AS ts, o.total AS total,
       collect(DISTINCT {product_id: p.product_id, name: p.name}) AS products
ORDER BY ts DESC
"""


def run(caller: Caller, *, customer_id: str, days: int = 90) -> dict:
    with get_driver().session(database=get_database()) as s:
        rs = s.run(CYPHER, cid=customer_id, days=days)
        return {"orders": [dict(r) for r in rs]}
