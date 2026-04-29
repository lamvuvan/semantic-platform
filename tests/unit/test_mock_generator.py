import io

from tests.fixtures.generate_mock import emit_cypher, generate


def test_generate_default_shape():
    ds = generate(n_merchants=5, n_customers=10, n_orders=20, days=30, seed=1)
    assert len(ds.merchants) == 5
    assert len(ds.customers) == 10
    assert len(ds.orders) == 20
    assert len(ds.products) > 0
    assert len(ds.toppings) == 10
    # Mọi order có ít nhất 1 line
    line_orders = {oid for oid, _ in ds.e_has_line}
    assert line_orders == {o["order_id"] for o in ds.orders}


def test_generate_deterministic():
    a = generate(n_merchants=3, n_customers=5, n_orders=10, seed=42)
    b = generate(n_merchants=3, n_customers=5, n_orders=10, seed=42)
    assert [o["order_id"] for o in a.orders] == [o["order_id"] for o in b.orders]
    assert a.e_line_with_topping == b.e_line_with_topping


def test_emit_cypher_idempotent_uses_merge():
    ds = generate(n_merchants=2, n_customers=3, n_orders=5, seed=7)
    buf = io.StringIO()
    emit_cypher(ds, buf)
    cypher = buf.getvalue()
    # Tất cả phải dùng MERGE để chạy lại an toàn — không có CREATE thuần
    assert "MERGE (n:Merchant" in cypher
    assert "MERGE (n:Product" in cypher
    assert "MERGE (n:Order" in cypher
    assert "CREATE (" not in cypher
    # Có quan hệ cốt lõi
    assert "[:OWNS]" in cypher
    assert "[:PLACED]" in cypher
    assert "[:HAS_LINE]" in cypher
    assert "[:OF_PRODUCT]" in cypher
    assert "[:OF_VARIANT]" in cypher
    # Có topping qty trên ít nhất 1 dòng
    assert "[r:WITH_TOPPING]" in cypher


def test_topping_only_on_drinks():
    ds = generate(n_merchants=5, n_customers=5, n_orders=50, seed=11)
    drink_categories = {"CAT_MILKTEA", "CAT_FRUITTEA", "CAT_PURETEA", "CAT_SPECIALTY", "CAT_SMOOTHIE"}
    product_to_cat = {pid: cid for pid, cid in ds.e_belongs}
    for pid, _tid in ds.e_offers_topping:
        assert product_to_cat[pid] in drink_categories
