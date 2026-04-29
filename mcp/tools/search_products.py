from __future__ import annotations

from mcp.auth.oidc import Caller
from mcp.tools._deps import get_retriever


def run(caller: Caller, *, query: str, merchant_id: str | None = None, top_k: int = 10) -> dict:
    merchant = merchant_id or caller.tenant_merchant_id
    retriever = get_retriever()
    ctx = retriever.retrieve(intent="search_product", query=query, merchant_id=merchant, params={"top_k": top_k})
    return {
        "results": ctx.entities[:top_k],
        "freshness_ts": ctx.freshness_ts,
    }
