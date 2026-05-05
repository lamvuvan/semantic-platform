# ADR-0001 — 5-layer architecture cho AI Agent integration

**Status**: Accepted (2026-05-05)

## Context

AI agent (LLM) cần truy cập KG để trả lời câu hỏi nghiệp vụ F&B. Nếu cho agent chạm DB trực tiếp:
- Lộ infrastructure (Cypher endpoint, ES DSL, vector API).
- Không cô lập tenant ở DB — Neo4j Community không có RBAC.
- Khó audit, rate limit, observability.

## Decision

5-layer kiến trúc tách biệt rõ trust boundary:

1. **Data Stores** (Neo4j + ES + Qdrant) — private VPC.
2. **Repository / DAO** — Cypher/JSON template parameterized, version-controlled.
3. **Domain Service** (FastAPI) — business logic: hybrid search, ranking, fallback, alias feedback.
4. **MCP Tool Server** (FastMCP) — auth (JWT), per-agent surface ≤10 tool, rate limit, audit.
5. **AI Agents** — chỉ thấy MCP tools.

Mỗi layer chỉ tin layer ngay dưới. LLM **không vượt qua Layer 4**.

## Consequences

✓ Agent thay đổi không vỡ DB schema (chỉ contract MCP tool).
✓ Mọi tool call có audit log + trace ID xuyên suốt MCP→Domain→Repo.
✓ Rate limit per (agent, merchant, tool) tự nhiên ở MCP boundary.
✓ Add backend mới (vd OpenSearch thay ES) chỉ ảnh hưởng Layer 2.

✗ Latency thêm 1 hop network MCP→Domain. Mitigate bằng HTTP/2 + connection pool + cache Redis.
✗ Phức tạp hơn cho dev — cần chạy 7 service trong docker-compose. Mitigate bằng `infra/docker/docker-compose.yml`.
