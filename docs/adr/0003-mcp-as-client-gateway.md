# ADR-0003: MCP làm cổng client/AI duy nhất

**Status**: Accepted (2026-04-29)

## Context

Nhiều loại client (Claude Desktop, custom agent, n8n, BI plugin) cần truy vấn KG. Cho phép truy vấn Cypher trực tiếp gây rủi ro: bypass tenant filter, query DoS, schema vỡ → client vỡ.

## Decision

Mọi client/AI tương tác với KG qua **MCP server + Tool registry**:

- MCP server (`mcp/server.py`, FastMCP) hỗ trợ stdio + HTTP+SSE.
- Tool registry declarative tại `mcp/registry/tools.yaml`, hot-reload.
- Mỗi tool: scope check (OIDC), tenant filter từ JWT claim, audit log, rate limit, query timeout.
- Read-only DB user duy nhất.

## Consequences

- Tất cả Cypher tập trung tại `mcp/queries/` và `mcp/tools/` — dễ review và pen-test.
- Schema KG có thể tiến hoá; tool versioning bảo vệ client.
- Đắt thêm 1 hop network nhưng cache Redis bù lại.
