// Layer 1 — Neo4j 5.x Community schema cho KG ngành F&B / KiotViet.
// Áp dụng idempotent — mọi lệnh dùng IF NOT EXISTS.
// Tham chiếu kiến trúc: README.md "AI Agent Integration Architecture".

// ─────────────────────────────────────────────────────────────────────────────
// Unique constraints
// ─────────────────────────────────────────────────────────────────────────────
CREATE CONSTRAINT merchant_id_unique IF NOT EXISTS
  FOR (m:Merchant) REQUIRE m.merchant_id IS UNIQUE;

CREATE CONSTRAINT category_id_unique IF NOT EXISTS
  FOR (c:Category) REQUIRE c.category_id IS UNIQUE;

CREATE CONSTRAINT product_id_unique IF NOT EXISTS
  FOR (p:Product) REQUIRE p.product_id IS UNIQUE;

CREATE CONSTRAINT variant_id_unique IF NOT EXISTS
  FOR (v:ProductVariant) REQUIRE v.variant_id IS UNIQUE;

CREATE CONSTRAINT topping_id_unique IF NOT EXISTS
  FOR (t:Topping) REQUIRE t.topping_id IS UNIQUE;

CREATE CONSTRAINT customer_id_unique IF NOT EXISTS
  FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;

CREATE CONSTRAINT order_id_unique IF NOT EXISTS
  FOR (o:Order) REQUIRE o.order_id IS UNIQUE;

CREATE CONSTRAINT line_id_unique IF NOT EXISTS
  FOR (l:OrderLine) REQUIRE l.line_id IS UNIQUE;

CREATE CONSTRAINT alias_id_unique IF NOT EXISTS
  FOR (a:Alias) REQUIRE a.alias_id IS UNIQUE;

// ─────────────────────────────────────────────────────────────────────────────
// Range / composite indexes phục vụ traversal
// ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX product_merchant IF NOT EXISTS
  FOR (p:Product) ON (p.merchant_id);

CREATE INDEX order_ts IF NOT EXISTS
  FOR (o:Order) ON (o.ts);

CREATE INDEX customer_segment IF NOT EXISTS
  FOR (c:Customer) ON (c.segment);

// ─────────────────────────────────────────────────────────────────────────────
// Lưu ý: KHÔNG tạo full-text index ở Neo4j — Elasticsearch đảm nhận lexical.
// KHÔNG tạo vector index ở Neo4j — Qdrant/pgvector đảm nhận semantic.
// Neo4j chỉ giữ vai trò graph store thuần (Layer 1).
// ─────────────────────────────────────────────────────────────────────────────
