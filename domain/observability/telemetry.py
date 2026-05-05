"""OpenTelemetry + Prometheus setup cho Domain Service.

Trace từ MCP đi qua header `traceparent` → propagate vào Neo4j/ES/Vector calls.
Metric Prometheus expose tại /metrics.
"""
from __future__ import annotations

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, make_asgi_app

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "domain_request_total",
    "Số request vào Domain Service",
    ["service", "method", "status"],
)
REQUEST_LATENCY = Histogram(
    "domain_request_seconds",
    "Latency Domain Service",
    ["service", "method"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def setup_tracing(service_name: str = "domain-service") -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if not endpoint:
        logger.info("OTLP endpoint not set — skipping tracing setup")
        return
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    logger.info("OTel tracing enabled — endpoint=%s", endpoint)


def install_fastapi_instrumentation(app) -> None:  # type: ignore[no-untyped-def]
    FastAPIInstrumentor.instrument_app(app)


def metrics_asgi_app():  # type: ignore[no-untyped-def]
    return make_asgi_app()
