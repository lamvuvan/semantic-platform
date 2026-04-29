"""Derive `SIMILAR_TO` (vector kNN) và `FAVORS` (co-purchase) sau khi load xong."""
from __future__ import annotations

import logging
import os

from loaders.common.neo4j_writer import Neo4jConfig, driver

logger = logging.getLogger(__name__)

# kNN bằng vector index — Community 5.x
SIMILAR_TO = """
MATCH (p:Product)
CALL db.index.vector.queryNodes('product_embedding', $k, p.embedding)
YIELD node AS sim, score
WHERE sim <> p AND score > $threshold
MERGE (p)-[r:SIMILAR_TO]->(sim)
SET r.score = score, r.computed_at = datetime()
"""

# FAVORS từ behavior 90 ngày gần nhất.
FAVORS = """
MATCH (c:Customer)-[:PLACED]->(o:Order)-[:HAS_LINE]->(:OrderLine)-[:OF_PRODUCT]->(p:Product)
WHERE o.ts > datetime() - duration({days: 90})
WITH c, p, count(*) AS freq
WHERE freq >= $min_freq
MERGE (c)-[r:FAVORS]->(p)
SET r.score = freq, r.computed_at = datetime()
"""


def main() -> None:
    cfg = Neo4jConfig(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
        database=os.environ.get("NEO4J_DATABASE", "neo4j"),
    )
    with driver(cfg) as drv, drv.session(database=cfg.database) as session:
        logger.info("deriving SIMILAR_TO …")
        session.run(SIMILAR_TO, k=20, threshold=0.75)
        logger.info("deriving FAVORS …")
        session.run(FAVORS, min_freq=3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    main()
