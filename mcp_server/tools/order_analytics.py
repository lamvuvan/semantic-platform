from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from mcp_server.middleware.auth import AgentIdentity
from mcp_server.tools._helpers import trusted_headers


class Input(BaseModel):
    metric: str = Field(..., pattern="^(revenue|qty|top_products|top_toppings)$")
    date_from: date | None = None
    date_to: date | None = None


async def run(identity: AgentIdentity, *, domain_client, raw: dict) -> dict:
    args = Input(**raw)
    payload = args.model_dump()
    if payload.get("date_from"):
        payload["date_from"] = payload["date_from"].isoformat()
    if payload.get("date_to"):
        payload["date_to"] = payload["date_to"].isoformat()
    # Endpoint analytics có thể bổ sung ở Domain Service ở P3 — placeholder gọi chung.
    return await domain_client.post(
        "/v1/analytics/orders",
        headers=trusted_headers(identity),
        json=payload,
    )
