"""Embedding adapter: gọi tới embedding service nội bộ (HTTP nội VPC).

Mặc định dùng REST endpoint `EMBEDDING_URL`. Có cache đơn giản để khử
gọi lặp cho cùng query trong vòng 60s.
"""
from __future__ import annotations

import os
import time

import httpx

_TIMEOUT = httpx.Timeout(2.0, connect=1.0)
_CACHE: dict[str, tuple[float, list[float]]] = {}
_CACHE_TTL_S = 60.0


def embed(text: str) -> list[float]:
    cached = _CACHE.get(text)
    if cached and time.time() - cached[0] < _CACHE_TTL_S:
        return cached[1]
    url = os.environ.get("EMBEDDING_URL", "http://embedding-svc.internal/embed")
    resp = httpx.post(url, json={"text": text}, timeout=_TIMEOUT)
    resp.raise_for_status()
    vec: list[float] = resp.json()["embedding"]
    _CACHE[text] = (time.time(), vec)
    return vec
