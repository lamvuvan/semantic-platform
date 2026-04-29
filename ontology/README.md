# Ontology

Định nghĩa schema KG cho domain F&B. Xem `docs/PLAN.md §1` cho thiết kế đầy đủ.

## Files

- `schema.cypher` — constraints, indexes (range, full-text, vector)
- `migrations/001_init.cypher` — migration đầu tiên áp dụng schema

## Áp dụng

```bash
cypher-shell -a neo4j://neo4j-host:7687 -u neo4j -p "$NEO4J_PASSWORD" \
  -f ontology/schema.cypher
```

## Node labels

| Label | Mục đích |
|---|---|
| `Merchant` | Cửa hàng/brand sở hữu sản phẩm |
| `Category` | Phân loại đa cấp từ Classified Product |
| `Product` | Sản phẩm gốc (master) |
| `ProductVariant` | Biến thể size/nhiệt độ/đường/đá |
| `Topping` | Topping/add-on |
| `Customer` | Khách hàng (PII đã hash) |
| `Order` | Đơn hàng |
| `OrderLine` | Dòng đơn (reified để gắn variant + topping) |

> `OrderLine` ≠ `Invoice`. Xem ghi chú trong `docs/PLAN.md`.

## Relationships

Xem `docs/PLAN.md §1.2`.
