"""Layer 3 — Domain Service FastAPI app.

Endpoints (chỉ MCP server gọi qua mTLS, không expose ngoài VPC):
- GET  /healthz
- POST /v1/products/search
- POST /v1/recommendations/toppings
- GET  /v1/customers/{customer_id}
- POST /v1/aliases/feedback
- GET  /metrics  (Prometheus)
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from domain.embedding import embed
from domain.models import (
    AliasFeedbackRequest,
    AliasFeedbackResponse,
    Caller,
    CustomerProfileResponse,
    HealthResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from domain.observability.telemetry import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    install_fastapi_instrumentation,
    metrics_asgi_app,
    setup_tracing,
)
from domain.services.alias_feedback import AliasFeedbackService, PostgresSettings
from domain.services.product_search import ProductSearchService
from domain.services.recommendation import RecommendationService
from repository.elasticsearch.client import ElasticsearchRepository, ElasticsearchSettings
from repository.neo4j.client import Neo4jRepository, Neo4jSettings
from repository.vector.client import VectorRepository, VectorSettings

logger = logging.getLogger(__name__)
SERVICE_VERSION = "0.1.0"


# ─────────────────────────────────────────────────────────────────────────────
# Trust boundary: chỉ chấp nhận caller identity từ trusted MCP qua mTLS.
# Header (gửi bởi MCP sau khi nó đã verify JWT của agent):
#   X-Agent-Id, X-Merchant-Id, X-Scopes (space-separated), X-Request-Id.
# Domain Service KHÔNG verify JWT — đó là việc của Layer 4.
# ─────────────────────────────────────────────────────────────────────────────
async def get_caller(request: Request) -> Caller:
    headers = request.headers
    agent = headers.get("x-agent-id")
    merchant = headers.get("x-merchant-id")
    request_id = headers.get("x-request-id") or headers.get("traceparent", "unknown")
    if not agent or not merchant:
        raise HTTPException(status_code=400, detail="missing x-agent-id or x-merchant-id")
    scopes = tuple(headers.get("x-scopes", "").split())
    return Caller(agent_id=agent, merchant_id=merchant, scopes=scopes, request_id=request_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing("domain-service")
    neo = Neo4jRepository(
        Neo4jSettings(
            uri=os.environ["NEO4J_URI"],
            user=os.environ["NEO4J_USER"],
            password=os.environ["NEO4J_PASSWORD"],
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        )
    )
    es = ElasticsearchRepository(
        ElasticsearchSettings(
            hosts=[os.environ["ELASTICSEARCH_URL"]],
            api_key=os.environ.get("ELASTICSEARCH_API_KEY"),
            ca_cert_path=os.environ.get("ELASTICSEARCH_CA"),
        )
    )
    vec = VectorRepository(
        VectorSettings(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ.get("QDRANT_API_KEY"),
        )
    )
    alias = AliasFeedbackService(PostgresSettings(dsn=os.environ["POSTGRES_DSN"]))
    await alias.startup()
    app.state.search = ProductSearchService(es=es, vector=vec, neo4j=neo, embed_fn=embed)
    app.state.reco = RecommendationService(neo4j=neo)
    app.state.alias = alias
    app.state.neo = neo
    app.state.es = es
    app.state.vec = vec
    try:
        yield
    finally:
        await alias.shutdown()
        neo.close()
        es.close()
        vec.close()


app = FastAPI(title="semantic-platform domain service", version=SERVICE_VERSION, lifespan=lifespan)
install_fastapi_instrumentation(app)
app.mount("/metrics", metrics_asgi_app())

router = APIRouter(prefix="/v1")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    # Lightweight liveness; deep checks via dedicated probes.
    return HealthResponse(status="ok", neo4j=True, elasticsearch=True, vector_store=True, version=SERVICE_VERSION)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    label_method = request.url.path
    REQUEST_LATENCY.labels(service="domain", method=label_method).observe(elapsed)
    REQUEST_COUNT.labels(service="domain", method=label_method, status=str(response.status_code)).inc()
    return response


@router.post("/products/search", response_model=ProductSearchResponse)
async def products_search(
    req: ProductSearchRequest,
    caller: Caller = Depends(get_caller),
) -> ProductSearchResponse:
    return app.state.search.search(req, caller)


@router.post("/recommendations/toppings", response_model=RecommendationResponse)
async def recommend_toppings(
    req: RecommendationRequest,
    caller: Caller = Depends(get_caller),
) -> RecommendationResponse:
    return app.state.reco.recommend_toppings(req, caller)


@router.get("/customers/{customer_id}", response_model=CustomerProfileResponse)
async def customer_profile(
    customer_id: str,
    days: int = 90,
    caller: Caller = Depends(get_caller),
) -> CustomerProfileResponse:
    rec = app.state.neo.run_single(
        "customer_360",
        merchant_id=caller.merchant_id,
        customer_id=customer_id,
        days=days,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="customer not found")
    return CustomerProfileResponse(
        customer_id=rec["customer_id"],
        segment=rec.get("segment"),
        loyalty_tier=rec.get("loyalty_tier"),
        order_count=int(rec.get("order_count", 0)),
        gmv=float(rec.get("gmv", 0.0)),
        top_products=rec.get("top_products", []),
        top_toppings=rec.get("top_toppings", []),
        request_id=caller.request_id,
    )


@router.post("/aliases/feedback", response_model=AliasFeedbackResponse)
async def alias_feedback(
    req: AliasFeedbackRequest,
    caller: Caller = Depends(get_caller),
) -> AliasFeedbackResponse:
    return await app.state.alias.submit(req, caller)


app.include_router(router)
