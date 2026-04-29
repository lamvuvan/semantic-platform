FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY loaders ./loaders

RUN pip install --upgrade pip && pip install ".[loaders]"

USER 1000:1000
ENTRYPOINT ["python", "-m"]
