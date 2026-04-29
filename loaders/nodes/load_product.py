"""Load Product nodes vào Neo4j từ CSV gold."""
from __future__ import annotations

import argparse
import logging
import os

from loaders.common.neo4j_writer import Neo4jConfig, driver, merge_nodes
from loaders.common.s3_reader import read_csv_objects, s3_client

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True, help="kg-staging/dt=.../kg_nodes_product/")
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

    rows = list(read_csv_objects(s3, args.bucket, args.prefix))
    logger.info("loaded %s product rows from s3", len(rows))

    with driver(cfg) as drv:
        n = merge_nodes(drv, cfg.database, "Product", "product_id", rows)
    logger.info("merged %s Product nodes", n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    main()
