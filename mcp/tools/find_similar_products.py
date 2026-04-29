from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_database, get_driver

CYPHER = """
MATCH (p:Product {product_id: $pid})
OPTIONAL MATCH (p)-[r:SIMILAR_TO]->(s:Product)
WHERE $merchant_id IS NULL OR EXISTS { MATCH (m:Merchant {merchant_id: $merchant_id})-[:OWNS]->(s) }
RETURN s.product_id AS product_id, s.name AS name, r.score AS score
ORDER BY score DESC LIMIT $k
"""


def run(caller: Caller, *, product_id: str, top_k: int = 10) -> dict:
    with get_driver().session(database=get_database()) as s:
        rs = s.run(CYPHER, pid=product_id, merchant_id=caller.tenant_merchant_id, k=top_k)
        return {"results": [dict(r) for r in rs]}
