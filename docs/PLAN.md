# FnB Knowledge Graph — Kế hoạch triển khai MVP Production-Ready

## Context

Dự án `semantic-platform` xây dựng lớp ngữ nghĩa (semantic layer) trên data platform hiện hữu (Product 360, Merchant 360, Classified Product) để cung cấp ngữ cảnh phong phú cho AI agent ngành F&B.

Hiện trạng: repo greenfield, chỉ có `CLAUDE.md`. Cần thiết kế end-to-end từ ontology, ingestion, KG store đến API/AI để đạt MVP production-ready.

Quyết định đã chốt với người dùng:
- **KG engine**: **Neo4j 5.x Community Edition** (Property Graph) — có so sánh với Apache AGE ở §2.0
- **Hạ tầng**: **On-premise hoàn toàn**, KHÔNG dùng Kubernetes — chạy trực tiếp trên VM/bare-metal nội bộ với Docker + Ansible
- **Object storage**: hệ thống **S3-compatible** nội bộ (đã có sẵn)
- **CI/CD & deployment**: **GitLab CI + GitLab Runner** (self-hosted)
- **Data Quality**: KHÔNG nằm trong scope — Data Platform thượng nguồn (Product 360, Merchant 360, Classified Product) đã đảm bảo chất lượng dữ liệu
- **Freshness**: Daily batch
- **Truy cập từ client/AI**: qua **MCP server + Tool registry** — client KHÔNG truy vấn Cypher trực tiếp
- **MVP goals**: (1) Natural language Q&A (Text-to-Cypher / GraphRAG), (2) Recommendation cross-sell/upsell, (3) Semantic search & data discovery

> **Lưu ý ontology**: `OrderLine` ≠ `Invoice`. `OrderLine` là dòng chi tiết bán hàng (sản phẩm + variant + topping + qty + giá) phục vụ phân tích sản phẩm/khách hàng. `Invoice` là chứng từ tài chính (VAT, MST), thuộc domain kế toán — không nằm trong scope MVP. Nếu sau này cần, bổ sung node `Invoice -[:BILLS]-> Order` riêng.

---

## 1. Ontology F&B (Schema KG)

### 1.1 Core entities (Node labels)
- `Merchant` — properties: merchant_id, name, brand, region, segment, opened_at
- `Category` — taxonomy phân loại từ Classified Product (đa cấp: Beverage > Tea > Milk Tea)
- `Product` — sản phẩm gốc (master): product_id, name, name_normalized, description, base_price, status
- `ProductVariant` — biến thể (size S/M/L, nhiệt độ hot/cold, đường, đá): variant_id, attributes (map), price_delta
- `Topping` — topping/add-on: topping_id, name, price, category (pearl/jelly/cheese/...)
- `Customer` — khách hàng: customer_id, hashed_phone, segment, loyalty_tier, signup_at, region
- `Order` — đơn hàng: order_id, ts, channel (dine-in/takeaway/delivery), payment_method, total, currency
- `OrderLine` — dòng đơn (reified relationship để gắn variant + topping): line_id, qty, unit_price, discount

### 1.2 Relationships
- `(Merchant)-[:OWNS]->(Product)`
- `(Product)-[:BELONGS_TO]->(Category)`
- `(Product)-[:HAS_VARIANT]->(ProductVariant)`
- `(Product)-[:OFFERS_TOPPING]->(Topping)`
- `(Order)-[:PLACED_AT]->(Merchant)`
- `(Customer)-[:PLACED]->(Order)`
- `(Order)-[:HAS_LINE]->(OrderLine)`
- `(OrderLine)-[:OF_PRODUCT]->(Product)`
- `(OrderLine)-[:OF_VARIANT]->(ProductVariant)`
- `(OrderLine)-[:WITH_TOPPING {qty}]->(Topping)`
- `(Product)-[:SIMILAR_TO {score}]->(Product)` — derived từ embedding
- `(Customer)-[:FAVORS {score}]->(Product)` — derived từ behavior

### 1.3 Constraints & indexes (Neo4j Community 5.x)
- Unique constraints: `merchant_id, product_id, variant_id, topping_id, customer_id, order_id, line_id`
- Composite range index: `(Product.name_normalized, Merchant.merchant_id)`
- **Vector index**: `Product.embedding (dim=384, cosine)` — Community 5.13+ hỗ trợ HNSW vector index
- Full-text index: `Product.name, Product.description`
- **Lưu ý Community**: không có fine-grained RBAC tại DB — RBAC/multi-tenant sẽ enforce ở **MCP layer** (xem §2.4); không có causal cluster — HA bằng single primary + backup + warm standby (xem §5).

---

## 2. Kiến trúc & Thành phần công nghệ

### 2.0 So sánh Neo4j Community vs Apache AGE (đánh giá lựa chọn KG core)

| Tiêu chí | **Neo4j 5.x Community** | **Apache AGE (PostgreSQL extension)** |
|---|---|---|
| License | GPLv3 — miễn phí, dùng on-prem thoải mái | Apache 2.0 — miễn phí |
| Mô hình | Property graph native | Property graph trên Postgres (mỗi graph = 1 schema) |
| Ngôn ngữ truy vấn | Cypher đầy đủ + GQL | openCypher subset (còn thiếu một số mệnh đề, MERGE phức tạp) |
| Hiệu năng traversal sâu | Tối ưu, native graph storage, index-free adjacency | Khá hơn SQL JOIN nhưng kém Neo4j khi traversal >3 hop |
| Vector index | **Có** built-in HNSW từ 5.13 (Community) | Chưa native — kết hợp `pgvector` cùng Postgres |
| Full-text index | Có (Lucene) | Dùng Postgres `tsvector` (mạnh, quen thuộc) |
| HA / Cluster | **Không có causal cluster** (chỉ Enterprise) → single primary + backup/warm standby | Postgres streaming replication/Patroni — vận hành quen thuộc |
| RBAC | **Không fine-grained** (chỉ Enterprise) → enforce tại MCP layer | Postgres role/grant đầy đủ |
| Multi-database | Không (chỉ DB mặc định) | Schema-level isolation tự nhiên trong Postgres |
| Hệ sinh thái AI | APOC Core, GDS Community, neo4j-graphrag-python, LangChain/LlamaIndex first-class, Neo4j MCP có sẵn | Nhỏ hơn, ít connector AI tích hợp sẵn |
| Tích hợp dữ liệu quan hệ | Cần ETL ra ngoài | SQL + Cypher trong cùng DB, JOIN sang bảng quan hệ thuận tiện |
| Trưởng thành | Rất cao, nhiều case study production | Đang phát triển nhanh, ít case lớn ngoài Bitnine |
| Tooling | Neo4j Browser, neosemantics (RDF) — Bloom là Enterprise | psql, pgAdmin — quen thuộc nhưng không có graph viz native |
| Phù hợp khi | Workload graph là first-class, traversal sâu, AI/GraphRAG nhiều | Đã chuẩn hóa Postgres, muốn 1 stack, traversal vừa phải |

**Khuyến nghị**: Dùng **Neo4j 5.x Community** cho MVP vì:
1. Vector index HNSW có sẵn ở Community 5.13+ → đủ cho hybrid retrieval.
2. Cypher đầy đủ + APOC Core + GDS Community → triển khai recommendation (similarity, co-purchase) không cần Enterprise.
3. Hệ sinh thái GraphRAG/MCP/LangChain first-class → tiết kiệm vài tuần phát triển AI agent.
4. License GPLv3 cho self-host on-prem hoàn toàn miễn phí.

**Đánh đổi cần xử lý** (vì là Community):
- Không có HA cluster → **HA bằng single primary + backup `neo4j-admin database backup` định kỳ + 1 warm standby restore offline** (RTO ~30 phút).
- Không có fine-grained RBAC tại DB → enforce **toàn bộ RBAC/multi-tenant ở MCP layer** với read-only DB user duy nhất.
- Không có multi-database → dùng 1 DB duy nhất, namespace logic bằng node label/property.

**Phương án dự phòng**: Giữ adapter pattern ở `loaders/` và `mcp/tools/` để có thể chuyển sang **Apache AGE** nếu Neo4j Community không đáp ứng (vd: cần HA cluster mạnh hơn mà không muốn Enterprise). Trong P1 sẽ benchmark cả hai trên dataset thật (Order 6 tháng) để có số liệu quyết định cuối cùng.

### 2.1 Layered architecture
```
┌──────────────────────────────────────────────────────────┐
│ Client / AI Agents  (Claude Desktop · custom agents · BI) │
│       ↕ MCP protocol (stdio/HTTP+SSE)                    │
├──────────────────────────────────────────────────────────┤
│ MCP Server + Tool Registry  (FastMCP / Python)           │
│  • Declarative tools (YAML)  • RBAC per tool             │
│  • Read-only Cypher templates  • Audit log               │
├──────────────────────────────────────────────────────────┤
│ Context Retrieval Layer                                   │
│  • Hybrid retriever (vector + graph + full-text)         │
│  • Subgraph extractor  • Re-ranker  • Context budgeter   │
│  • Cache (Redis)                                          │
├──────────────────────────────────────────────────────────┤
│ Internal Service Layer  (FastAPI + GraphQL — admin/BI)   │
│  • Auth (OIDC/Keycloak)  • Query templates               │
├──────────────────────────────────────────────────────────┤
│ Knowledge Graph  (Neo4j 5.x Community — single primary)  │
│  • Property graph  • HNSW vector index  • APOC + GDS     │
├──────────────────────────────────────────────────────────┤
│ Transform & Load  (Spark + dbt + Python loader)          │
│  • Bronze → Silver → Gold → Graph                        │
├──────────────────────────────────────────────────────────┤
│ Orchestration  (Apache Airflow — CeleryExecutor)         │
├──────────────────────────────────────────────────────────┤
│ Storage  (S3-compatible nội bộ · PostgreSQL meta · Redis)│
├──────────────────────────────────────────────────────────┤
│ Sources  Product 360 · Merchant 360 · Classified Product │
└──────────────────────────────────────────────────────────┘
```

Tất cả thành phần chạy trên VM/bare-metal nội bộ với **Docker** (compose) + **Ansible** cho cấu hình. Không có Kubernetes. Không có dịch vụ cloud.

### 2.2 Technology stack (on-premise hoàn toàn, không K8s)
| Tầng | Công nghệ | Vai trò |
|---|---|---|
| Orchestration | Apache Airflow 2.9 (**CeleryExecutor**, Redis broker) trên VM | Lập lịch DAG daily batch |
| Compute | Apache Spark 3.5 **standalone cluster** trên VM (1 master + N worker) | ETL khối lượng lớn (orders) |
| Modeling | dbt-core (Spark adapter) | Silver→Gold transforms, lineage |
| KG | **Neo4j 5.x Community** (single primary VM + warm standby) | Graph store + vector index |
| Loader | Python + `neo4j` driver + APOC `apoc.periodic.iterate` | Bulk upsert + derived edges |
| Object store | **S3-compatible nội bộ** (đã có sẵn) | Bronze/Silver parquet, backup Neo4j |
| Metadata | PostgreSQL (HA streaming replication, Patroni) | Airflow + dbt + app metadata + audit |
| Embeddings | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) chạy trên GPU VM | Đa ngôn ngữ VN/EN, on-prem |
| LLM | **Self-host hoàn toàn**: vLLM/Ollama serving Qwen2.5-14B-Instruct + BGE reranker trên GPU VM | NL→Cypher, GraphRAG, không gửi dữ liệu ra ngoài |
| MCP server | FastMCP (Python) + tool registry YAML — chạy bằng Docker, sau Nginx reverse proxy | Cổng truy cập duy nhất cho AI client |
| Cache | Redis (master + replica + Sentinel) | Cache context retrieval, rate-limit, Airflow Celery broker |
| API (admin/BI) | FastAPI + Strawberry GraphQL | Truy vấn KG cho admin/BI nội bộ |
| Auth | Keycloak (OIDC, self-hosted) | RBAC/multi-tenant enforce ở MCP layer |
| Lineage | OpenLineage → Marquez (self-hosted) | Truy vết nguồn → KG |
| Observability | Prometheus + Grafana + Loki + node_exporter + OpenTelemetry collector | Metrics/logs/traces |
| Provisioning | **Ansible** playbooks | Cài OS, Docker, services, cấu hình |
| Container runtime | **Docker / docker-compose** | Đóng gói service (MCP, API, loaders, Airflow workers) |
| Reverse proxy / LB | Nginx + keepalived (VRRP) | TLS termination, LB, failover |
| CI/CD | **GitLab CI + GitLab Runner** (self-hosted, shell + docker executor) | Build, test, scan, deploy qua Ansible |
| Secrets | HashiCorp Vault (self-hosted) | Token, password, API key |

### 2.3 Context Retrieval Layer (chi tiết)

Mục tiêu: nhận một câu hỏi/intent từ MCP tool, trả về một **context object** đã được chọn lọc + cô đọng (nodes, edges, summaries) đủ cho LLM trả lời chính xác mà không quá ngân sách token.

**Pipeline 5 bước**:

1. **Intent & Entity Resolution**
   - LLM nhỏ (Qwen2.5-7B) phân tích câu hỏi → intent (lookup / aggregate / recommend / compare) + entity mentions.
   - Entity linker: fuzzy match + vector search trên `Product.embedding`, `Customer.hashed_phone`, `Merchant.name` → trả về candidate IDs với score.

2. **Hybrid Retrieval** (3 kênh chạy song song):
   - **Vector**: top-k Product/Topping theo cosine similarity (Neo4j `db.index.vector.queryNodes`).
   - **Full-text**: Neo4j `db.index.fulltext.queryNodes` cho name/description.
   - **Graph**: Cypher template tham số hoá quanh các entity đã link (vd: 1-2 hop neighbors, time-windowed orders).

3. **Subgraph Extraction**
   - Mở rộng từ entity hạt giống theo policy theo intent (vd: với `recommend` → mở rộng đến `Customer-PLACED-Order-OF_PRODUCT-Product-SIMILAR_TO`, depth ≤ 3).
   - Giới hạn max nodes/edges (default 200/500) để chống explosion.

4. **Re-ranking & Compression**
   - Cross-encoder reranker (BGE-reranker-v2-m3) chấm lại top-k.
   - Summarizer (template-based + LLM cho long context): biến subgraph thành mô tả ngắn (vd: "Khách hàng C123 đặt 12 đơn 30 ngày qua, top 3 món: Trà sữa M, Hồng trà L, Matcha M; topping ưa thích: trân châu đen, phô mai").
   - Context budget: tính token, drop theo score nếu vượt ngân sách (default 4k token).

5. **Context Object** (JSON, version-stable):
   ```json
   {
     "intent": "recommend_topping",
     "entities": [{"type":"Customer","id":"C123","confidence":0.94}],
     "subgraph": {"nodes":[...], "edges":[...]},
     "summaries": ["..."],
     "evidence_cypher": "MATCH ... RETURN ...",
     "freshness_ts": "2026-04-28T07:00:00Z",
     "ttl_s": 3600
   }
   ```
   - Cache trong Redis theo `(intent, entity_ids, params)` với TTL = freshness next batch.
   - Mọi context trả về kèm `evidence_cypher` để debug/audit.

**Retrieval policies** (đặt trong `agents/retrieval/policies.yaml`): mỗi intent có depth, k, edge filters, summarization template riêng — tách rời khỏi code để PO/SME có thể tinh chỉnh.

### 2.4 MCP Server & Tool Registry (cổng client/AI duy nhất)

**Nguyên tắc**: Client (Claude Desktop, custom agent, n8n, BI plugin) không bao giờ chạm Cypher hay GraphQL trực tiếp — chỉ gọi tool qua MCP. Lợi ích:
- Governance & RBAC tập trung tại tool boundary.
- Schema KG có thể tiến hoá mà không vỡ client.
- Audit log chuẩn hoá theo tool call.
- Dễ thay backend (Neo4j → Apache AGE) mà client không đổi.

**Kiến trúc MCP server**:
- Triển khai bằng **FastMCP** (Python) — hỗ trợ stdio cho desktop client và **HTTP+SSE** cho client mạng nội bộ.
- Mỗi tool = 1 hàm Python được wrap bởi metadata trong YAML (tool registry).
- Mỗi tool gọi xuống Context Retrieval Layer rồi format kết quả MCP-compliant (`content`, `isError`, structured JSON).

**Tool registry** (`mcp/registry/tools.yaml`) — declarative, hot-reload:
```yaml
- name: search_products
  description: "Tìm sản phẩm theo tên/mô tả với hỗ trợ ngữ nghĩa"
  scopes: [merchant.read]
  input_schema:
    query: {type: string, required: true}
    merchant_id: {type: string}
    top_k: {type: integer, default: 10, max: 50}
  retrieval: {intent: search_product, channel: hybrid}
  cypher_template: "queries/search_products.cypher"

- name: get_customer_profile
  description: "Lấy hồ sơ 360 của khách hàng (PII đã hash)"
  scopes: [customer.read]
  pii: true
  input_schema:
    customer_id: {type: string, required: true}
  retrieval: {intent: customer_360, depth: 2}

- name: recommend_toppings
  description: "Gợi ý topping cho 1 sản phẩm dựa trên hành vi"
  scopes: [recommendation.read]
  input_schema:
    product_id: {type: string, required: true}
    customer_id: {type: string}
  retrieval: {intent: recommend_topping}

- name: order_analytics
  description: "Phân tích bán hàng theo merchant/khoảng thời gian"
  scopes: [analytics.read]
  input_schema:
    merchant_id: {type: string, required: true}
    date_from: {type: string, format: date}
    date_to: {type: string, format: date}
    metric: {type: string, enum: [revenue, qty, top_products, top_toppings]}
  retrieval: {intent: aggregate}

- name: find_similar_products
  description: "Tìm sản phẩm tương tự dựa trên embedding + co-purchase"
  scopes: [merchant.read]
  input_schema:
    product_id: {type: string, required: true}
    top_k: {type: integer, default: 10}

- name: data_discovery
  description: "Semantic search trên metadata + ontology cho data team"
  scopes: [data.discover]
  input_schema:
    query: {type: string, required: true}

- name: get_ontology_schema
  description: "Trả về schema KG (labels, rels, props) để LLM tự suy luận"
  scopes: [public]
```

**Bộ tool MVP** (~10 tool): `search_products`, `get_product`, `find_similar_products`, `recommend_toppings`, `recommend_products_for_customer`, `get_customer_profile`, `get_order_history`, `order_analytics`, `data_discovery`, `get_ontology_schema`.

**Bảo mật & governance MCP**:
- AuthN: OIDC token từ Keycloak gắn vào MCP HTTP transport; stdio dùng signed token.
- AuthZ: mỗi tool khai báo `scopes`; resolver kiểm tra scope của caller.
- Tenant isolation: tự động chèn `merchant_id` filter vào mọi Cypher template từ claim trong token.
- Rate limit per-tool, per-tenant qua Redis.
- Read-only DB role cho MCP — không bao giờ ghi.
- PII guard: tool có cờ `pii: true` luôn trả dữ liệu đã hash + ghi audit.
- Audit: mỗi tool call → log JSON (caller, tool, params, latency, rows, evidence_cypher) sang Loki + bảng `mcp_audit` Postgres để compliance.
- Query timeout 5s, kill long-running.

**Versioning**: mỗi tool có `version` (semver). Breaking change → tool mới `_v2`, giữ song song 1 quý.

### 2.5 Data flow daily batch
1. **01:30** `neo4j-admin database backup` snapshot trước batch → S3-compatible (rollback point).
2. **02:00** Airflow trigger → Spark standalone đọc snapshot từ Product 360, Merchant 360, Classified Product (JDBC/Parquet) — **dữ liệu đã được Data Platform thượng nguồn đảm bảo chất lượng**.
3. **02:30** Bronze (raw parquet trên S3-compatible) → Silver (chuẩn hoá, dedup, SCD2) bằng dbt-spark.
4. **04:00** Gold layer xuất ra `nodes/*.csv` và `edges/*.csv` theo schema KG.
5. **04:30** Loader Python merge vào Neo4j bằng `apoc.periodic.iterate` (idempotent UNWIND + MERGE), batch 10k.
6. **05:30** Job tính embedding cho Product mới/thay đổi → cập nhật vector index.
7. **06:00** Job derive `SIMILAR_TO`, `FAVORS` (Cypher GDS hoặc Python).
8. **06:30** Smoke checks tối thiểu (đếm node/edge so với baseline ±X%, không có dangling reference) → nếu fail → restore snapshot 01:30 và alert.
9. **07:00** Cập nhật dashboard freshness, notify kênh nội bộ (email/chat self-hosted).

---

## 3. Repo structure đề xuất

```
semantic-platform/
├── ontology/                  # Schema docs + Cypher constraints/migrations
│   ├── schema.cypher
│   ├── migrations/
│   └── README.md
├── airflow/dags/              # DAGs daily batch
│   ├── ingest_product.py
│   ├── ingest_customer.py
│   ├── ingest_order.py
│   └── kg_post_process.py
├── transforms/                # dbt project + Spark jobs
│   ├── dbt/models/{bronze,silver,gold}/
│   └── spark/jobs/
├── loaders/                   # Python loader → Neo4j
│   ├── nodes/  edges/  embeddings/
│   └── common/
├── api/                       # FastAPI + GraphQL (admin/BI nội bộ)
│   ├── schema.graphql
│   ├── resolvers/
│   └── auth/
├── mcp/                       # MCP server + Tool registry (cổng client/AI)
│   ├── server.py              # FastMCP entrypoint (stdio + HTTP+SSE)
│   ├── registry/tools.yaml
│   ├── tools/                 # 1 file/tool, dùng Context Retrieval
│   ├── queries/               # Cypher templates
│   ├── auth/                  # OIDC + scope check + tenant filter
│   └── audit/
├── agents/                    # AI / Retrieval layer
│   ├── retrieval/             # Context retrieval pipeline
│   │   ├── entity_linker.py
│   │   ├── hybrid_retriever.py
│   │   ├── subgraph_extractor.py
│   │   ├── reranker.py
│   │   ├── summarizer.py
│   │   └── policies.yaml
│   ├── text_to_cypher/        # Fallback khi không có tool phù hợp
│   ├── graphrag/
│   └── recommender/
├── infra/                     # On-prem provisioning (no K8s)
│   ├── ansible/               # Playbooks: neo4j, airflow, spark, mcp, redis, postgres, nginx, vault, monitoring
│   ├── docker/                # Dockerfiles + docker-compose per service
│   └── inventory/             # Hosts: dev, stg, prod
├── .gitlab-ci.yml             # GitLab CI pipelines
├── ci/                        # Reusable GitLab CI templates, scan jobs
├── tests/                     # unit + integration (testcontainers-neo4j)
├── eval/                      # Gold NL→answer dataset + harness
└── docs/                      # ADR, architecture, runbooks
```

---

## 4. Work breakdown & Timeline (16 tuần)

| Phase | Tuần | Hạng mục chính | Deliverable |
|---|---|---|---|
| **P0 — Foundations** | 1–2 | Provision VM (Ansible) cho Neo4j/Airflow/Spark/Postgres/Redis/Keycloak/Nginx; GitLab CI runner; repo skeleton; benchmark Neo4j Community vs Apache AGE | Hạ tầng VM sẵn sàng, smoke deploy pass, ADR chốt KG |
| **P1 — Ontology** | 2–3 | Workshop với SME F&B, chốt schema, viết `schema.cypher` + ADR-001 | Ontology v1 + constraints loaded |
| **P2 — Product ingestion** | 3–5 | DAG ingest Product/Variant/Topping/Category từ Product 360 + Classified Product (data đã sạch từ thượng nguồn) | Master data trong KG, dashboard count |
| **P3 — Merchant + Customer** | 5–6 | Ingest Merchant 360, Customer (PII hashing) | Customer/Merchant nodes + relationships |
| **P4 — Order ingestion** | 6–8 | DAG ingest Order/OrderLine (incremental), reified topping edges, idempotency | Full graph với fact orders |
| **P5 — Embeddings & derived edges** | 8–9 | Spark embedding job (GPU node), vector index, `SIMILAR_TO`/`FAVORS` | Semantic search hoạt động |
| **P6 — Context Retrieval Layer** | 9–10 | Entity linker, hybrid retriever, subgraph extractor, reranker, summarizer, Redis cache, policies.yaml | Retrieval lib + benchmark latency p95 < 800ms |
| **P7 — MCP server & Tool registry** | 10–12 | FastMCP server (stdio+HTTP+SSE), 10 tool MVP, OIDC, RBAC, tenant filter, audit, rate-limit, hot-reload registry | MCP server + tool catalog v1, kết nối Claude Desktop demo |
| **P8 — AI agents & eval** | 11–13 | Text-to-Cypher fallback, GraphRAG, recommender (qua MCP tools); eval harness gold set | Eval ≥80% accuracy trên 100 câu hỏi |
| **P9 — Hardening** | 13–15 | Neo4j single-primary + warm standby + backup/restore drill, load test (k6), pen-test MCP, runbooks, on-call | Prod-readiness checklist pass |
| **P10 — UAT & Launch** | 15–16 | Pilot với data team + 1 AI agent thật qua MCP, fix, go-live MVP | MVP production-ready |

**Đội hình đề xuất**: 1 TL/Architect, 2 Data Engineer, 1 Backend (MCP/API), 1 ML/AI Engineer (retrieval + agents), 0.5 DevOps, 0.5 PO.

Tổng thời gian giãn từ 16 → **16 tuần** (vẫn giữ) bằng cách chạy P6/P7/P8 song song một phần (Backend lo MCP, ML lo retrieval/agents).

---

## 5. Production readiness checklist (gate cho P9)

- [ ] **Neo4j Community HA**: single primary + warm standby (file-system snapshot từ backup mỗi giờ); RPO ≤ 1h, RTO ≤ 30 phút
- [ ] Backup `neo4j-admin database backup` mỗi giờ sang S3-compatible, retention 30 ngày, drill restore mỗi quý
- [ ] Idempotent loader (re-run cùng partition không tạo duplicate)
- [ ] PII hashing cho Customer (SHA-256 + salt từ Vault), audit log truy cập
- [ ] **RBAC enforce ở MCP layer** (Neo4j Community không có DB-level RBAC): scope check + tenant filter chèn `merchant_id` vào mọi Cypher template từ JWT claim
- [ ] Read-only DB user duy nhất cho MCP/API
- [ ] Rate limit + circuit breaker ở MCP và API
- [ ] Observability: SLO dashboard (freshness, query p95, MCP tool latency, agent accuracy)
- [ ] Runbook: incident, restore, schema migration, on-call rotation
- [ ] Security: SAST (Semgrep) + image scan (Trivy) chạy trong GitLab CI; secrets trong Vault, không lưu trong repo
- [ ] LLM guardrails: read-only Cypher, query timeout, schema-bounded prompt
- [ ] **MCP server**: 2 instance Docker sau Nginx LB (active-active stateless), OIDC verify mọi request, scope check 100% tool, audit log đầy đủ
- [ ] **Tool registry**: schema validation, hot-reload an toàn, versioning, không có tool ghi
- [ ] **Context retrieval**: cache hit ratio ≥ 50% steady-state, p95 < 800ms, fallback an toàn khi cache miss
- [ ] **Air-gap compliance**: firewall/iptables rule chặn egress internet từ VM MCP/LLM/embedding; verify bằng `curl` test định kỳ
- [ ] GitLab CI pipelines: build → test → scan → deploy (Ansible) qua môi trường dev → stg → prod, có manual gate

---

## 6. Verification (cách test end-to-end)

1. **Unit tests**: pytest cho transforms, loaders, agents (`tests/unit`) — chạy trong GitLab CI mỗi MR.
2. **Integration tests**: testcontainers Neo4j Community + Postgres; DAG chạy trên dữ liệu seed; assert node/edge counts.
3. **Schema migration test**: apply `ontology/migrations/*.cypher` lên Neo4j Community sạch trong GitLab CI job.
4. **API contract test**: schemathesis trên GraphQL SDL.
5. **MCP conformance test**: dùng `mcp-inspector` chạy qua từng tool — verify schema input/output, error code, audit log; thử connect bằng Claude Desktop trên dataset stg.
6. **Tool RBAC test**: mỗi tool chạy với 3 token (đủ scope, thiếu scope, sai tenant) → kỳ vọng allow/deny đúng.
7. **AI eval harness** (`eval/`): bộ ~100 cặp NL→answer F&B (vd: "Top 5 topping bán chạy nhất tuần qua tại merchant X"); chạy mỗi MR qua MCP tool; threshold ≥80% exact-match hoặc semantic-match.
8. **Retrieval benchmark**: bộ 50 query với gold subgraph; đo recall@k, precision, latency p95.
9. **Load test**: k6 mô phỏng 100 RPS qua MCP HTTP+SSE, p95 < 1.2s end-to-end; Neo4j Community p95 < 250ms.
10. **End-to-end smoke**: sau mỗi daily batch, agent trả lời đúng 10 canonical questions qua MCP trong staging trước khi promote.
11. **Air-gap test**: GitLab CI job verify firewall egress rules; chạy `curl` đến internet từ VM MCP/LLM phải fail.
12. **Disaster drill**: backup-restore Neo4j Community mỗi quý từ snapshot trên S3-compatible; verify data parity với baseline counts.

---

## 7. Critical files sẽ tạo ở phase đầu

- `ontology/schema.cypher` — constraints, indexes, vector index
- `ontology/migrations/001_init.cypher`
- `airflow/dags/ingest_product.py` — template DAG đầu tiên
- `loaders/common/neo4j_writer.py` — idempotent UNWIND/MERGE helper
- `transforms/dbt/dbt_project.yml` + `models/gold/dim_product.sql`
- `infra/ansible/playbooks/neo4j.yml` — cài Neo4j Community trên VM
- `infra/ansible/playbooks/{airflow,spark,mcp,redis,postgres,nginx,vault,monitoring}.yml`
- `infra/docker/mcp/Dockerfile` + `infra/docker/mcp/docker-compose.yml`
- `.gitlab-ci.yml` — pipelines build/test/scan/deploy
- `api/schema.graphql` — GraphQL schema sinh từ ontology (admin/BI nội bộ)
- `mcp/server.py` — FastMCP entrypoint
- `mcp/registry/tools.yaml` — tool registry v1
- `mcp/queries/*.cypher` — Cypher templates parametrized
- `mcp/auth/oidc.py` — verify token + scope + tenant filter
- `agents/retrieval/policies.yaml` — retrieval policies per intent
- `agents/retrieval/hybrid_retriever.py` — vector + graph + full-text
- `agents/text_to_cypher/prompt.py` — schema-aware few-shot prompt (fallback)
- `eval/gold_qa.jsonl` — bộ NL→answer cho eval harness
- `eval/retrieval_gold.jsonl` — gold subgraph cho retrieval benchmark
- `docs/architecture.md`, `docs/adr/0001-ontology.md`, `docs/adr/0002-neo4j-community-vs-age.md`, `docs/adr/0003-mcp-as-client-gateway.md`, `docs/adr/0004-no-k8s-vm-based-deployment.md`

---

## 8. Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Ontology thay đổi liên tục | Versioning schema + migration; ADR cho mỗi thay đổi |
| Order volume lớn → load chậm | Partition by date, parallel APOC, chỉ load delta |
| Text-to-Cypher hallucinate | Schema-bounded prompt + read-only role + query validator + fallback to template |
| PII rò rỉ | Hash trước khi vào KG, RBAC, audit log, không gửi PII vào LLM ngoài |
| Neo4j Community không có HA cluster | Single primary + warm standby từ backup mỗi giờ; RTO 30 phút chấp nhận được cho daily batch use case; benchmark Apache AGE ở P0 để có fallback |
| Neo4j Community không có DB-RBAC | Enforce RBAC/tenant filter ở MCP layer; read-only DB user; pen-test trong P9 |
| LLM hạ tầng GPU thiếu | Self-host Qwen2.5-14B trên 2 GPU nội bộ; cache aggressive; tách model nhỏ cho intent/rerank |
| MCP misuse (client lạm dụng tool) | Rate limit + scope + per-tool quota; circuit breaker |
| Retrieval trả context sai | Eval harness gắn gold subgraph; canary tool version; rollback nhanh |
| Schema KG đổi → vỡ tool | Tool versioning, contract test trong CI, deprecation 1 quý |

---

**Tóm tắt**: 16 tuần, 5 FTE, **on-prem hoàn toàn**, **không Kubernetes** — chạy trên VM/bare-metal với Docker + Ansible, **GitLab CI/Runner** cho CI/CD. **Neo4j 5.x Community** + S3-compatible nội bộ + GPU VM self-host LLM. **Client/AI tương tác qua MCP server + Tool registry**, không truy vấn KG trực tiếp. **Context Retrieval Layer** đảm bảo trả về subgraph cô đọng + summaries có evidence. RBAC/multi-tenant enforce ở MCP layer (vì Community không có DB-RBAC). Data Quality không nằm trong scope — đã được Data Platform thượng nguồn đảm bảo. Có so sánh Neo4j Community vs Apache AGE với fallback path. MVP cuối tuần 16 đáp ứng 3 mục tiêu: NL Q&A, Recommendation, Semantic search — với HA single-primary+standby, observability, security, air-gap đầy đủ.
