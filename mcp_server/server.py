"""Layer 4 — MCP Tool Server (FastMCP, Streamable HTTP).

Trách nhiệm:
- Verify JWT của AI agent → AgentIdentity (sub, merchant_id, scopes).
- Load surface theo agent_id từ surfaces.yaml — chỉ expose tool đúng vai trò.
- Pydantic input validation cho mọi tool.
- Tenant scope: BẮT BUỘC merchant_id từ JWT, KHÔNG nhận từ body.
- Rate limit per (agent, merchant, tool) qua Redis.
- Audit log JSON cho mọi call.
- Gọi Domain Service qua mTLS, KHÔNG truy vấn DB trực tiếp.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastmcp import FastMCP

from mcp_server.agents.registry import AgentSurface, ToolSpec, load_surfaces
from mcp_server.domain_client import DomainClient
from mcp_server.middleware.audit import audit
from mcp_server.middleware.auth import AgentIdentity, AuthError, JwtVerifier, require_scopes
from mcp_server.middleware.ratelimit import RateLimit, RateLimiter

logger = logging.getLogger("mcp.server")

mcp = FastMCP(name="semantic-platform-kg")
_VERIFIER: JwtVerifier | None = None
_DOMAIN: DomainClient | None = None
_RATE: RateLimiter | None = None


def _get_verifier() -> JwtVerifier:
    global _VERIFIER
    if _VERIFIER is None:
        _VERIFIER = JwtVerifier()
    return _VERIFIER


def _resolve_identity(headers: dict[str, str] | None) -> AgentIdentity:
    if headers is None:
        token = os.environ.get("MCP_DEV_TOKEN")
        if not token:
            raise AuthError("no auth context (stdio dev mode requires MCP_DEV_TOKEN)")
        return _get_verifier().verify(token)
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise AuthError("missing bearer token")
    return _get_verifier().verify(auth.split(" ", 1)[1].strip())


def _make_tool(surface: AgentSurface, spec: ToolSpec):
    """Wrap 1 tool implementation thành MCP tool — tên unique theo (agent, tool)."""
    qualified_name = f"{surface.agent_id}__{spec.name}"

    @mcp.tool(name=qualified_name, description=f"[{surface.agent_id}] {spec.name}")
    async def _tool(headers: dict[str, str] | None = None, **raw: Any) -> dict:
        identity = _resolve_identity(headers)
        # Agent isolation: mỗi token chỉ dùng surface đúng agent_id của nó.
        if identity.agent_id != surface.agent_id:
            raise AuthError(f"agent {identity.agent_id} không khớp surface {surface.agent_id}")
        require_scopes(identity, surface.scopes_required)
        assert _RATE is not None and _DOMAIN is not None
        await _RATE.check(
            agent_id=identity.agent_id,
            merchant_id=identity.merchant_id,
            tool=spec.name,
            limit=RateLimit(requests_per_minute=surface.rate_limit_rpm),
        )
        with audit(tool=spec.name, agent_id=identity.agent_id, merchant_id=identity.merchant_id, params=raw):
            return await spec.handler(identity, domain_client=_DOMAIN, raw=raw)

    return _tool


def register_all() -> None:
    surfaces = load_surfaces()
    total = 0
    for surface in surfaces.values():
        for spec in surface.tools.values():
            _make_tool(surface, spec)
            total += 1
    logger.info("registered %s qualified tools across %s agents", total, len(surfaces))


_HTTP_TRANSPORT_ALIASES = {"http", "streamable-http", "streamable_http"}


def _resolve_transport(env_value: str | None) -> str:
    raw = (env_value or "stdio").strip().lower()
    if raw == "stdio":
        return "stdio"
    if raw in _HTTP_TRANSPORT_ALIASES:
        return "streamable-http"
    raise ValueError(f"unsupported MCP_TRANSPORT={env_value!r}")


async def _startup() -> None:
    global _DOMAIN, _RATE
    _DOMAIN = DomainClient()
    await _DOMAIN.startup()
    _RATE = RateLimiter()
    await _RATE.startup()


async def _shutdown() -> None:
    if _DOMAIN is not None:
        await _DOMAIN.shutdown()
    if _RATE is not None:
        await _RATE.shutdown()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    register_all()
    transport = _resolve_transport(os.environ.get("MCP_TRANSPORT"))
    if transport == "streamable-http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8080"))
        path = os.environ.get("MCP_PATH", "/mcp")
        mcp.run(transport="streamable-http", host=host, port=port, path=path,
                on_startup=[_startup], on_shutdown=[_shutdown])
    else:
        mcp.run(transport="stdio", on_startup=[_startup], on_shutdown=[_shutdown])


if __name__ == "__main__":
    main()
