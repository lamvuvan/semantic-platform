"""Internal admin/BI API — FastAPI + Strawberry GraphQL.

Chỉ dành cho dashboard nội bộ. Client AI/agent dùng MCP server (xem mcp/server.py).
"""
from __future__ import annotations

import os

import strawberry
from fastapi import FastAPI, Header, HTTPException
from neo4j import GraphDatabase
from strawberry.fastapi import GraphQLRouter

from mcp.auth.oidc import AuthError, OidcVerifier

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)
DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")
verifier = OidcVerifier()


@strawberry.type
class Product:
    product_id: str
    name: str
    description: str | None = None
    base_price: float | None = None


@strawberry.type
class Query:
    @strawberry.field
    def product(self, product_id: str) -> Product | None:
        with driver.session(database=DATABASE) as s:
            rec = s.run("MATCH (p:Product {product_id: $pid}) RETURN p", pid=product_id).single()
            if rec is None:
                return None
            data = dict(rec["p"])
            return Product(
                product_id=data["product_id"],
                name=data.get("name", ""),
                description=data.get("description"),
                base_price=data.get("base_price"),
            )

    @strawberry.field
    def search_products(self, query: str, top_k: int = 10) -> list[Product]:
        cypher = """
        CALL db.index.fulltext.queryNodes('product_fulltext', $q) YIELD node, score
        RETURN node LIMIT $k
        """
        with driver.session(database=DATABASE) as s:
            return [
                Product(
                    product_id=dict(r["node"]).get("product_id", ""),
                    name=dict(r["node"]).get("name", ""),
                    description=dict(r["node"]).get("description"),
                    base_price=dict(r["node"]).get("base_price"),
                )
                for r in s.run(cypher, q=query, k=top_k)
            ]


schema = strawberry.Schema(Query)
graphql = GraphQLRouter(schema)
app = FastAPI(title="semantic-platform admin API")


@app.middleware("http")
async def auth_mw(request, call_next):  # type: ignore[no-untyped-def]
    if request.url.path.startswith("/healthz"):
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        verifier.verify(auth.split(" ", 1)[1].strip())
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    return await call_next(request)


app.include_router(graphql, prefix="/graphql")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
