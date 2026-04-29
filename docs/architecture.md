# Architecture overview

Tham chiếu chi tiết: [`docs/PLAN.md`](./PLAN.md)

## Layers

```
Client / AI agents (qua MCP)
        ↓
MCP server + Tool registry  (mcp/)
        ↓
Context retrieval layer     (agents/retrieval/)
        ↓
Knowledge Graph             (Neo4j 5.x Community)
        ↑
Transform & Load            (transforms/, loaders/)
        ↑
Sources: Product 360, Merchant 360, Classified Product
```

## Data flow daily batch

`airflow/dags/kg_daily_batch.py` lập lịch 02:00 mỗi ngày:

1. Snapshot Neo4j (rollback point) → S3-compatible.
2. dbt-spark: bronze → silver → gold.
3. Spark export gold tables ra CSV trên S3.
4. Loader Python merge nodes + edges vào Neo4j (idempotent UNWIND/MERGE).
5. Embedding job (GPU VM) → vector index.
6. Derive `SIMILAR_TO` + `FAVORS`.
7. Smoke check counts vs baseline.

## Client tương tác

Client AI và app KHÔNG truy vấn Cypher trực tiếp.

```
┌──────────────┐   bearer JWT   ┌────────────┐  Cypher  ┌──────┐
│ Claude/Agent │ ─────────────▶ │ MCP server │ ───────▶ │ Neo4j│
└──────────────┘                └────────────┘          └──────┘
                                  │
                                  ├── Audit log → Loki + Postgres
                                  └── Rate limit → Redis
```

Tool registry tại `mcp/registry/tools.yaml` — declarative, hot-reload, có versioning.

## Trên prem, KHÔNG K8s

- VM/bare-metal nội bộ.
- Provisioning bằng Ansible (`infra/ansible/playbooks/`).
- Container runtime Docker (`infra/docker/`).
- Reverse proxy Nginx + keepalived VRRP cho HA tại layer LB.
- CI/CD GitLab CI + GitLab Runner self-hosted (`.gitlab-ci.yml`).
