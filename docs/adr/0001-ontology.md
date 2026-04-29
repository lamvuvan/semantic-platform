# ADR-0001: Ontology F&B v1

**Status**: Accepted (2026-04-29)

## Context

Cần ontology cho domain F&B đáp ứng phân tích sản phẩm, đơn hàng, khách hàng cho AI agent.

## Decision

Sử dụng **Property Graph** với 8 node label: `Merchant`, `Category`, `Product`, `ProductVariant`, `Topping`, `Customer`, `Order`, `OrderLine`. Quan hệ topping bị **reified** qua `OrderLine` để gắn được qty/price từng topping mỗi dòng đơn.

`OrderLine` ≠ `Invoice`: `OrderLine` thuộc domain bán hàng (variant + topping + qty + giá), trong khi `Invoice` là chứng từ tài chính (VAT, MST). Nếu sau này cần Invoice → bổ sung `(:Invoice)-[:BILLS]->(:Order)` riêng.

## Consequences

- Truy vấn topping theo dòng đơn cần 1 hop thêm qua `OrderLine` — chấp nhận được vì độ chính xác phân tích cao hơn.
- Schema sinh embedding chỉ trên `Product` ở MVP; mở rộng sau cho Topping nếu cần.
