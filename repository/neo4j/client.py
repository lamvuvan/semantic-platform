"""Layer 2 — Neo4j repository client.

Đọc Cypher từ `queries/*.cypher` (parameterized, version-controlled), thực thi
qua read-only session. Không có MERGE/CREATE/DELETE — Layer 2 này chỉ READ.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from neo4j import Driver, GraphDatabase

logger = logging.getLogger(__name__)
QUERIES_DIR = Path(__file__).with_name("queries")


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str
    database: str = "neo4j"


@lru_cache(maxsize=64)
def _load_query(name: str) -> str:
    path = QUERIES_DIR / f"{name}.cypher"
    return path.read_text(encoding="utf-8")


class Neo4jRepository:
    """Read-only DAO. Mọi truy vấn đi qua đây — không có Cypher inline ngoài đây."""

    def __init__(self, settings: Neo4jSettings) -> None:
        self._settings = settings
        self._driver: Driver = GraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password),
        )

    def close(self) -> None:
        self._driver.close()

    @contextmanager
    def _session(self) -> Iterator[Any]:
        with self._driver.session(
            database=self._settings.database,
            default_access_mode="READ",
        ) as session:
            yield session

    def run(self, query_name: str, **params: Any) -> list[dict[str, Any]]:
        cypher = _load_query(query_name)
        with self._session() as s:
            result = s.run(cypher, **params)
            return [dict(r) for r in result]

    def run_single(self, query_name: str, **params: Any) -> dict[str, Any] | None:
        cypher = _load_query(query_name)
        with self._session() as s:
            record = s.run(cypher, **params).single()
            return dict(record) if record else None
