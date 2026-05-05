"""Test confidence ranking + fallback của ProductSearchService."""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

# Stub heavy DB clients trước khi import service.
for _mod in ("elasticsearch", "qdrant_client", "neo4j"):
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)
if not hasattr(sys.modules["elasticsearch"], "Elasticsearch"):
    sys.modules["elasticsearch"].Elasticsearch = type("Elasticsearch", (), {})  # type: ignore[attr-defined]
if "qdrant_client.http" not in sys.modules:
    sys.modules["qdrant_client.http"] = types.ModuleType("qdrant_client.http")
if "qdrant_client.http.models" not in sys.modules:
    qmodels = types.ModuleType("qdrant_client.http.models")
    qmodels.Filter = type("Filter", (), {"__init__": lambda self, **_: None})
    qmodels.FieldCondition = type("FieldCondition", (), {"__init__": lambda self, **_: None})
    qmodels.MatchValue = type("MatchValue", (), {"__init__": lambda self, **_: None})
    sys.modules["qdrant_client.http.models"] = qmodels
if not hasattr(sys.modules["qdrant_client"], "QdrantClient"):
    sys.modules["qdrant_client"].QdrantClient = type("QdrantClient", (), {})  # type: ignore[attr-defined]
if not hasattr(sys.modules["neo4j"], "Driver"):
    sys.modules["neo4j"].Driver = type("Driver", (), {})  # type: ignore[attr-defined]
    sys.modules["neo4j"].GraphDatabase = type("GraphDatabase", (), {"driver": staticmethod(lambda *a, **k: None)})  # type: ignore[attr-defined]

from domain.models import Caller, ProductSearchRequest  # noqa: E402
from domain.services.product_search import ProductSearchService  # noqa: E402


@pytest.fixture
def caller() -> Caller:
    return Caller(agent_id="t", merchant_id="M01", scopes=("merchant.read",), request_id="r1")


def _svc(es_hits, vec_hits):
    es = MagicMock()
    es.search_products.return_value = es_hits
    vec = MagicMock()
    vec.search_products.return_value = vec_hits
    neo = MagicMock()
    return ProductSearchService(es=es, vector=vec, neo4j=neo, embed_fn=lambda _: [0.1] * 384)


def test_hybrid_merge_picks_intersection_first(caller):
    svc = _svc(
        es_hits=[{"product_id": "P1", "name": "P1", "score": 10.0}, {"product_id": "P2", "name": "P2", "score": 5.0}],
        vec_hits=[{"product_id": "P1", "score": 0.95}, {"product_id": "P3", "score": 0.7}],
    )
    resp = svc.search(ProductSearchRequest(query="trà", top_k=5), caller)
    pids = [h.product_id for h in resp.hits]
    assert pids[0] == "P1"  # xuất hiện ở cả 2 source → cao nhất
    assert "lexical" in resp.hits[0].sources and "semantic" in resp.hits[0].sources
    assert not resp.fallback_used


def test_fallback_when_one_source_fails(caller):
    es = MagicMock()
    es.search_products.side_effect = RuntimeError("ES down")
    vec = MagicMock()
    vec.search_products.return_value = [{"product_id": "P1", "score": 0.9}]
    svc = ProductSearchService(es=es, vector=vec, neo4j=MagicMock(), embed_fn=lambda _: [0.0] * 384)
    resp = svc.search(ProductSearchRequest(query="trà", top_k=3), caller)
    assert [h.product_id for h in resp.hits] == ["P1"]
    assert resp.fallback_used is True


def test_tenant_scope_pulled_from_caller(caller):
    es = MagicMock(); es.search_products.return_value = []
    vec = MagicMock(); vec.search_products.return_value = []
    svc = ProductSearchService(es=es, vector=vec, neo4j=MagicMock(), embed_fn=lambda _: [0.0] * 384)
    svc.search(ProductSearchRequest(query="x", top_k=1), caller)
    # ES + Vector phải nhận đúng merchant_id từ caller, không phải từ payload.
    es.search_products.assert_called_with(merchant_id="M01", query="x", top_k=1)
    vec.search_products.assert_called_with(merchant_id="M01", embedding=[0.0] * 384, top_k=1)
