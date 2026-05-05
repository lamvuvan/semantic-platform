// Subgraph quanh 1 product: variant + topping + category. Depth = 2.
// Tham số: $merchant_id, $product_id, $max_neighbors.

MATCH (:Merchant {merchant_id: $merchant_id})-[:OWNS]->(p:Product {product_id: $product_id})
OPTIONAL MATCH (p)-[:HAS_VARIANT]->(v:ProductVariant)
OPTIONAL MATCH (p)-[:OFFERS_TOPPING]->(t:Topping)
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
RETURN p,
       collect(DISTINCT v)[..$max_neighbors] AS variants,
       collect(DISTINCT t)[..$max_neighbors] AS toppings,
       collect(DISTINCT c)                   AS categories;
