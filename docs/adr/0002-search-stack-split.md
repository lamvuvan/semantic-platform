# ADR-0002 — Tách lexical / semantic / graph thành 3 store chuyên biệt

**Status**: Accepted (2026-05-05)

## Context

KG cần 3 loại truy vấn cho AI agent:
- **Lexical**: tìm sản phẩm theo tên, mô tả, alias tiếng Việt.
- **Semantic**: tìm sản phẩm tương tự theo embedding.
- **Graph**: traversal quan hệ Customer→Order→Product→Topping.

Lựa chọn ban đầu (v1) gộp tất cả vào Neo4j Community (vector index 5.13+, full-text Lucene). Vấn đề:
- Lucene của Neo4j yếu cho VN (không có analyzer chuyên dụng).
- Vector HNSW của Neo4j không có filter pre-index theo tenant.
- Query hybrid cần 3 cú syntax khác nhau trong cùng Cypher.

## Decision

Tách thành 3 store chuyên dụng:

| Concern | Store | Lý do |
|---|---|---|
| Lexical | Elasticsearch 8.x | VN analyzer, alias boosting, fuzziness AUTO |
| Semantic | Qdrant 1.12 | Native filter `merchant_id` ở index, HNSW tốt, replication |
| Graph | Neo4j 5.x Community | Property graph thuần, traversal sâu hiệu quả |

Hybrid merge ở **Layer 3 ProductSearchService** — fan-out 3 store song song, weighted score.

## Consequences

✓ Lexical search VN chất lượng hơn — alias boosting + asciifolding.
✓ Vector search filter tenant ở index level — performance + security.
✓ Neo4j chỉ làm graph thuần → schema đơn giản hơn.
✓ Mỗi store scale độc lập theo workload.

✗ 3 store → 3 nhóm vận hành (backup/monitor riêng).
✗ Đồng bộ dữ liệu Product giữa 3 store — cần ingestion pipeline đảm bảo.
