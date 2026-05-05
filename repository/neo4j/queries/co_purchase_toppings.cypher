// Tìm topping hay được mua kèm 1 sản phẩm tại 1 merchant.
// Tham số: $merchant_id, $product_id, $k.

MATCH (:Merchant {merchant_id: $merchant_id})<-[:PLACED_AT]-(o:Order)
      -[:HAS_LINE]->(l:OrderLine)-[:OF_PRODUCT]->(p:Product {product_id: $product_id})
WITH o
MATCH (o)-[:HAS_LINE]->(:OrderLine)-[:WITH_TOPPING]->(t:Topping)
WITH t, count(DISTINCT o) AS cnt
RETURN t.topping_id AS topping_id,
       t.name       AS name,
       cnt          AS frequency
ORDER BY frequency DESC LIMIT $k;
