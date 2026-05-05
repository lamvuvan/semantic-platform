"""Helpers chung cho mọi tool: build trusted headers gửi xuống Domain Service."""
from __future__ import annotations

import uuid

from mcp_server.middleware.auth import AgentIdentity


def trusted_headers(identity: AgentIdentity, request_id: str | None = None) -> dict[str, str]:
    return {
        "x-agent-id":    identity.agent_id,
        "x-merchant-id": identity.merchant_id,
        "x-scopes":      " ".join(sorted(identity.scopes)),
        "x-request-id":  request_id or str(uuid.uuid4()),
    }
