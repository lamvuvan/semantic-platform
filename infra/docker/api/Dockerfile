FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/api.txt ./requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/api.txt

COPY pyproject.toml ./
COPY api ./api
COPY mcp ./mcp
COPY agents ./agents
RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000
USER 1000:1000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
