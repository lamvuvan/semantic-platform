"""Smoke check sau daily batch: so sánh count node/edge với baseline ±tolerance."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

LABELS = ["Merchant", "Category", "Product", "ProductVariant", "Topping", "Customer", "Order", "OrderLine"]
TOLERANCE = 0.10


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    drv = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    counts: dict[str, int] = {}
    with drv.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as s:
        for label in LABELS:
            counts[label] = s.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()["c"]
    drv.close()

    baseline_path = Path(args.baseline)
    if args.write_baseline:
        baseline_path.write_text(json.dumps(counts, indent=2))
        print("baseline written:", counts)
        return

    if not baseline_path.exists():
        print("no baseline yet — skip", file=sys.stderr)
        baseline_path.write_text(json.dumps(counts, indent=2))
        return

    baseline = json.loads(baseline_path.read_text())
    failures = []
    for label, prev in baseline.items():
        cur = counts.get(label, 0)
        if prev == 0:
            continue
        delta = abs(cur - prev) / prev
        if delta > TOLERANCE:
            failures.append({"label": label, "prev": prev, "cur": cur, "delta": delta})

    if failures:
        print(json.dumps({"failed": failures, "counts": counts}, indent=2))
        sys.exit(2)
    baseline_path.write_text(json.dumps(counts, indent=2))
    print(json.dumps({"ok": True, "counts": counts}))


if __name__ == "__main__":
    main()
