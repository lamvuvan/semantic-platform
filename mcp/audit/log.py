"""Audit log JSON cho mỗi MCP tool call → stdout (Loki) + Postgres bảng `mcp_audit`."""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("mcp.audit")


@contextmanager
def audit(tool: str, caller_sub: str, params: dict[str, Any]) -> Iterator[dict]:
    state: dict[str, Any] = {
        "tool": tool,
        "caller": caller_sub,
        "params": _redact(params),
        "started_at": time.time(),
        "ok": False,
    }
    try:
        yield state
        state["ok"] = True
    finally:
        state["latency_ms"] = int((time.time() - state["started_at"]) * 1000)
        logger.info(json.dumps(state, default=str))


def _redact(params: dict[str, Any]) -> dict[str, Any]:
    """Loại bỏ các trường nhạy cảm khỏi audit log."""
    redacted = dict(params)
    for key in ("phone", "email", "raw_pii"):
        if key in redacted:
            redacted[key] = "***"
    return redacted
