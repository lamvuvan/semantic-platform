"""ProductSearchService — Layer 3 business logic.

Hybrid search = lexical (ES) + semantic (Vector) + graph (Neo4j neighborhood).
Confidence ranking + fallback khi 1 nguồn down.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from domain.models import Caller, ProductHit, ProductSearchRequest, ProductSearchResponse
from repository.elasticsearch.client import ElasticsearchRepository
from repository.neo4j.client import Neo4jRepository
from repository.vector.client import VectorRepository

logger = logging.getLogger(__name__)


@dataclass
class _Source:
    name: str
    weight: float


_WEIGHTS = {
    "lexical": _Source("lexical", weight=0.45),
    "semantic": _Source("semantic", weight=0.40),
    "graph":    _Source("graph",   weight=0.15),
}


class ProductSearchService:
    def __init__(
        self,
        *,
        es: ElasticsearchRepository,
        vector: VectorRepository,
        neo4j: Neo4jRepository,
        embed_fn,  # callable(str) -> list[float]
    ) -> None:
        self._es = es
        self._vec = vector
        self._neo = neo4j
        self._embed = embed_fn

    def search(self, req: ProductSearchRequest, caller: Caller) -> ProductSearchResponse:
        """Hybrid search.

        Tenant scoping: chỉ dùng caller.merchant_id. Bất kỳ merchant_id nào
        khác trong body bị bỏ qua — đây là invariant Layer 3.
        """
        merchant = caller.merchant_id
        with ThreadPoolExecutor(max_workers=3) as pool:
            f_lex = pool.submit(self._lexical, req, merchant) if req.mode in ("hybrid", "lexical") else None
            f_sem = pool.submit(self._semantic, req, merchant) if req.mode in ("hybrid", "semantic") else None
            f_grp = pool.submit(self._graph, req, merchant) if req.mode == "hybrid" else None

            results: dict[str, dict[str, dict]] = {}  # source -> {product_id: hit}
            for source, fut in (("lexical", f_lex), ("semantic", f_sem), ("graph", f_grp)):
                if fut is None:
                    continue
                try:
                    results[source] = {h["product_id"]: h for h in fut.result(timeout=4)}
                except Exception:
                    logger.exception("source %s failed; degrading", source)
                    results[source] = {}

        merged = self._merge(results, top_k=req.top_k)
        fallback = any(not results.get(s) for s in ("lexical", "semantic")) and req.mode == "hybrid"
        return ProductSearchResponse(hits=merged, fallback_used=fallback, request_id=caller.request_id)

    # ── kênh search ─────────────────────────────────────────────────────────
    def _lexical(self, req: ProductSearchRequest, merchant: str) -> list[dict]:
        return self._es.search_products(merchant_id=merchant, query=req.query, top_k=req.top_k)

    def _semantic(self, req: ProductSearchRequest, merchant: str) -> list[dict]:
        emb = self._embed(req.query)
        return self._vec.search_products(merchant_id=merchant, embedding=emb, top_k=req.top_k)

    def _graph(self, req: ProductSearchRequest, merchant: str) -> list[dict]:
        # Đơn giản: trả về 0 hits ở MVP — sẽ enable khi có category-keyword matching.
        return []

    # ── ranking ────────────────────────────────────────────────────────────
    @staticmethod
    def _merge(results: dict[str, dict[str, dict]], top_k: int) -> list[ProductHit]:
        scores: dict[str, dict] = {}
        for source, hits in results.items():
            weight = _WEIGHTS[source].weight
            # Normalize score within each source
            max_score = max((h.get("score", 0.0) for h in hits.values()), default=0.0) or 1.0
            for pid, h in hits.items():
                norm = float(h.get("score", 0.0)) / max_score
                entry = scores.setdefault(pid, {"name": h.get("name"), "confidence": 0.0, "sources": []})
                entry["confidence"] += weight * norm
                entry["sources"].append(source)
                entry["name"] = entry["name"] or h.get("name")

        ranked = sorted(scores.items(), key=lambda kv: kv[1]["confidence"], reverse=True)[:top_k]
        return [
            ProductHit(
                product_id=pid,
                name=v["name"],
                confidence=min(v["confidence"], 1.0),
                sources=tuple(sorted(set(v["sources"]))),
            )
            for pid, v in ranked
        ]
