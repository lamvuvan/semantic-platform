"""Audit log mọi MCP tool call — JSON dòng → Loki + Postgres mcp_audit."""
from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("mcp.audit")


@contextmanager
def audit(*, tool: str, agent_id: str, merchant_id: str, params: dict[str, Any]) -> Iterator[dict]:
    state: dict[str, Any] = {
        "request_id": str(uuid.uuid4()),
        "tool": tool,
        "agent_id": agent_id,
        "merchant_id": merchant_id,
        "params": _redact(params),
        "started_at": time.time(),
        "ok": False,
    }
    try:
        yield state
        state["ok"] = True
    except Exception as e:
        state["error"] = type(e).__name__
        state["error_msg"] = str(e)[:200]
        raise
    finally:
        state["latency_ms"] = int((time.time() - state["started_at"]) * 1000)
        logger.info(json.dumps(state, default=str))


def _redact(params: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(params)
    for k in ("phone", "email", "raw_pii", "token", "authorization"):
        if k in redacted:
            redacted[k] = "***"
    return redacted
