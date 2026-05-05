from __future__ import annotations

from pydantic import BaseModel, Field

from mcp_server.middleware.auth import AgentIdentity
from mcp_server.tools._helpers import trusted_headers


class Input(BaseModel):
    product_id: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)


async def run(identity: AgentIdentity, *, domain_client, raw: dict) -> dict:
    args = Input(**raw)
    return await domain_client.post(
        "/v1/products/search",
        headers=trusted_headers(identity),
        json={"query": args.product_id, "top_k": args.top_k, "mode": "semantic"},
    )
