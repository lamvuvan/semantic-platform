"""Summarize subgraph thành mô tả ngắn để giảm token cho LLM downstream."""
from __future__ import annotations

from collections import Counter

from agents.retrieval.subgraph_extractor import Subgraph


def summarize_customer(sub: Subgraph) -> str:
    """Vd: 'Khách C123 đặt 12 đơn 30 ngày qua, top 3 món: …; topping ưa thích: …'."""
    customer = next((n for n in sub.nodes if n["label"] == "Customer"), None)
    if customer is None:
        return "Không tìm thấy khách hàng."
    orders = [n for n in sub.nodes if n["label"] == "Order"]
    products = [n for n in sub.nodes if n["label"] == "Product"]
    toppings = [n for n in sub.nodes if n["label"] == "Topping"]
    top_p = [name for name, _ in Counter(p.get("name", "?") for p in products).most_common(3)]
    top_t = [name for name, _ in Counter(t.get("name", "?") for t in toppings).most_common(3)]
    return (
        f"Khách {customer.get('customer_id')}: {len(orders)} đơn gần đây, "
        f"top 3 món: {', '.join(top_p) or 'n/a'}; "
        f"topping ưa thích: {', '.join(top_t) or 'n/a'}."
    )


def summarize_product_neighborhood(sub: Subgraph) -> str:
    product = next((n for n in sub.nodes if n["label"] == "Product"), None)
    if product is None:
        return "Không tìm thấy sản phẩm."
    by_label = Counter(n["label"] for n in sub.nodes if n["label"] != "Product")
    detail = ", ".join(f"{lbl}: {cnt}" for lbl, cnt in by_label.most_common())
    return f"Sản phẩm {product.get('name')} ({product.get('product_id')}); lân cận → {detail}."
