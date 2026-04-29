# Requirements

Python **3.12** required (xem `pyproject.toml [project] requires-python`).

## Files

| File | Mục đích | Dùng khi |
|---|---|---|
| `base.txt` | Core deps dùng chung mọi component | Không dùng trực tiếp — file khác `-r base.txt` |
| `mcp.txt` | MCP server runtime | Build `infra/docker/mcp/Dockerfile` |
| `api.txt` | Admin/BI API runtime | Build `infra/docker/api/Dockerfile` |
| `loaders.txt` | KG loaders runtime | Build `infra/docker/loaders/Dockerfile` |
| `agents.txt` | Retrieval/agents runtime | MCP image hoặc embedding worker GPU |
| `dev.txt` | Full dev/CI (test + lint + scan) | `pip install -r requirements/dev.txt` |
| `../requirements.txt` | Aggregate cho scanner tool ở root | Renovate/Dependabot/Trivy |

## Quan hệ với `pyproject.toml`

`pyproject.toml` định nghĩa cùng deps qua `[project]` + `[project.optional-dependencies]`. File `requirements/*.txt` là **mirror** để:
- Build Docker image nhanh hơn (`pip install -r` không cần parse pyproject + setuptools).
- Tool scan SCA (Trivy, Snyk, Renovate) phát hiện được.
- CI runner cài deps tách biệt khỏi project install.

Khi đổi version: cập nhật cả `pyproject.toml` và file `requirements/*.txt` tương ứng. Ý tưởng dài hạn: dùng `pip-compile` (có sẵn trong `dev.txt`) để sinh `requirements/lock/*.txt` cố định version đầy đủ — bật khi cần reproducible build.

## Pinning style

Lower-bound + upper-bound theo major version:
```
neo4j>=5.20,<6.0
```

Lý do:
- Cho phép security patch (5.x) tự nhận.
- Chặn breaking change ở major (6.0).
- Khi cần reproducible chính xác, tạo lockfile riêng — không pin cứng trong file primary.

## Sinh lockfile (tuỳ chọn)

```bash
pip install pip-tools
pip-compile --resolver=backtracking -o requirements/lock/mcp.lock requirements/mcp.txt
```

Lock file được commit ở `requirements/lock/` khi cần determinstic build.
