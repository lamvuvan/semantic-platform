from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_retriever


def run(caller: Caller, *, customer_id: str) -> dict:
    ctx = get_retriever().retrieve(intent="customer_360", entity_ids=[customer_id])
    return {
        "summary": ctx.summaries,
        "subgraph": ctx.subgraph,
        "freshness_ts": ctx.freshness_ts,
    }
