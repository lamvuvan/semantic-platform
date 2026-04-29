"""Load OrderLine relationships: HAS_LINE, OF_PRODUCT, OF_VARIANT, WITH_TOPPING."""
from __future__ import annotations

import argparse
import logging
import os

from loaders.common.neo4j_writer import Neo4jConfig, driver, merge_edges
from loaders.common.s3_reader import read_csv_objects, s3_client

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix-base", required=True, help="kg-staging/dt=.../")
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

    base = args.prefix_base.rstrip("/")
    edge_jobs = [
        ("kg_edges_order_has_line", "Order", "order_id", "HAS_LINE", "OrderLine", "line_id"),
        ("kg_edges_line_of_product", "OrderLine", "line_id", "OF_PRODUCT", "Product", "product_id"),
        ("kg_edges_line_of_variant", "OrderLine", "line_id", "OF_VARIANT", "ProductVariant", "variant_id"),
        ("kg_edges_line_with_topping", "OrderLine", "line_id", "WITH_TOPPING", "Topping", "topping_id"),
    ]

    with driver(cfg) as drv:
        for table, src_label, src_key, rel_type, dst_label, dst_key in edge_jobs:
            rows = list(read_csv_objects(s3, args.bucket, f"{base}/{table}/"))
            logger.info("loading %s -> %s rows", table, len(rows))
            n = merge_edges(
                drv,
                cfg.database,
                src_label=src_label,
                src_key=src_key,
                rel_type=rel_type,
                dst_label=dst_label,
                dst_key=dst_key,
                rows=rows,
            )
            logger.info("merged %s rels of type %s", n, rel_type)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    main()
