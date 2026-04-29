// FnB Knowledge Graph — Schema (Neo4j 5.x Community)
// Tham chiếu: docs/PLAN.md §1
//
// Áp dụng idempotent: lệnh `IF NOT EXISTS` cho phép chạy lại an toàn.

// ─────────────────────────────────────────────────────────────
// Unique constraints (cũng tạo index ngầm)
// ─────────────────────────────────────────────────────────────
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

// ─────────────────────────────────────────────────────────────
// Range / composite indexes
// ─────────────────────────────────────────────────────────────
CREATE INDEX product_name_normalized IF NOT EXISTS
  FOR (p:Product) ON (p.name_normalized);

CREATE INDEX order_ts IF NOT EXISTS
  FOR (o:Order) ON (o.ts);

CREATE INDEX customer_segment IF NOT EXISTS
  FOR (c:Customer) ON (c.segment);

// ─────────────────────────────────────────────────────────────
// Full-text indexes (Lucene)
// ─────────────────────────────────────────────────────────────
CREATE FULLTEXT INDEX product_fulltext IF NOT EXISTS
  FOR (p:Product) ON EACH [p.name, p.description];

CREATE FULLTEXT INDEX topping_fulltext IF NOT EXISTS
  FOR (t:Topping) ON EACH [t.name];

// ─────────────────────────────────────────────────────────────
// Vector index (HNSW — Neo4j Community 5.13+)
// dim=384 cho paraphrase-multilingual-MiniLM-L12-v2
// ─────────────────────────────────────────────────────────────
CREATE VECTOR INDEX product_embedding IF NOT EXISTS
  FOR (p:Product) ON p.embedding
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 384,
      `vector.similarity_function`: 'cosine'
    }
  };
