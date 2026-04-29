"""Nạp vector embedding của Product vào Neo4j vector index."""
from __future__ import annotations

import argparse
import json
import logging
import os

from loaders.common.neo4j_writer import Neo4jConfig, driver, upsert_vector
from loaders.common.s3_reader import read_csv_objects, s3_client

logger = logging.getLogger(__name__)


def parse_embedding(value: str) -> list[float]:
    return [float(x) for x in json.loads(value)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()

    cfg = Neo4jConfig(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
        database=os.environ.get("NEO4J_DATABASE", "neo4j"),
    )
    s3 = s3_client(
        endpoint_url=os.environ["S3_ENDPOINT"],
        access_key=os.environ["S3_ACCESS_KEY"],
        secret_key=os.environ["S3_SECRET_KEY"],
    )

    rows = []
    for raw in read_csv_objects(s3, args.bucket, args.prefix):
        rows.append({"product_id": raw["product_id"], "embedding": parse_embedding(raw["embedding"])})
    logger.info("loaded %s embeddings", len(rows))

    with driver(cfg) as drv:
        n = upsert_vector(drv, cfg.database, "Product", "product_id", rows)
    logger.info("upserted %s vectors", n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    main()
