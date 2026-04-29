from __future__ import annotations

from agents.text_to_cypher.prompt import SCHEMA_HINT
from mcp.auth.oidc import Caller


def run(caller: Caller) -> dict:
    return {"schema": SCHEMA_HINT.strip()}
