"""Context retrieval pipeline: glue các bước thành 1 entrypoint cho MCP tool gọi.

Tham chiếu: docs/PLAN.md §2.3
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from neo4j import Driver

from agents.retrieval.cache import CacheKey, ContextCache
from agents.retrieval.entity_linker import EntityCandidate, EntityLinker
from agents.retrieval.hybrid_retriever import HybridRetriever, RetrievalHit
from agents.retrieval.reranker import Reranker
from agents.retrieval.subgraph_extractor import Subgraph, SubgraphExtractor
from agents.retrieval.summarizer import summarize_customer, summarize_product_neighborhood

POLICIES_PATH = Path(__file__).with_name("policies.yaml")


def _load_policies() -> dict:
    return yaml.safe_load(POLICIES_PATH.read_text())


@dataclass
class ContextObject:
    intent: str
    entities: list[dict] = field(default_factory=list)
    subgraph: dict = field(default_factory=lambda: {"nodes": [], "edges": []})
    summaries: list[str] = field(default_factory=list)
    evidence_cypher: str = ""
    freshness_ts: str = ""
    ttl_s: int = 3600

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextRetriever:
    def __init__(
        self,
        driver: Driver,
        database: str = "neo4j",
        cache: ContextCache | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self._driver = driver
        self._db = database
        self._linker = EntityLinker(driver, database)
        self._hybrid = HybridRetriever(driver, database)
        self._extractor = SubgraphExtractor(driver, database)
        self._cache = cache or ContextCache()
        self._reranker = reranker or Reranker()
        self._policies = _load_policies()

    def retrieve(
        self,
        intent: str,
        query: str | None = None,
        entity_ids: list[str] | None = None,
        params: dict | None = None,
        embedding: list[float] | None = None,
        merchant_id: str | None = None,
    ) -> ContextObject:
        params = params or {}
        entity_ids = entity_ids or []
        policy = self._resolve_policy(intent)
        cache_key = CacheKey(
            intent=intent,
            entity_ids=tuple(entity_ids),
            params=tuple(sorted(params.items())),
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return ContextObject(**cached)

        ctx = ContextObject(intent=intent, ttl_s=policy["cache_ttl_seconds"])
        if intent == "customer_360" and entity_ids:
            sub = self._extractor.around_customer(
                customer_id=entity_ids[0],
                days=policy.get("time_window_days", 90),
                max_nodes=policy["max_nodes"],
            )
            ctx.subgraph = {"nodes": sub.nodes, "edges": sub.edges}
            ctx.summaries.append(summarize_customer(sub))
            ctx.evidence_cypher = sub.evidence_cypher
        elif intent in ("recommend_topping", "search_product", "data_discovery"):
            hits: list[RetrievalHit] = self._hybrid.retrieve(
                query=query or "",
                embedding=embedding,
                vector_top_k=policy.get("vector_top_k", 20),
                fulltext_top_k=policy.get("fulltext_top_k", 20),
                merchant_id=merchant_id,
            )
            reranked = self._reranker.rerank(
                query or "",
                [h.name for h in hits],
                top_k=policy["rerank_top_k"],
            )
            top_names = {r.text for r in reranked}
            top_hits = [h for h in hits if h.name in top_names]
            ctx.entities = [{"type": h.label, "id": h.node_id, "name": h.name, "score": h.score} for h in top_hits]
            if intent == "recommend_topping" and top_hits:
                sub = self._extractor.around_product(
                    product_id=top_hits[0].node_id,
                    depth=2,
                    max_nodes=policy["max_nodes"],
                )
                ctx.subgraph = {"nodes": sub.nodes, "edges": sub.edges}
                ctx.summaries.append(summarize_product_neighborhood(sub))
                ctx.evidence_cypher = sub.evidence_cypher
        else:
            raise ValueError(f"unsupported intent: {intent}")

        ctx.freshness_ts = datetime.now(timezone.utc).isoformat()
        self._cache.set(cache_key, ctx.to_dict(), ttl_seconds=ctx.ttl_s)
        return ctx

    def link_products(self, mention: str, top_k: int = 5) -> list[EntityCandidate]:
        return self._linker.link_products(mention, top_k=top_k)

    def _resolve_policy(self, intent: str) -> dict:
        defaults = self._policies["defaults"]
        intent_pol = self._policies["intents"].get(intent, {})
        return {**defaults, **intent_pol}
