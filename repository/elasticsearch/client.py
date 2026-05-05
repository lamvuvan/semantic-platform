"""Layer 2 — Elasticsearch repository (lexical search) cho Product index.

Tenant scoping bắt buộc qua filter `merchant_id`. Layer 3 chèn từ JWT —
không tin tham số merchant_id từ caller.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)
QUERIES_DIR = Path(__file__).with_name("queries")
PRODUCT_INDEX = "products"


@dataclass(frozen=True)
class ElasticsearchSettings:
    hosts: list[str]
    api_key: str | None = None
    ca_cert_path: str | None = None
    timeout_s: int = 5


@lru_cache(maxsize=32)
def _load_template(name: str) -> str:
    return (QUERIES_DIR / f"{name}.json").read_text(encoding="utf-8")


class ElasticsearchRepository:
    def __init__(self, settings: ElasticsearchSettings) -> None:
        kwargs: dict[str, Any] = {"hosts": settings.hosts, "request_timeout": settings.timeout_s}
        if settings.api_key:
            kwargs["api_key"] = settings.api_key
        if settings.ca_cert_path:
            kwargs["ca_certs"] = settings.ca_cert_path
        self._client = Elasticsearch(**kwargs)

    def close(self) -> None:
        self._client.close()

    def search_products(self, *, merchant_id: str, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        template = _load_template("product_search")
        body = json.loads(
            template
            .replace("{{q}}", _escape(query))
            .replace("{{merchant_id}}", _escape(merchant_id))
            .replace('"{{top_k}}"', str(int(top_k)))
        )
        resp = self._client.search(index=PRODUCT_INDEX, body=body)
        hits = resp.get("hits", {}).get("hits", [])
        return [
            {
                "product_id": h["_source"]["product_id"],
                "name":       h["_source"].get("name"),
                "score":      h["_score"],
                "category_path": h["_source"].get("category_path"),
            }
            for h in hits
        ]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
