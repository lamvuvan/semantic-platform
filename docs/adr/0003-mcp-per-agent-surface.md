# ADR-0003 — Per-agent tool surface ≤10 tool

**Status**: Accepted (2026-05-05)

## Context

Có 3 nhóm AI agent ban đầu: Sales Copilot (call center), BI Agent (chủ chuỗi), Inventory Agent (kho). Nếu expose chung tool list:
- Inventory Agent có thể gọi `get_customer_profile` (PII) — không cần thiết, vi phạm least privilege.
- LLM context bị nhiễu khi 30+ tools cùng list.
- Khó tinh chỉnh rate limit theo agent.

## Decision

Mỗi agent có **surface YAML riêng**: list tool ≤ 10, scopes, rate_limit_rpm. MCP server load `mcp_server/agents/surfaces.yaml` và đăng ký tools với tên qualified `{agent_id}__{tool_name}`. JWT `sub` của agent phải khớp `agent_id` của surface.

```yaml
agents:
  sales-copilot:
    scopes_required: [merchant.read, customer.read, recommendation.read]
    rate_limit_rpm: 120
    tools: [search_products, get_product, ..., submit_alias_feedback]  # ≤10
  inventory-agent:
    tools: [search_products, get_product, find_similar_products]  # 3 tools
```

## Consequences

✓ Least privilege per agent — không bị lộ tool ngoài vai trò.
✓ LLM context nhỏ → hiệu quả prompt + rẻ token.
✓ Audit log có agent_id rõ ràng.
✓ Soft cap 10 tool ép designer suy nghĩ kỹ tool API thay vì chiêu thêm.

✗ Có thể duplication tool implementation nếu nhiều agent cần biến thể khác nhau — chấp nhận, vì tool implementation nhỏ.
