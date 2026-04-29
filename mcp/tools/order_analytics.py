from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_database, get_driver

QUERIES = {
    "revenue": """
        MATCH (m:Merchant {merchant_id: $mid})<-[:PLACED_AT]-(o:Order)
        WHERE ($from IS NULL OR o.ts >= datetime($from))
          AND ($to IS NULL OR o.ts <= datetime($to))
        RETURN sum(o.total) AS value
    """,
    "qty": """
        MATCH (m:Merchant {merchant_id: $mid})<-[:PLACED_AT]-(o:Order)-[:HAS_LINE]->(l:OrderLine)
        WHERE ($from IS NULL OR o.ts >= datetime($from))
          AND ($to IS NULL OR o.ts <= datetime($to))
        RETURN sum(coalesce(l.qty, 1)) AS value
    """,
    "top_products": """
        MATCH (m:Merchant {merchant_id: $mid})<-[:PLACED_AT]-(o:Order)-[:HAS_LINE]->(l:OrderLine)-[:OF_PRODUCT]->(p:Product)
        WHERE ($from IS NULL OR o.ts >= datetime($from))
          AND ($to IS NULL OR o.ts <= datetime($to))
        RETURN p.product_id AS product_id, p.name AS name, sum(coalesce(l.qty, 1)) AS qty
        ORDER BY qty DESC LIMIT 10
    """,
    "top_toppings": """
        MATCH (m:Merchant {merchant_id: $mid})<-[:PLACED_AT]-(o:Order)-[:HAS_LINE]->(l:OrderLine)-[:WITH_TOPPING]->(t:Topping)
        WHERE ($from IS NULL OR o.ts >= datetime($from))
          AND ($to IS NULL OR o.ts <= datetime($to))
        RETURN t.topping_id AS topping_id, t.name AS name, sum(coalesce(l.qty, 1)) AS qty
        ORDER BY qty DESC LIMIT 10
    """,
}


def run(caller: Caller, *, merchant_id: str, metric: str, date_from: str | None = None, date_to: str | None = None) -> dict:
    if caller.tenant_merchant_id and caller.tenant_merchant_id != merchant_id:
        raise PermissionError("merchant_id mismatch with token claim")
    cypher = QUERIES[metric]
    with get_driver().session(database=get_database()) as s:
        rs = s.run(cypher, mid=merchant_id, **{"from": date_from, "to": date_to})
        rows = [dict(r) for r in rs]
    return {"metric": metric, "rows": rows}
