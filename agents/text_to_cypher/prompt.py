"""Schema-aware few-shot prompt cho NL→Cypher fallback (read-only)."""
from __future__ import annotations

SCHEMA_HINT = """
KG schema (read-only):
- (Merchant)-[:OWNS]->(Product)
- (Product)-[:BELONGS_TO]->(Category)
- (Product)-[:HAS_VARIANT]->(ProductVariant)
- (Product)-[:OFFERS_TOPPING]->(Topping)
- (Customer)-[:PLACED]->(Order)
- (Order)-[:PLACED_AT]->(Merchant)
- (Order)-[:HAS_LINE]->(OrderLine)
- (OrderLine)-[:OF_PRODUCT]->(Product)
- (OrderLine)-[:OF_VARIANT]->(ProductVariant)
- (OrderLine)-[:WITH_TOPPING]->(Topping)
- (Product)-[:SIMILAR_TO]->(Product)
- (Customer)-[:FAVORS]->(Product)

Property keys: merchant_id, product_id, variant_id, topping_id, customer_id, order_id, line_id, name, ts, base_price, total, qty.
"""

FEWSHOT = """
Q: Top 5 topping bán chạy nhất tại merchant M01 trong 7 ngày qua
Cypher:
MATCH (m:Merchant {merchant_id: 'M01'})<-[:PLACED_AT]-(o:Order)-[:HAS_LINE]->(l:OrderLine)-[:WITH_TOPPING]->(t:Topping)
WHERE o.ts > datetime() - duration({days: 7})
RETURN t.name AS topping, sum(coalesce(l.qty, 1)) AS qty ORDER BY qty DESC LIMIT 5

Q: Khách hàng C123 đã đặt bao nhiêu đơn trong 30 ngày qua?
Cypher:
MATCH (c:Customer {customer_id: 'C123'})-[:PLACED]->(o:Order)
WHERE o.ts > datetime() - duration({days: 30})
RETURN count(o) AS orders
"""

SYSTEM = (
    "Bạn là trợ lý sinh Cypher truy vấn read-only cho Knowledge Graph F&B.\n"
    "QUY TẮC:\n"
    "1. CHỈ sinh truy vấn READ-ONLY (MATCH, RETURN). KHÔNG dùng CREATE/MERGE/DELETE/SET/REMOVE/CALL apoc.*.write.\n"
    "2. Luôn ràng buộc theo `merchant_id` từ context khi có.\n"
    "3. Không gọi function/procedure ngoài danh sách an toàn (db.index.fulltext.queryNodes, db.index.vector.queryNodes).\n"
    "4. Nếu câu hỏi vượt schema, trả về 'I_DONT_KNOW'.\n"
)


def build_prompt(question: str, merchant_id: str | None = None) -> str:
    ctx = f"Merchant context: {merchant_id}\n" if merchant_id else ""
    return f"{SYSTEM}\n{SCHEMA_HINT}\n{FEWSHOT}\n{ctx}Q: {question}\nCypher:\n"
