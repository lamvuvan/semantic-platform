"""Unit test logic chọn transport — không cần boot FastMCP/server thật."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_resolve_transport():
    """Import `_resolve_transport` từ mcp/server.py mà không trigger heavy deps.

    Stub fastmcp + jsonschema + jwt + một số module khác để cô lập đơn vị test.
    """
    stubs = {
        "fastmcp": _make_fastmcp_stub,
        "jsonschema": _make_jsonschema_stub,
        "jwt": _make_jwt_stub,
    }
    for name, factory in stubs.items():
        if name not in sys.modules:
            sys.modules[name] = factory()

    spec = importlib.util.spec_from_file_location(
        "mcp.server_under_test",
        Path(__file__).resolve().parents[2] / "mcp" / "server.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module._resolve_transport


def _make_fastmcp_stub() -> types.ModuleType:
    mod = types.ModuleType("fastmcp")

    class _FakeFastMCP:
        def __init__(self, *_, **__): ...
        def tool(self, *_, **__):
            def deco(fn): return fn
            return deco
        def run(self, *_, **__): ...

    mod.FastMCP = _FakeFastMCP
    return mod


def _make_jsonschema_stub() -> types.ModuleType:
    mod = types.ModuleType("jsonschema")
    mod.validate = lambda **_: None  # type: ignore[attr-defined]
    return mod


def _make_jwt_stub() -> types.ModuleType:
    """Stub đủ surface mà mcp.auth.oidc dùng: jwt.decode, jwt.PyJWKClient, jwt.PyJWTError."""
    mod = types.ModuleType("jwt")

    class _PyJWTError(Exception):
        pass

    class _PyJWKClient:
        def __init__(self, *_, **__): ...
        def get_signing_key_from_jwt(self, *_): ...

    mod.PyJWTError = _PyJWTError
    mod.PyJWKClient = _PyJWKClient
    mod.decode = lambda *a, **k: {}  # type: ignore[attr-defined]
    return mod


resolve = _load_resolve_transport()


@pytest.mark.parametrize("env", [None, "", "stdio", "STDIO", " stdio "])
def test_default_is_stdio(env):
    assert resolve(env) == "stdio"


@pytest.mark.parametrize("env", ["http", "HTTP", "streamable-http", "streamable_http", " Streamable-HTTP "])
def test_http_aliases_map_to_streamable_http(env):
    assert resolve(env) == "streamable-http"


@pytest.mark.parametrize("env", ["sse", "websocket", "tcp", "garbage"])
def test_unsupported_transports_raise(env):
    with pytest.raises(ValueError, match="MCP_TRANSPORT"):
        resolve(env)
