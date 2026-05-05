"""Test logic chọn transport — không boot server thật."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load():
    if "fastmcp" not in sys.modules:
        m = types.ModuleType("fastmcp")
        class _F:
            def __init__(self, *_, **__): ...
            def tool(self, *_, **__):
                def deco(fn): return fn
                return deco
            def run(self, *_, **__): ...
        m.FastMCP = _F
        sys.modules["fastmcp"] = m
    if "jwt" not in sys.modules:
        j = types.ModuleType("jwt")
        class _Err(Exception): ...
        j.PyJWTError = _Err
        j.PyJWKClient = lambda *_, **__: None
        j.decode = lambda *_, **__: {}
        sys.modules["jwt"] = j
    if "httpx" not in sys.modules:
        sys.modules["httpx"] = types.ModuleType("httpx")
    if "redis" not in sys.modules:
        redis_mod = types.ModuleType("redis")
        sys.modules["redis"] = redis_mod
        async_mod = types.ModuleType("redis.asyncio")
        sys.modules["redis.asyncio"] = async_mod

    spec = importlib.util.spec_from_file_location(
        "mcp_server_test_server",
        Path(__file__).resolve().parents[2] / "mcp_server" / "server.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod._resolve_transport


resolve = _load()


@pytest.mark.parametrize("env", [None, "", "stdio", "STDIO"])
def test_stdio_default(env):
    assert resolve(env) == "stdio"


@pytest.mark.parametrize("env", ["http", "streamable-http", "streamable_http", " STREAMABLE-HTTP "])
def test_http_aliases(env):
    assert resolve(env) == "streamable-http"


@pytest.mark.parametrize("env", ["sse", "ws", "tcp"])
def test_unsupported(env):
    with pytest.raises(ValueError):
        resolve(env)
