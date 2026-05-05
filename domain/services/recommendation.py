"""RecommendationService — gợi ý topping cho 1 sản phẩm.

Logic: kết hợp co-purchase (graph) + personal bias (graph) + category default.
"""
from __future__ import annotations

from domain.models import Caller, RecommendationRequest, RecommendationResponse, ToppingRecommendation
from repository.neo4j.client import Neo4jRepository

_PERSONAL_QUERY = """
MATCH (:Merchant {merchant_id: $merchant_id})<-[:PLACED_AT]-(:Order)<-[:PLACED]-(:Customer {customer_id: $customer_id})
RETURN 1 LIMIT 0
"""


class RecommendationService:
    def __init__(self, *, neo4j: Neo4jRepository) -> None:
        self._neo = neo4j

    def recommend_toppings(self, req: RecommendationRequest, caller: Caller) -> RecommendationResponse:
        co_rows = self._neo.run(
            "co_purchase_toppings",
            merchant_id=caller.merchant_id,
            product_id=req.product_id,
            k=req.top_k * 2,
        )

        scored: dict[str, ToppingRecommendation] = {}
        if co_rows:
            max_freq = max(int(r["frequency"]) for r in co_rows) or 1
            for r in co_rows:
                tid = r["topping_id"]
                scored[tid] = ToppingRecommendation(
                    topping_id=tid,
                    name=r.get("name"),
                    score=float(r["frequency"]) / max_freq,
                    rationale="co_purchase",
                )

        # Stub: personal/category fallback bỏ trống ở MVP — sẽ làm sau.
        ranked = sorted(scored.values(), key=lambda x: x.score, reverse=True)[: req.top_k]
        return RecommendationResponse(
            product_id=req.product_id,
            recommendations=ranked,
            request_id=caller.request_id,
        )
