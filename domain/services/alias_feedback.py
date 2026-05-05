"""AliasFeedbackService — agent gửi alias mới khi người dùng gõ tự do.

Mục tiêu: lưu (surface_text → product_id) làm tín hiệu để cải thiện
lexical search (boost ES alias field) và embedding training set.

MVP: ghi vào Postgres `aliases` table; offline pipeline đẩy vào ES alias
field trong batch hôm sau. Production sẽ bổ sung review queue cho confidence
thấp.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

import asyncpg

from domain.models import AliasFeedbackRequest, AliasFeedbackResponse, Caller

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostgresSettings:
    dsn: str


_INSERT = """
INSERT INTO aliases (alias_id, merchant_id, surface_text, matched_product_id,
                     confidence, was_accepted, submitted_by_agent, submitted_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (merchant_id, surface_text, matched_product_id)
DO UPDATE SET
    confidence    = EXCLUDED.confidence,
    was_accepted  = EXCLUDED.was_accepted,
    submitted_at  = EXCLUDED.submitted_at
RETURNING alias_id
"""


class AliasFeedbackService:
    def __init__(self, settings: PostgresSettings) -> None:
        self._dsn = settings.dsn
        self._pool: asyncpg.Pool | None = None

    async def startup(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=8)

    async def shutdown(self) -> None:
        if self._pool is not None:
            await self._pool.close()

    async def submit(self, req: AliasFeedbackRequest, caller: Caller) -> AliasFeedbackResponse:
        assert self._pool is not None, "service not started"
        # Threshold đơn giản: chấp nhận khi confidence >= 0.7 hoặc was_accepted=True từ user.
        accepted = bool(req.was_accepted) and req.confidence >= 0.7
        alias_id = str(uuid.uuid4())
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                _INSERT,
                alias_id,
                caller.merchant_id,
                req.surface_text,
                req.matched_product_id,
                req.confidence,
                accepted,
                caller.agent_id,
                req.submitted_at,
            )
        return AliasFeedbackResponse(
            alias_id=str(row["alias_id"]),
            accepted=accepted,
            request_id=caller.request_id,
        )
