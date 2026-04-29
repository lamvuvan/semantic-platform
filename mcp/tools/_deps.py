"""Lazy dependencies cho MCP tools — driver Neo4j, retriever, redis."""
from __future__ import annotations

import os
from functools import lru_cache

from neo4j import Driver, GraphDatabase

from agents.retrieval import ContextRetriever


@lru_cache(maxsize=1)
def get_driver() -> Driver:
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )


@lru_cache(maxsize=1)
def get_retriever() -> ContextRetriever:
    return ContextRetriever(
        driver=get_driver(),
        database=os.environ.get("NEO4J_DATABASE", "neo4j"),
    )


def get_database() -> str:
    return os.environ.get("NEO4J_DATABASE", "neo4j")
