# semantic-platform

Lớp ngữ nghĩa (semantic layer) trên data platform F&B — Knowledge Graph cung cấp ngữ cảnh phong phú cho AI agent.

Tham chiếu thiết kế đầy đủ: [`docs/PLAN.md`](./docs/PLAN.md).

## Tóm tắt

- **KG**: Neo4j 5.x Community (Property Graph + HNSW vector index).
- **Hạ tầng**: on-prem hoàn toàn, KHÔNG Kubernetes — VM/bare-metal + Docker + Ansible.
- **Object storage**: S3-compatible nội bộ.
- **CI/CD**: GitLab CI + GitLab Runner self-hosted.
- **Cổng client/AI**: MCP server + Tool registry — không truy vấn Cypher trực tiếp.
- **Freshness**: daily batch (02:00 mỗi ngày).

## Cấu trúc repo

| Path | Mục đích |
|---|---|
| `ontology/` | Schema KG, constraints, indexes (Cypher) |
| `transforms/dbt/` | Bronze → Silver → Gold (dbt-spark) |
| `transforms/spark/jobs/` | Spark jobs export CSV + sinh embedding |
| `loaders/` | Python idempotent loader → Neo4j |
| `airflow/dags/` | DAG daily batch |
| `agents/retrieval/` | Context retrieval pipeline (entity link, hybrid, subgraph, rerank, summarize, cache) |
| `agents/text_to_cypher/` | Schema-aware NL→Cypher fallback + validator read-only |
| `agents/graphrag/`, `agents/recommender/` | Logic AI cụ thể |
| `mcp/` | MCP server + tool registry + auth + audit |
| `api/` | FastAPI + GraphQL admin/BI |
| `infra/ansible/` | Playbooks provision toàn stack |
| `infra/docker/` | Dockerfile cho mcp/api/loaders + docker-compose dev |
| `.gitlab-ci.yml` | Pipeline GitLab CI |
| `tests/` | unit + integration + smoke |
| `eval/` | Gold NL→answer + harness |
| `docs/` | Plan, architecture, ADRs, runbook |

## Quickstart (dev)

```bash
# Spin up Neo4j + Redis + Postgres + MCP + API local
cd infra/docker && docker compose up -d

# Apply schema
docker compose exec neo4j cypher-shell -u neo4j -p changeme \
  -f /opt/ontology/schema.cypher

# Seed dataset
docker compose exec neo4j cypher-shell -u neo4j -p changeme \
  -f /opt/tests/integration/seed.cypher

# Chạy unit tests
pip install -e ".[dev]"
pytest tests/unit -q

# Chạy MCP CLI inspector (cần `mcp-inspector` cài sẵn)
mcp-inspector --transport stdio python -m mcp.server
```

## Roadmap (16 tuần)

Xem `docs/PLAN.md §4`.

## License

Internal.
