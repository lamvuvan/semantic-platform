"""Smoke test idempotency của loader — yêu cầu Neo4j đang chạy.

Chạy: pytest tests/integration/test_loader_idempotent.py
"""
from __future__ import annotations

import os

import pytest

from loaders.common.neo4j_writer import Neo4jConfig, driver, merge_nodes

pytestmark = pytest.mark.skipif(
    "NEO4J_URI" not in os.environ,
    reason="cần Neo4j chạy + biến môi trường NEO4J_URI/USER/PASSWORD",
)


def test_merge_nodes_idempotent():
    cfg = Neo4jConfig(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    )
    rows = [
        {"product_id": "TEST_P1", "name": "Test 1"},
        {"product_id": "TEST_P2", "name": "Test 2"},
    ]
    with driver(cfg) as drv:
        merge_nodes(drv, cfg.database, "Product", "product_id", rows)
        merge_nodes(drv, cfg.database, "Product", "product_id", rows)  # chạy lần 2
        with drv.session(database=cfg.database) as s:
            count = s.run(
                "MATCH (p:Product) WHERE p.product_id IN $ids RETURN count(p) AS c",
                ids=[r["product_id"] for r in rows],
            ).single()["c"]
        assert count == len(rows)
