"""Entity linker: từ câu hỏi NL → candidate entity IDs có score."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from neo4j import Driver


@dataclass(frozen=True)
class EntityCandidate:
    type: str
    id: str
    name: str
    score: float


class EntityLinker:
    """Link entity bằng full-text + vector trên Neo4j."""

    def __init__(self, driver: Driver, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    def link_products(self, mention: str, top_k: int = 5) -> list[EntityCandidate]:
        cypher = """
        CALL db.index.fulltext.queryNodes('product_fulltext', $q) YIELD node, score
        RETURN node.product_id AS id, node.name AS name, score
        ORDER BY score DESC LIMIT $k
        """
        with self._driver.session(database=self._database) as session:
            return [
                EntityCandidate(type="Product", id=r["id"], name=r["name"], score=float(r["score"]))
                for r in session.run(cypher, q=mention, k=top_k)
            ]

    def link_by_vector(self, embedding: Sequence[float], top_k: int = 5) -> list[EntityCandidate]:
        cypher = """
        CALL db.index.vector.queryNodes('product_embedding', $k, $emb)
        YIELD node, score
        RETURN node.product_id AS id, node.name AS name, score
        """
        with self._driver.session(database=self._database) as session:
            return [
                EntityCandidate(type="Product", id=r["id"], name=r["name"], score=float(r["score"]))
                for r in session.run(cypher, k=top_k, emb=list(embedding))
            ]
