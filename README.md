# semantic-platform

Lớp ngữ nghĩa (semantic layer) trên data platform — Knowledge Graph cung cấp ngữ cảnh phong phú cho AI agent.

# Knowledge Graph — AI Agent Integration Architecture

**Phạm vi:** Thiết kế kiến trúc và tool layer để AI Agent truy cập Knowledge Graph của KiotViet một cách an toàn, có observability, và scale được.

**Stack:** Neo4j (KG) + Elasticsearch (lexical) + Vector store (semantic) + FastMCP (tool layer) + FastAPI (domain service). Multi-tenant theo `merchant_id`.

**Nguyên tắc cốt lõi:** AI Agent **không bao giờ** kết nối trực tiếp với database. Agent chỉ thấy *capabilities* (MCP tools), không thấy *infrastructure* (Cypher endpoint, ES query DSL, vector search API).

---

## 1. Tóm tắt kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: AI AGENTS                                             │
│  Sales Copilot │ BI Agent │ Inventory Agent                     │
│  - LLM + MCP client                                             │
│  - Chỉ thấy tools, không thấy DB                                │
└────────────────────────────┬────────────────────────────────────┘
                             │  MCP protocol (Streamable-HTTP)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: MCP TOOL SERVER (FastMCP)                              │
│  - Tool surface ≤10 tools per agent                              │
│  - Pydantic input validation                                     │
│  - Mandatory tenant scoping (merchant_id required)               │
│  - Rate limiting per agent + per merchant                        │
│  - Audit log mọi tool call                                       │
│  - Auth: agent JWT với scope                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTP/gRPC nội bộ (mTLS)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: DOMAIN SERVICE (FastAPI)                               │
│  - ProductSearchService (hybrid: lexical + semantic + graph)     │
│  - RecommendationService                                         │
│  - AliasFeedbackService                                          │
│  - Business logic: confidence ranking, fallback, cache (Redis)   │
│  - Observability: OpenTelemetry trace, Prometheus metrics        │
└────────────────────────────┬────────────────────────────────────┘
                             │  Bolt + ES + Vector clients
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: REPOSITORY / DAO                                       │
│  - Cypher queries PARAMETERIZED, version-controlled (.cypher)    │
│  - ES query templates                                            │
│  - Vector search wrappers                                        │
│  - Index hints, query plan reviewed trong CI                     │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: DATA STORES (private VPC, không expose ngoài)          │
│  Neo4j (KG)   │   Elasticsearch   │   Vector store (Qdrant/pg)   │
│  Read-only role cho service account                              │
└─────────────────────────────────────────────────────────────────┘
```

**Trust boundaries:** Mỗi layer chỉ tin layer ngay dưới. LLM **không vượt qua Layer 4**.