from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_retriever


def run(caller: Caller, *, query: str) -> dict:
    ctx = get_retriever().retrieve(intent="data_discovery", query=query)
    return {"results": ctx.entities, "freshness_ts": ctx.freshness_ts}
