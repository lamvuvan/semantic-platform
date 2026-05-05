"""Test surface registry: ≤10 tool/agent, scope hợp lệ, handler resolve được."""
from __future__ import annotations

import sys
import types

import pytest


@pytest.fixture(autouse=True)
def _stub_heavy_modules(monkeypatch):
    """Stub những module sẽ chỉ có ở runtime container — test logic load surface độc lập."""
    for mod_name in ("httpx", "fastmcp"):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)
    if not hasattr(sys.modules["fastmcp"], "FastMCP"):
        class _Fake:
            def __init__(self, *_, **__): ...
            def tool(self, *_, **__):
                def deco(fn): return fn
                return deco
            def run(self, *_, **__): ...
        sys.modules["fastmcp"].FastMCP = _Fake


def test_load_surfaces_shape():
    from mcp_server.agents.registry import load_surfaces
    surfaces = load_surfaces()
    assert {"sales-copilot", "bi-agent", "inventory-agent"} <= set(surfaces.keys())
    for s in surfaces.values():
        assert 1 <= len(s.tools) <= 10, f"agent {s.agent_id} có {len(s.tools)} tools (giới hạn 10)"
        assert s.rate_limit_rpm > 0
        for tname, spec in s.tools.items():
            assert callable(spec.handler), f"handler của {tname} phải callable"


def test_pii_tools_marked():
    from mcp_server.agents.registry import load_surfaces
    sales = load_surfaces()["sales-copilot"]
    assert sales.tools["get_customer_profile"].pii is True
    assert sales.tools["search_products"].pii is False


def test_inventory_agent_no_pii_tools():
    from mcp_server.agents.registry import load_surfaces
    inv = load_surfaces()["inventory-agent"]
    assert all(not t.pii for t in inv.tools.values()), "inventory-agent không nên có PII tool"
