FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/mcp.txt ./requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/mcp.txt

COPY pyproject.toml ./
COPY mcp_server ./mcp_server
RUN pip install --no-cache-dir --no-deps .

# MCP_TRANSPORT=http alias cho streamable-http (xem mcp_server.server._resolve_transport).
ENV MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8080 MCP_PATH=/mcp
EXPOSE 8080

# Streamable HTTP chỉ chấp nhận POST /mcp; healthcheck bằng socket connect.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8080), 3).close()" || exit 1

USER 1000:1000
CMD ["python", "-m", "mcp_server.server"]
