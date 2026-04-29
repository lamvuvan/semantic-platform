"""Validator chặn Cypher ghi/destructive trước khi chạy."""
from __future__ import annotations

import re

FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|FOREACH|CALL\s+apoc\.[^\s]*\.(write|delete))\b",
    re.IGNORECASE,
)
ALLOWED_PROCEDURES = {
    "db.index.fulltext.queryNodes",
    "db.index.vector.queryNodes",
}
PROC_RE = re.compile(r"CALL\s+([a-zA-Z0-9._]+)\s*\(", re.IGNORECASE)


class CypherSafetyError(ValueError):
    pass


def assert_read_only(cypher: str) -> None:
    if FORBIDDEN.search(cypher):
        raise CypherSafetyError("forbidden write/destructive clause detected")
    for proc in PROC_RE.findall(cypher):
        if proc not in ALLOWED_PROCEDURES:
            raise CypherSafetyError(f"procedure not allowlisted: {proc}")
