"""HTTP client gọi Domain Service qua mTLS — Layer 4 → Layer 3.

Mỗi request kèm header trusted: X-Agent-Id, X-Merchant-Id, X-Scopes,
X-Request-Id. Client dùng cert nội VPC để Domain Service tin cậy caller.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import httpx


def _build_client(timeout_s: float = 5.0) -> httpx.AsyncClient:
    base_url = os.environ["DOMAIN_SERVICE_URL"]
    cert = (os.environ["MCP_MTLS_CERT"], os.environ["MCP_MTLS_KEY"])
    verify = os.environ.get("DOMAIN_SERVICE_CA", True)
    return httpx.AsyncClient(
        base_url=base_url,
        cert=cert,
        verify=verify,
        timeout=httpx.Timeout(timeout_s, connect=1.0),
        http2=True,
    )


class DomainClient:
    """Stateful client tái sử dụng connection pool."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._client = _build_client()

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    @asynccontextmanager
    async def _client_or_die(self):
        if self._client is None:
            raise RuntimeError("DomainClient not started")
        yield self._client

    async def post(self, path: str, *, headers: dict[str, str], json: Any) -> dict:
        async with self._client_or_die() as c:
            resp = await c.post(path, headers=headers, json=json)
            resp.raise_for_status()
            return resp.json()

    async def get(self, path: str, *, headers: dict[str, str], params: dict | None = None) -> dict:
        async with self._client_or_die() as c:
            resp = await c.get(path, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
