"""Cross-encoder reranker (BGE) — placeholder gọi tới mô hình self-host."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Reranked:
    text: str
    score: float


class Reranker:
    """Wrapper quanh mô hình BGE-reranker chạy local hoặc qua HTTP API.

    Triển khai thật: đặt model trên GPU VM và gọi qua REST.
    Stub trả về điểm theo độ trùng từ khoá để test pipeline.
    """

    def __init__(self, endpoint: str | None = None) -> None:
        self._endpoint = endpoint

    def rerank(self, query: str, candidates: Sequence[str], top_k: int = 10) -> list[Reranked]:
        if self._endpoint:
            return self._rerank_remote(query, candidates, top_k)
        return self._rerank_stub(query, candidates, top_k)

    def _rerank_remote(self, query: str, candidates: Sequence[str], top_k: int) -> list[Reranked]:
        import httpx

        resp = httpx.post(
            self._endpoint,
            json={"query": query, "candidates": list(candidates), "top_k": top_k},
            timeout=10.0,
        )
        resp.raise_for_status()
        scored = resp.json()["scored"]
        return [Reranked(text=s["text"], score=float(s["score"])) for s in scored]

    @staticmethod
    def _rerank_stub(query: str, candidates: Sequence[str], top_k: int) -> list[Reranked]:
        q_tokens = set(query.lower().split())
        scored = [
            Reranked(text=c, score=len(q_tokens & set(c.lower().split())) / max(len(q_tokens), 1))
            for c in candidates
        ]
        return sorted(scored, key=lambda r: r.score, reverse=True)[:top_k]
