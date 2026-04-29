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

# MCP_TRANSPORT=http là alias cho streamable-http (xem mcp/server.py:_resolve_transport).
# Endpoint Streamable HTTP duy nhất là $MCP_PATH (mặc định /mcp), chỉ chấp nhận POST JSON-RPC.
ENV MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8080 MCP_PATH=/mcp
EXPOSE 8080

# Healthcheck: chỉ kiểm tra listener đang mở port — không thể GET /mcp vì
# Streamable HTTP yêu cầu POST với body JSON-RPC hợp lệ.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import socket,sys; s=socket.create_connection(('127.0.0.1', 8080), 3); s.close()" || exit 1

USER 1000:1000
CMD ["python", "-m", "mcp.server"]
