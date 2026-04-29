// Migration 001 — Initial schema
// Áp dụng `ontology/schema.cypher` lên DB sạch.
// Idempotent: dùng IF NOT EXISTS.

:source schema.cypher
