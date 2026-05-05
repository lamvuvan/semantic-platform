"""Validate Pydantic input contract — đảm bảo agent không bypass merchant scoping."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from domain.models.schemas import (
    AliasFeedbackRequest,
    Caller,
    ProductSearchRequest,
    RecommendationRequest,
)


def test_search_request_validates_query():
    req = ProductSearchRequest(query="trà sữa", top_k=5)
    assert req.mode == "hybrid"
    with pytest.raises(ValidationError):
        ProductSearchRequest(query="", top_k=5)
    with pytest.raises(ValidationError):
        ProductSearchRequest(query="x", top_k=999)


def test_recommendation_request_top_k_capped_20():
    with pytest.raises(ValidationError):
        RecommendationRequest(product_id="P001", top_k=21)


def test_alias_feedback_confidence_bounds():
    from datetime import datetime, timezone
    with pytest.raises(ValidationError):
        AliasFeedbackRequest(
            surface_text="trà sữa size lớn",
            matched_product_id="P001",
            confidence=1.5,
            was_accepted=True,
            submitted_at=datetime.now(timezone.utc),
        )


def test_caller_requires_merchant_id():
    with pytest.raises(ValidationError):
        Caller(agent_id="sales-copilot", merchant_id="", scopes=(), request_id="r1")
