"""Đọc CSV gold layer từ S3-compatible nội bộ."""
from __future__ import annotations

import csv
import io
from typing import Iterator

import boto3
from botocore.config import Config


def s3_client(endpoint_url: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )


def read_csv_objects(client, bucket: str, prefix: str) -> Iterator[dict]:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if not obj["Key"].endswith(".csv"):
                continue
            body = client.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
            reader = csv.DictReader(io.StringIO(body.decode("utf-8")))
            yield from reader
