# Runbook

## On-call quick links

- Grafana: http://monitor-01.internal:3000
- Loki: http://monitor-01.internal:3100
- Airflow: http://airflow-web.internal:8080
- Neo4j Browser: http://neo4j-01.internal:7474
- MCP health: http://nginx-01.internal/healthz

## Sự cố phổ biến

### 1. Daily batch fail

1. Check Airflow log task fail.
2. Nếu fail ở `load_*`: kiểm tra Neo4j có còn dung lượng / không bị restart.
3. Restore snapshot trước batch:
   ```bash
   neo4j-admin database restore neo4j --from-path=s3://kg-backups/dt=YYYY-MM-DD/
   ```

### 2. MCP tool trả 401

- Token hết hạn / sai audience. Verify JWT bằng `jwt.io` và check `OIDC_AUDIENCE`.
- Keycloak realm có đúng client không.

### 3. Neo4j down

- `systemctl status neo4j` trên `neo4j-01`.
- Nếu primary down lâu → promote standby:
  ```bash
  ssh neo4j-02 -- neo4j-admin database load neo4j --from-path=s3://kg-backups/latest/
  systemctl start neo4j
  # Cập nhật DNS/Nginx upstream sang neo4j-02
  ```

### 4. MCP latency cao

1. Check Redis hit ratio (Grafana panel "context_cache_hit").
2. Check Neo4j query log slow queries.
3. Tăng cache TTL ở `agents/retrieval/policies.yaml` nếu phù hợp.

## Schema migration

```bash
cypher-shell -a bolt://neo4j-01:7687 -u neo4j -p $PWD \
  -f ontology/migrations/00X_*.cypher
```

Mỗi migration phải idempotent (`IF NOT EXISTS`).

## Backup & restore drill

Thực hiện mỗi quý:

```bash
# Backup
neo4j-admin database backup neo4j --to-path=/tmp/restore-test/

# Restore lên VM staging
ssh neo4j-stg -- neo4j-admin database load neo4j --from-path=/tmp/restore-test/

# So sánh count
python -m tests.smoke.kg_counts --baseline /opt/baselines/last.json
```
