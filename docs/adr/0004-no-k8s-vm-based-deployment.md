# ADR-0004: Triển khai VM-based, KHÔNG Kubernetes

**Status**: Accepted (2026-04-29)

## Context

Yêu cầu on-prem hoàn toàn. Đội vận hành quen Ansible/Linux, chưa có team K8s sẵn.

## Decision

- Provisioning bằng **Ansible** (`infra/ansible/playbooks/`).
- Container runtime **Docker** trên từng VM (`infra/docker/`).
- HA layer: Nginx + keepalived (VRRP) cho MCP/API; Postgres streaming + Patroni; Redis Sentinel.
- Spark standalone cluster (1 master + N worker), Airflow CeleryExecutor + Redis broker.
- CI/CD **GitLab CI** + GitLab Runner self-hosted.

## Consequences

- Triển khai đơn giản, không cần kỹ năng K8s.
- Trả giá: scaling thủ công, không có auto-healing như K8s. Chấp nhận được vì daily batch + SLO ở mức MVP.
- Khi đội trưởng thành K8s, có thể migrate từng dịch vụ vì mỗi dịch vụ đã đóng gói Docker.
