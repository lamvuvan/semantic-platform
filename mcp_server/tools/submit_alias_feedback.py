from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from mcp_server.middleware.auth import AgentIdentity
from mcp_server.tools._helpers import trusted_headers


class Input(BaseModel):
    surface_text: str = Field(..., min_length=1, max_length=200)
    matched_product_id: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    was_accepted: bool


async def run(identity: AgentIdentity, *, domain_client, raw: dict) -> dict:
    args = Input(**raw)
    payload = args.model_dump()
    payload["submitted_at"] = datetime.now(timezone.utc).isoformat()
    return await domain_client.post(
        "/v1/aliases/feedback",
        headers=trusted_headers(identity),
        json=payload,
    )
