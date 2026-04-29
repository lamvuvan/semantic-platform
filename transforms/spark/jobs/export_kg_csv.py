"""Export gold layer ra CSV để loader nạp vào Neo4j.

Chạy: spark-submit transforms/spark/jobs/export_kg_csv.py \
    --gold-db semantic_platform \
    --output s3a://kg-staging/dt=2026-04-29/
"""
from __future__ import annotations

import argparse

from pyspark.sql import SparkSession

NODE_TABLES = [
    "kg_nodes_merchant",
    "kg_nodes_category",
    "kg_nodes_product",
    "kg_nodes_product_variant",
    "kg_nodes_topping",
    "kg_nodes_customer",
    "kg_nodes_order",
    "kg_nodes_order_line",
]

EDGE_TABLES = [
    "kg_edges_merchant_owns_product",
    "kg_edges_product_category",
    "kg_edges_product_variant",
    "kg_edges_product_topping",
    "kg_edges_customer_placed_order",
    "kg_edges_order_placed_at_merchant",
    "kg_edges_order_has_line",
    "kg_edges_line_of_product",
    "kg_edges_line_of_variant",
    "kg_edges_line_with_topping",
]


def export(spark: SparkSession, db: str, output: str) -> None:
    for table in NODE_TABLES + EDGE_TABLES:
        df = spark.table(f"{db}.{table}")
        target = f"{output.rstrip('/')}/{table}"
        (
            df.coalesce(8)
            .write.mode("overwrite")
            .option("header", True)
            .csv(target)
        )
        print(f"exported {table} -> {target} ({df.count()} rows)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-db", required=True)
    parser.add_argument("--output", required=True, help="s3a://bucket/path/")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("export_kg_csv")
        .enableHiveSupport()
        .getOrCreate()
    )
    export(spark, args.gold_db, args.output)
    spark.stop()


if __name__ == "__main__":
    main()
