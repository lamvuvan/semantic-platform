# Architecture overview

Tham chiếu **README.md** mục "AI Agent Integration Architecture" cho big picture.
File này mô tả implementation cụ thể từng layer.

## Layer 1 — Data Stores
- `data/neo4j/` — KG schema (constraints + indexes range; KHÔNG có vector/fulltext index ở Neo4j)
- `data/elasticsearch/mappings/product.json` — index Product cho lexical search VN
- `data/vector/qdrant/products.json` — collection Qdrant cho semantic embeddings (dim=384, cosine)

Trust boundary: chỉ Layer 2 (repository) kết nối; private VPC; service account read-only.

## Layer 2 — Repository (DAO)
- `repository/neo4j/` — `client.py` đọc Cypher từ `queries/*.cypher` (parameterized, version-controlled). Chỉ READ.
- `repository/elasticsearch/` — `client.py` substitute Mustache template từ `queries/*.json`.
- `repository/vector/` — `client.py` Qdrant search với filter `merchant_id`.

Tenant scoping: mọi truy vấn nhận `merchant_id` parameter. Layer 3 chèn từ Caller, không tin caller body.

## Layer 3 — Domain Service (FastAPI)
- `domain/main.py` — endpoints `/v1/products/search`, `/v1/recommendations/toppings`, `/v1/customers/{id}`, `/v1/aliases/feedback`.
- `domain/services/` — 3 service classes:
  - `ProductSearchService` — hybrid lexical + semantic + graph với confidence merge + fallback.
  - `RecommendationService` — co-purchase + personal bias.
  - `AliasFeedbackService` — ghi alias mới vào Postgres để cải thiện search.
- `domain/models/schemas.py` — Pydantic input/output, version-stable.
- `domain/observability/telemetry.py` — OpenTelemetry trace + Prometheus metrics.
- `domain/embedding.py` — adapter gọi embedding service nội VPC, có cache.

Trust boundary: chấp nhận caller identity từ trusted MCP qua mTLS — header `x-agent-id`, `x-merchant-id`, `x-scopes`. Domain Service KHÔNG verify JWT — đó là việc của Layer 4.

## Layer 4 — MCP Tool Server
- `mcp_server/server.py` — FastMCP entrypoint, Streamable HTTP `POST /mcp`.
- `mcp_server/agents/surfaces.yaml` — declarative surface ≤10 tool/agent (sales-copilot, bi-agent, inventory-agent).
- `mcp_server/middleware/auth.py` — verify JWT (JWKS cache).
- `mcp_server/middleware/ratelimit.py` — token bucket Redis per (agent, merchant, tool).
- `mcp_server/middleware/audit.py` — JSON audit log → Loki + Postgres `mcp_audit`.
- `mcp_server/tools/*.py` — Pydantic input → trusted headers → gọi Domain Service qua `domain_client.py` (mTLS).
- Mỗi tool MCP-qualified `{agent_id}__{tool_name}` để agent isolation rõ ràng.

## Layer 5 — AI Agents
Không có code trong repo này — agent là client bên ngoài (Claude Desktop, custom MCP client). Mỗi agent có 1 JWT từ Keycloak với `merchant_id` claim, scopes, và sub = agent_id khớp surface.

## Trust boundaries (tóm tắt)
- LLM ↔ Layer 4: JWT + scope + rate limit + per-agent surface.
- Layer 4 ↔ Layer 3: mTLS + trusted header (Domain tin Layer 4).
- Layer 3 ↔ Layer 2: tham số merchant_id bắt buộc.
- Layer 2 ↔ Layer 1: read-only DB account, private VPC.

LLM **không vượt qua Layer 4** — không bao giờ thấy URL DB, không bao giờ chạm Cypher/SQL/HTTP repo.
