"""Idempotent UNWIND + MERGE helper cho Neo4j Community.

Sử dụng `apoc.periodic.iterate` để load batch lớn không giữ transaction lâu.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, Iterator

from neo4j import Driver, GraphDatabase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j"


@contextmanager
def driver(cfg: Neo4jConfig) -> Iterator[Driver]:
    drv = GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))
    try:
        yield drv
    finally:
        drv.close()


def merge_nodes(
    drv: Driver,
    database: str,
    label: str,
    key: str,
    rows: Iterable[dict],
    batch_size: int = 10_000,
) -> int:
    """MERGE nodes idempotent.

    Cypher template chỉ chấp nhận label/key từ developer (allowlist), không từ user input.
    """
    cypher = (
        f"UNWIND $rows AS row "
        f"MERGE (n:`{label}` {{`{key}`: row.`{key}`}}) "
        f"SET n += row"
    )
    return _periodic_iterate(drv, database, rows, cypher, batch_size)


def merge_edges(
    drv: Driver,
    database: str,
    src_label: str,
    src_key: str,
    rel_type: str,
    dst_label: str,
    dst_key: str,
    rows: Iterable[dict],
    batch_size: int = 10_000,
) -> int:
    """MERGE relationships idempotent.

    `rows` cần các trường: src, dst, props (dict).
    """
    cypher = (
        f"UNWIND $rows AS row "
        f"MATCH (a:`{src_label}` {{`{src_key}`: row.src}}) "
        f"MATCH (b:`{dst_label}` {{`{dst_key}`: row.dst}}) "
        f"MERGE (a)-[r:`{rel_type}`]->(b) "
        f"SET r += coalesce(row.props, {{}})"
    )
    return _periodic_iterate(drv, database, rows, cypher, batch_size)


def _periodic_iterate(
    drv: Driver,
    database: str,
    rows: Iterable[dict],
    inner_cypher: str,
    batch_size: int,
) -> int:
    materialized = list(rows)
    if not materialized:
        return 0
    outer = "UNWIND $rows AS row RETURN row"
    apoc = (
        "CALL apoc.periodic.iterate($outer, $inner, "
        "{batchSize: $batch, parallel: false, params: {rows: $rows}}) "
        "YIELD batches, total RETURN batches, total"
    )
    with drv.session(database=database) as session:
        result = session.run(
            apoc,
            outer=outer,
            inner=inner_cypher,
            batch=batch_size,
            rows=materialized,
        ).single()
        if result is None:
            return 0
        total = int(result["total"])
        logger.info("merged %s rows in %s batches", total, result["batches"])
        return total


def upsert_vector(
    drv: Driver,
    database: str,
    label: str,
    key: str,
    rows: Iterable[dict],
    embedding_field: str = "embedding",
    batch_size: int = 1_000,
) -> int:
    cypher = (
        f"UNWIND $rows AS row "
        f"MATCH (n:`{label}` {{`{key}`: row.`{key}`}}) "
        f"CALL db.create.setNodeVectorProperty(n, '{embedding_field}', row.{embedding_field})"
    )
    return _periodic_iterate(drv, database, rows, cypher, batch_size)
