from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_database, get_driver

CYPHER = """
MATCH (p:Product {product_id: $pid})
WHERE $merchant_id IS NULL OR EXISTS { MATCH (m:Merchant {merchant_id: $merchant_id})-[:OWNS]->(p) }
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(v:ProductVariant)
OPTIONAL MATCH (p)-[:OFFERS_TOPPING]->(t:Topping)
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
RETURN p, collect(DISTINCT v) AS variants, collect(DISTINCT t) AS toppings, collect(DISTINCT c) AS categories
"""


def run(caller: Caller, *, product_id: str) -> dict:
    with get_driver().session(database=get_database()) as s:
        rec = s.run(CYPHER, pid=product_id, merchant_id=caller.tenant_merchant_id).single()
        if rec is None:
            return {"product": None}
        return {
            "product": dict(rec["p"]),
            "variants": [dict(v) for v in rec["variants"] if v is not None],
            "toppings": [dict(t) for t in rec["toppings"] if t is not None],
            "categories": [dict(c) for c in rec["categories"] if c is not None],
        }
