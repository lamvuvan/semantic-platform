from __future__ import annotations

from agents.recommender.topping import recommend
from mcp.auth.oidc import Caller
from mcp.tools._deps import get_database, get_driver


def run(caller: Caller, *, product_id: str, customer_id: str | None = None, top_k: int = 10) -> dict:
    results = recommend(
        get_driver(),
        get_database(),
        product_id=product_id,
        customer_id=customer_id,
        k=top_k,
    )
    return {"results": results}
