"""Layer 2 — Vector repository (semantic search) trên Qdrant.

Embedding sinh ở Domain Service hoặc embedding-worker, KHÔNG sinh ở repo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as q

logger = logging.getLogger(__name__)
PRODUCTS_COLLECTION = "products"


@dataclass(frozen=True)
class VectorSettings:
    url: str
    api_key: str | None = None
    timeout_s: int = 5


class VectorRepository:
    def __init__(self, settings: VectorSettings) -> None:
        self._client = QdrantClient(
            url=settings.url,
            api_key=settings.api_key,
            timeout=settings.timeout_s,
        )

    def close(self) -> None:
        self._client.close()

    def search_products(
        self,
        *,
        merchant_id: str,
        embedding: list[float],
        top_k: int = 10,
        score_threshold: float | None = 0.6,
    ) -> list[dict[str, Any]]:
        flt = q.Filter(must=[q.FieldCondition(key="merchant_id", match=q.MatchValue(value=merchant_id))])
        hits = self._client.search(
            collection_name=PRODUCTS_COLLECTION,
            query_vector=embedding,
            query_filter=flt,
            limit=top_k,
            score_threshold=score_threshold,
        )
        return [
            {
                "product_id": h.payload.get("product_id") if h.payload else None,
                "score": float(h.score),
                "merchant_id": h.payload.get("merchant_id") if h.payload else None,
                "category_id": h.payload.get("category_id") if h.payload else None,
            }
            for h in hits
        ]
