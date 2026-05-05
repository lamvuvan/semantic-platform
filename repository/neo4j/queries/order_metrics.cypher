// Aggregate metric đơn giản theo merchant + khoảng thời gian.
// Tham số: $merchant_id, $from_iso, $to_iso, $metric (revenue|qty|top_products|top_toppings).

CALL {
  WITH $metric AS metric, $merchant_id AS mid, $from_iso AS f, $to_iso AS t
  MATCH (m:Merchant {merchant_id: mid})<-[:PLACED_AT]-(o:Order)
  WHERE (f IS NULL OR o.ts >= datetime(f))
    AND (t IS NULL OR o.ts <= datetime(t))
  WITH metric, o
  OPTIONAL MATCH (o)-[:HAS_LINE]->(l:OrderLine)
  OPTIONAL MATCH (l)-[:OF_PRODUCT]->(p:Product)
  OPTIONAL MATCH (l)-[:WITH_TOPPING]->(top:Topping)
  RETURN metric, o, l, p, top
}
WITH metric, collect({o:o, l:l, p:p, top:top}) AS rows
RETURN metric, rows;
