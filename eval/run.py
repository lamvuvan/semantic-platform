"""Eval harness: chạy gold set qua MCP tools, đo accuracy.

Yêu cầu Neo4j seed bằng dataset eval (xem tests/integration/seed.cypher).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp.auth.oidc import Caller
from mcp.registry.loader import load_registry

GOLD = Path(__file__).with_name("gold_qa.jsonl")


def fake_caller() -> Caller:
    return Caller(sub="eval", scopes=frozenset({"merchant.read", "customer.read", "recommendation.read", "analytics.read", "data.discover", "public"}), tenant_merchant_id=None, raw={})


def evaluate(threshold: float) -> int:
    tools = {t.name: t for t in load_registry()}
    total = 0
    passed = 0
    fails = []
    caller = fake_caller()
    for line in GOLD.read_text().splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        total += 1
        spec = tools[item["tool"]]
        try:
            result = spec.handler(caller, **item["args"])
            ok = all(key in json.dumps(result, default=str) for key in item["expected_contains"])
        except Exception as e:
            ok = False
            result = {"error": str(e)}
        if ok:
            passed += 1
        else:
            fails.append({"id": item["id"], "result": result})

    accuracy = passed / total if total else 0.0
    print(json.dumps({"total": total, "passed": passed, "accuracy": accuracy, "failures": fails[:5]}, indent=2, default=str))
    return 0 if accuracy >= threshold else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    sys.exit(evaluate(args.threshold))


if __name__ == "__main__":
    main()
