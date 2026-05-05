CREATE TABLE IF NOT EXISTS aliases (
    alias_id            UUID PRIMARY KEY,
    merchant_id         TEXT NOT NULL,
    surface_text        TEXT NOT NULL,
    matched_product_id  TEXT NOT NULL,
    confidence          DOUBLE PRECISION NOT NULL,
    was_accepted        BOOLEAN NOT NULL DEFAULT false,
    submitted_by_agent  TEXT NOT NULL,
    submitted_at        TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (merchant_id, surface_text, matched_product_id)
);

CREATE INDEX IF NOT EXISTS aliases_merchant_idx
    ON aliases (merchant_id, was_accepted, submitted_at DESC);

CREATE TABLE IF NOT EXISTS mcp_audit (
    request_id   UUID PRIMARY KEY,
    tool         TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    merchant_id  TEXT NOT NULL,
    params       JSONB NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL,
    latency_ms   INT,
    ok           BOOLEAN NOT NULL,
    error        TEXT,
    error_msg    TEXT
);

CREATE INDEX IF NOT EXISTS mcp_audit_tenant_idx
    ON mcp_audit (merchant_id, agent_id, started_at DESC);
