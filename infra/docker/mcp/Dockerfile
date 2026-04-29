FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY mcp ./mcp
COPY agents ./agents

RUN pip install --upgrade pip && \
    pip install ".[mcp]"

ENV MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

USER 1000:1000
CMD ["python", "-m", "mcp.server"]
