from __future__ import annotations

from pydantic import BaseModel, Field

from mcp_server.middleware.auth import AgentIdentity
from mcp_server.tools._helpers import trusted_headers


class Input(BaseModel):
    customer_id: str = Field(..., min_length=1)
    days: int = Field(90, ge=1, le=365)


async def run(identity: AgentIdentity, *, domain_client, raw: dict) -> dict:
    """Order history piggyback trên customer endpoint của Domain Service."""
    args = Input(**raw)
    profile = await domain_client.get(
        f"/v1/customers/{args.customer_id}",
        headers=trusted_headers(identity),
        params={"days": args.days},
    )
    return {
        "customer_id": profile["customer_id"],
        "order_count": profile.get("order_count", 0),
        "gmv": profile.get("gmv", 0.0),
        "top_products": profile.get("top_products", []),
        "top_toppings": profile.get("top_toppings", []),
        "request_id": profile.get("request_id"),
    }
