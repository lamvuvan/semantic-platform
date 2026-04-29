"""GraphRAG: lấy context từ retriever + format answer cho LLM self-host."""
from __future__ import annotations

from agents.retrieval.pipeline import ContextObject, ContextRetriever


def build_answer_prompt(question: str, ctx: ContextObject) -> str:
    summaries = "\n".join(f"- {s}" for s in ctx.summaries) or "(không có summary)"
    nodes = ctx.subgraph.get("nodes", [])[:20]
    nodes_str = "\n".join(f"- {n.get('label')}: {n.get('name', n)}" for n in nodes)
    return (
        "Trả lời câu hỏi dựa CHỈ trên context được cung cấp. "
        "Nếu không đủ thông tin, nói 'Không đủ dữ liệu'.\n\n"
        f"### Câu hỏi\n{question}\n\n"
        f"### Summaries\n{summaries}\n\n"
        f"### Top nodes\n{nodes_str}\n\n"
        f"### Evidence Cypher\n{ctx.evidence_cypher}\n"
    )


def answer(retriever: ContextRetriever, intent: str, question: str, **kwargs) -> str:
    ctx = retriever.retrieve(intent=intent, query=question, **kwargs)
    return build_answer_prompt(question, ctx)
