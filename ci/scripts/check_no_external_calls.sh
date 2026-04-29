#!/usr/bin/env bash
# Phát hiện call ra internet không mong muốn trong code (URL ngoài internal domain).
# Chạy ở stage `scan`. Air-gap: tham chiếu docs/PLAN.md §5.

set -euo pipefail

ALLOWED_DOMAINS_REGEX='(\.internal|localhost|127\.0\.0\.1|::1|neo4j|redis|postgres|s3-internal|keycloak|vault)'

violations=$(grep -RInE 'https?://[^ "'\''`)]+' \
    --include='*.py' --include='*.yml' --include='*.yaml' --include='*.sh' \
    . | grep -vE "$ALLOWED_DOMAINS_REGEX" || true)

if [[ -n "$violations" ]]; then
    echo "Phát hiện URL có thể call ra ngoài internet:" >&2
    echo "$violations" >&2
    exit 1
fi

echo "OK — không phát hiện external URL."
