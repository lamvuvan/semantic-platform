import pytest

from agents.text_to_cypher.validator import CypherSafetyError, assert_read_only


@pytest.mark.parametrize("cypher", [
    "MATCH (p:Product) RETURN p LIMIT 10",
    "MATCH (m:Merchant)-[:OWNS]->(p:Product) RETURN m, p",
    "CALL db.index.vector.queryNodes('product_embedding', 5, $emb) YIELD node RETURN node",
])
def test_read_only_passes(cypher):
    assert_read_only(cypher)


@pytest.mark.parametrize("cypher", [
    "CREATE (n:Product {id: 1})",
    "MATCH (p:Product) DELETE p",
    "MATCH (p:Product) SET p.price = 0",
    "MERGE (p:Product {id: 'x'})",
    "MATCH (p) DETACH DELETE p",
    "CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'DELETE n', {})",
])
def test_destructive_blocked(cypher):
    with pytest.raises(CypherSafetyError):
        assert_read_only(cypher)


def test_unallowed_procedure_blocked():
    with pytest.raises(CypherSafetyError):
        assert_read_only("CALL apoc.export.json.all('out.json', {}) YIELD file RETURN file")
