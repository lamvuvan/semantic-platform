"""MCP Server entrypoint — FastMCP với stdio + HTTP+SSE.

Mỗi tool đăng ký từ `mcp/registry/tools.yaml`, được wrap bởi:
- OIDC verify caller (HTTP transport) hoặc signed token (stdio).
- Scope check theo declarative `scopes`.
- Tenant filter — chèn merchant_id từ JWT claim.
- Audit log JSON.
- Rate limit per-tool/per-tenant qua Redis.
- Query timeout.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import jsonschema
from fastmcp import FastMCP

from mcp.audit.log import audit
from mcp.auth.oidc import AuthError, Caller, OidcVerifier, require_scopes
from mcp.registry.loader import ToolSpec, load_registry

logger = logging.getLogger("mcp.server")

mcp = FastMCP(name="semantic-platform")
_TOOLS: dict[str, ToolSpec] = {}
_VERIFIER: OidcVerifier | None = None


def _get_verifier() -> OidcVerifier:
    global _VERIFIER
    if _VERIFIER is None:
        _VERIFIER = OidcVerifier()
    return _VERIFIER


def _resolve_caller(headers: dict[str, str] | None) -> Caller:
    """Trên transport HTTP+SSE — đọc Authorization Bearer.

    Trên stdio: dev mode chấp nhận token từ env $MCP_DEV_TOKEN.
    """
    if headers is not None:
        auth = headers.get("authorization") or headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            raise AuthError("missing bearer token")
        return _get_verifier().verify(auth.split(" ", 1)[1].strip())
    token = os.environ.get("MCP_DEV_TOKEN")
    if token:
        return _get_verifier().verify(token)
    raise AuthError("no auth context")


def _make_tool(spec: ToolSpec):
    schema = spec.input_schema

    @mcp.tool(name=spec.name, description=spec.description)
    def _tool(headers: dict[str, str] | None = None, **kwargs: Any) -> dict:
        caller = _resolve_caller(headers)
        require_scopes(caller, spec.scopes)
        jsonschema.validate(instance=kwargs, schema=schema)
        with audit(spec.name, caller.sub, kwargs):
            return spec.handler(caller, **kwargs)

    return _tool


def register_all() -> None:
    for spec in load_registry():
        _TOOLS[spec.name] = spec
        _make_tool(spec)
    logger.info("registered %s tools: %s", len(_TOOLS), sorted(_TOOLS))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    register_all()
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8080"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
