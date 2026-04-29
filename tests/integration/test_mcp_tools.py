"""Integration test MCP tools end-to-end với Neo4j seed."""
from __future__ import annotations

import os

import pytest

from mcp.auth.oidc import Caller
from mcp.tools import get_product, search_products

pytestmark = pytest.mark.skipif(
    "NEO4J_URI" not in os.environ,
    reason="cần Neo4j seeded",
)


def _caller() -> Caller:
    return Caller(
        sub="it",
        scopes=frozenset({"merchant.read", "customer.read", "recommendation.read", "analytics.read"}),
        tenant_merchant_id=None,
        raw={},
    )


def test_search_and_get_product():
    res = search_products.run(_caller(), query="matcha", top_k=5)
    assert "results" in res
    detail = get_product.run(_caller(), product_id="P_MAT_M")
    assert detail["product"] is not None
    assert detail["product"]["name"].lower().startswith("matcha")
