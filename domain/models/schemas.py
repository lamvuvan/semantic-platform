"""Pydantic models — input/output contract của Layer 3 Domain Service.

Layer 4 MCP cũng dùng các model này để validate input từ AI agent — đảm bảo
request đi qua boundary có schema thống nhất, version-stable.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Auth context — Domain Service nhận từ MCP qua mTLS header
# ─────────────────────────────────────────────────────────────────────────────
class Caller(BaseModel):
    """Caller identity injected từ Layer 4 MCP server qua trusted mTLS header."""

    agent_id: str = Field(..., min_length=1, description="ID của AI agent (vd: sales-copilot)")
    merchant_id: str = Field(..., min_length=1, description="Tenant scope — REQUIRED, không override được")
    scopes: tuple[str, ...] = Field(default=(), description="OAuth scopes")
    request_id: str = Field(..., min_length=1, description="Trace ID xuyên suốt MCP→Domain→Repo")


# ─────────────────────────────────────────────────────────────────────────────
# Common
# ─────────────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    neo4j: bool
    elasticsearch: bool
    vector_store: bool
    version: str


# ─────────────────────────────────────────────────────────────────────────────
# Product search
# ─────────────────────────────────────────────────────────────────────────────
class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    top_k: int = Field(10, ge=1, le=50)
    mode: Literal["hybrid", "lexical", "semantic"] = "hybrid"

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query rỗng sau khi strip")
        return v


class ProductHit(BaseModel):
    product_id: str
    name: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: tuple[Literal["lexical", "semantic", "graph"], ...]
    category_path: list[str] | None = None


class ProductSearchResponse(BaseModel):
    hits: list[ProductHit]
    fallback_used: bool = False
    request_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Recommendation
# ─────────────────────────────────────────────────────────────────────────────
class RecommendationRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    customer_id: str | None = None
    top_k: int = Field(10, ge=1, le=20)


class ToppingRecommendation(BaseModel):
    topping_id: str
    name: str | None = None
    score: float
    rationale: Literal["co_purchase", "personal", "category_default"]


class RecommendationResponse(BaseModel):
    product_id: str
    recommendations: list[ToppingRecommendation]
    request_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Customer profile
# ─────────────────────────────────────────────────────────────────────────────
class CustomerProfileResponse(BaseModel):
    customer_id: str
    segment: str | None = None
    loyalty_tier: str | None = None
    order_count: int
    gmv: float
    top_products: list[dict]
    top_toppings: list[dict]
    request_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Alias feedback — agent gửi alias mới (vd "trà sữa size lớn" → P_TS_L)
# ─────────────────────────────────────────────────────────────────────────────
class AliasFeedbackRequest(BaseModel):
    surface_text: str = Field(..., min_length=1, max_length=200, description="Text user gõ")
    matched_product_id: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    was_accepted: bool
    submitted_at: datetime


class AliasFeedbackResponse(BaseModel):
    alias_id: str
    accepted: bool
    request_id: str
