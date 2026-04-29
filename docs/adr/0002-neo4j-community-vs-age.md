# ADR-0002: Neo4j Community vs Apache AGE

**Status**: Accepted (2026-04-29) — chọn **Neo4j 5.x Community**

## Context

Cần graph store on-prem, không license thương mại, hỗ trợ vector index, Cypher đầy đủ, và hệ sinh thái GraphRAG/MCP mature.

## Decision

Chọn **Neo4j 5.x Community** vì:

1. Vector index HNSW có sẵn từ 5.13 (Community).
2. Cypher đầy đủ + APOC Core + GDS Community.
3. Hệ sinh thái LangChain/LlamaIndex/MCP first-class.

**Đánh đổi vì là Community**:
- Không có HA cluster → single primary + warm standby + backup mỗi giờ; RTO 30 phút.
- Không có DB-level RBAC → enforce **toàn bộ RBAC ở MCP layer**.
- Không có multi-database → 1 DB, namespace bằng label.

**Phương án dự phòng**: Apache AGE (Postgres extension), nếu HA hoặc tích hợp Postgres trở thành quan trọng. Adapter pattern ở `loaders/` và `mcp/tools/` cho phép chuyển backend.

## Consequences

- Cần process backup/restore drill mỗi quý.
- Pen-test MCP layer phải đảm bảo không bypass tenant filter.
