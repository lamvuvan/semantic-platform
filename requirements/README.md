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

## Pinning policy — EXACT version (`==`)

Tất cả deps đều pin **chính xác** một version cụ thể. Không dùng `>=`, không dùng range, không dùng `~=`.

```
neo4j==5.27.0
```

Lý do:
- **Reproducible build**: image tag và CI run cùng commit luôn cho ra cùng dependency tree.
- **Air-gap an toàn**: không bị resolver tự kéo phiên bản mới khi mirror nội bộ refresh.
- **Audit dễ**: SCA scanner (Trivy/Snyk) báo CVE chính xác trên version đang chạy.
- **Đổi version = MR có review**: bắt buộc qua quy trình kiểm thử regression đầy đủ, không có upgrade ngầm.

Đánh đổi: cần proactive nâng cấp định kỳ (mỗi quý) để không tích nợ CVE — Renovate/Dependabot tự mở MR đề xuất bump, người review chạy CI rồi merge.

## Quy trình nâng cấp 1 dependency

1. Cập nhật cùng lúc cả `requirements/<role>.txt` **và** `pyproject.toml`.
2. Nếu là transitive dep (vd `cryptography` của `PyJWT[crypto]`) thì cũng phải pin bản tương thích.
3. Chạy local: `pip install -r requirements/dev.txt && pytest tests/unit -q`.
4. Push MR → GitLab CI chạy lint + test + scan + build image.
5. Nếu Trivy/Semgrep báo regression → fix hoặc rollback.
6. Merge sau khi review.

## Sinh lockfile transitive đầy đủ (tuỳ chọn)

```bash
pip install pip-tools
pip-compile --resolver=backtracking --generate-hashes \
    -o requirements/lock/mcp.lock requirements/mcp.txt
```

Lock file ở `requirements/lock/` ghim toàn bộ transitive — bật khi cần
hash-pinned reproducible build (vd cho image production cuối cùng).
