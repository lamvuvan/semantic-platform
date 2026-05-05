FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/domain.txt ./requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/domain.txt

COPY pyproject.toml ./
COPY domain ./domain
COPY repository ./repository
RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000
USER 1000:1000
CMD ["uvicorn", "domain.main:app", "--host", "0.0.0.0", "--port", "8000"]
