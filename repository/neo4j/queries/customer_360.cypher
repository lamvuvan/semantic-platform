// Layer 2 — DAO query: lấy ngữ cảnh 360 của 1 khách hàng theo merchant.
// Tham số: $merchant_id (string), $customer_id (string), $days (int).
// Tenant scoping: merchant_id BẮT BUỘC, được Layer 3 chèn từ JWT.

MATCH (m:Merchant {merchant_id: $merchant_id})<-[:PLACED_AT]-(o:Order)<-[:PLACED]-(c:Customer {customer_id: $customer_id})
WHERE o.ts > datetime() - duration({days: $days})
OPTIONAL MATCH (o)-[:HAS_LINE]->(l:OrderLine)-[:OF_PRODUCT]->(p:Product)
OPTIONAL MATCH (l)-[:WITH_TOPPING]->(t:Topping)
WITH c, m,
     count(DISTINCT o)                                AS order_count,
     sum(coalesce(o.total, 0))                        AS gmv,
     collect(DISTINCT {id: p.product_id, name: p.name})[..10] AS top_products,
     collect(DISTINCT {id: t.topping_id, name: t.name})[..10] AS top_toppings
RETURN c.customer_id   AS customer_id,
       c.segment       AS segment,
       c.loyalty_tier  AS loyalty_tier,
       order_count,
       gmv,
       top_products,
       top_toppings;
