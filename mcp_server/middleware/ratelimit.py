"""Rate limit per agent + per merchant qua Redis (token bucket).

Key naming:
    rl:{agent_id}:{merchant_id}:{window_start_minute}

Default: 60 req/phút per (agent, merchant). Override per-tool tại registry.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import redis.asyncio as redis_async


class RateLimitExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class RateLimit:
    requests_per_minute: int = 60


class RateLimiter:
    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.environ["REDIS_URL"]
        self._client: redis_async.Redis | None = None

    async def startup(self) -> None:
        self._client = redis_async.from_url(self._url, encoding="utf-8", decode_responses=True)

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def check(self, *, agent_id: str, merchant_id: str, tool: str, limit: RateLimit) -> None:
        assert self._client is not None
        window = int(time.time() // 60)
        key = f"rl:{agent_id}:{merchant_id}:{tool}:{window}"
        # INCR + EXPIRE atomic via pipeline
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 65)
            count, _ = await pipe.execute()
        if int(count) > limit.requests_per_minute:
            raise RateLimitExceeded(
                f"rate limit exceeded: {agent_id}/{merchant_id}/{tool} = {count}/{limit.requests_per_minute}/min"
            )
