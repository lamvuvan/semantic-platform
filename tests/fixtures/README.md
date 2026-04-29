# Mock data fixtures

Mock dataset F&B realistic (tiếng Việt) cho dev/test/eval. Sinh **deterministic** với seed cố định.

## Files

- `generate_mock.py` — generator
- `seed_full.cypher` — seed pre-generated (5 merchants, 50 customers, 200 orders, 90 ngày)
- `seed_small.cypher` — seed nhỏ cho integration test (committed, không phải `seed_full`)

## Sử dụng

### Sinh seed mới

```bash
# Cypher (mặc định 5/50/200)
python -m tests.fixtures.generate_mock --output tests/fixtures/seed_full.cypher

# Quy mô lớn hơn
python -m tests.fixtures.generate_mock \
    --merchants 5 --customers 500 --orders 5000 --days 180 \
    --output /tmp/seed_large.cypher

# CSV cho loader pipeline
python -m tests.fixtures.generate_mock --csv-dir /tmp/kg-csv
```

### Apply vào Neo4j

```bash
# Schema trước
cypher-shell -a bolt://localhost:7687 -u neo4j -p $PWD \
    -f ontology/schema.cypher

# Seed
cypher-shell -a bolt://localhost:7687 -u neo4j -p $PWD \
    -f tests/fixtures/seed_full.cypher
```

Hoặc bằng `docker compose`:

```bash
docker compose -f infra/docker/docker-compose.yml exec -T neo4j \
    cypher-shell -u neo4j -p changeme < tests/fixtures/seed_full.cypher
```

## Quy mô mặc định

| Entity | Count |
|---|---:|
| Merchant | 5 |
| Category | 13 (cây 3 cấp) |
| Product | 20 |
| ProductVariant | ~148 (drink: size×ice×sugar) |
| Topping | 10 |
| Customer | 50 |
| Order | 200 (rải đều 90 ngày) |
| OrderLine | ~320 |

Đủ để smoke-test toàn bộ MCP tool và eval harness mà không cần GPU/embedding.
