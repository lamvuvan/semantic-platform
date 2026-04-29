FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements/base.txt requirements/loaders.txt ./requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/loaders.txt

COPY pyproject.toml ./
COPY loaders ./loaders
RUN pip install --no-cache-dir --no-deps .

USER 1000:1000
ENTRYPOINT ["python", "-m"]
