from __future__ import annotations

from pydantic import BaseModel, Field

from mcp_server.middleware.auth import AgentIdentity
from mcp_server.tools._helpers import trusted_headers


class Input(BaseModel):
    customer_id: str = Field(..., min_length=1)
    days: int = Field(90, ge=1, le=365)


async def run(identity: AgentIdentity, *, domain_client, raw: dict) -> dict:
    args = Input(**raw)
    return await domain_client.get(
        f"/v1/customers/{args.customer_id}",
        headers=trusted_headers(identity),
        params={"days": args.days},
    )
