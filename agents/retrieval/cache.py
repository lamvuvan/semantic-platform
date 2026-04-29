"""Cache wrapper cho context retrieval — Redis backend với fallback in-memory."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CacheKey:
    intent: str
    entity_ids: tuple[str, ...]
    params: tuple[tuple[str, Any], ...]

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"intent": self.intent, "entity_ids": list(self.entity_ids), "params": dict(self.params)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class ContextCache:
    """Phía trước Redis. Nếu không có client thì dùng dict in-process (test/dev)."""

    def __init__(self, redis_client=None, namespace: str = "ctx") -> None:
        self._redis = redis_client
        self._ns = namespace
        self._mem: dict[str, tuple[float, str]] = {}

    def get(self, key: CacheKey) -> dict | None:
        full = f"{self._ns}:{key.fingerprint()}"
        if self._redis is not None:
            raw = self._redis.get(full)
            return json.loads(raw) if raw else None
        entry = self._mem.get(full)
        if entry is None:
            return None
        expires, raw = entry
        if expires < time.time():
            self._mem.pop(full, None)
            return None
        return json.loads(raw)

    def set(self, key: CacheKey, value: dict, ttl_seconds: int) -> None:
        full = f"{self._ns}:{key.fingerprint()}"
        payload = json.dumps(value, default=str)
        if self._redis is not None:
            self._redis.setex(full, ttl_seconds, payload)
        else:
            self._mem[full] = (time.time() + ttl_seconds, payload)
