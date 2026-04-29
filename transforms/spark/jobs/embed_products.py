"""Sinh embedding cho Product mới/thay đổi và xuất CSV cho loader.

Chạy trên GPU VM:
    spark-submit --master spark://spark-master:7077 \
        transforms/spark/jobs/embed_products.py \
        --gold-db semantic_platform --output s3a://kg-staging/embeddings/dt=...
"""
from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, FloatType

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("embed_products")
        .enableHiveSupport()
        .getOrCreate()
    )

    products = spark.table(f"{args.gold_db}.kg_nodes_product").select(
        "product_id", "name", "description"
    )

    @F.pandas_udf(ArrayType(FloatType()))
    def encode(names, descriptions):  # type: ignore[no-untyped-def]
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
        texts = (names.fillna("") + ". " + descriptions.fillna("")).tolist()
        vectors = model.encode(texts, batch_size=args.batch_size, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]

    out = products.withColumn("embedding", encode("name", "description"))
    (
        out.select("product_id", "embedding")
        .write.mode("overwrite")
        .option("header", True)
        .csv(args.output)
    )
    spark.stop()


if __name__ == "__main__":
    main()
