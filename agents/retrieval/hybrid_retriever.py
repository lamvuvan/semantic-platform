"""Hybrid retriever: vector + full-text + graph chạy song song, gộp kết quả."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Sequence

from neo4j import Driver


@dataclass(frozen=True)
class RetrievalHit:
    node_id: str
    label: str
    name: str
    score: float
    channel: str


class HybridRetriever:
    def __init__(self, driver: Driver, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    def retrieve(
        self,
        query: str,
        embedding: Sequence[float] | None,
        vector_top_k: int = 20,
        fulltext_top_k: int = 20,
        merchant_id: str | None = None,
    ) -> list[RetrievalHit]:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = []
            futures.append(pool.submit(self._fulltext, query, fulltext_top_k, merchant_id))
            if embedding is not None:
                futures.append(pool.submit(self._vector, list(embedding), vector_top_k, merchant_id))
            results: list[RetrievalHit] = []
            for f in futures:
                results.extend(f.result())
        return self._dedupe(results)

    def _fulltext(self, q: str, k: int, merchant_id: str | None) -> list[RetrievalHit]:
        cypher = """
        CALL db.index.fulltext.queryNodes('product_fulltext', $q) YIELD node, score
        WITH node, score
        WHERE $merchant_id IS NULL OR EXISTS {
          MATCH (m:Merchant {merchant_id: $merchant_id})-[:OWNS]->(node)
        }
        RETURN node.product_id AS id, node.name AS name, score LIMIT $k
        """
        with self._driver.session(database=self._database) as s:
            rs = s.run(cypher, q=q, k=k, merchant_id=merchant_id)
            return [
                RetrievalHit(node_id=r["id"], label="Product", name=r["name"], score=float(r["score"]), channel="fulltext")
                for r in rs
            ]

    def _vector(self, emb: list[float], k: int, merchant_id: str | None) -> list[RetrievalHit]:
        cypher = """
        CALL db.index.vector.queryNodes('product_embedding', $k, $emb) YIELD node, score
        WITH node, score
        WHERE $merchant_id IS NULL OR EXISTS {
          MATCH (m:Merchant {merchant_id: $merchant_id})-[:OWNS]->(node)
        }
        RETURN node.product_id AS id, node.name AS name, score
        """
        with self._driver.session(database=self._database) as s:
            rs = s.run(cypher, k=k, emb=emb, merchant_id=merchant_id)
            return [
                RetrievalHit(node_id=r["id"], label="Product", name=r["name"], score=float(r["score"]), channel="vector")
                for r in rs
            ]

    @staticmethod
    def _dedupe(hits: list[RetrievalHit]) -> list[RetrievalHit]:
        best: dict[tuple[str, str], RetrievalHit] = {}
        for h in hits:
            key = (h.label, h.node_id)
            if key not in best or h.score > best[key].score:
                best[key] = h
        return sorted(best.values(), key=lambda x: x.score, reverse=True)
