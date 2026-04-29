FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY api ./api
COPY mcp ./mcp
COPY agents ./agents

RUN pip install --upgrade pip && pip install ".[api]"

EXPOSE 8000
USER 1000:1000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
