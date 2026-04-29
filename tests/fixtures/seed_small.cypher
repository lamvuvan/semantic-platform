// Seed dataset cho integration test + eval.
CREATE (m:Merchant {merchant_id: 'M01', name: 'Highlands Q1', region: 'south', segment: 'flagship'});

CREATE (cTea:Category {category_id: 'CAT_TEA', name: 'Trà sữa'});

CREATE (p1:Product {product_id: 'P_TS_M', name: 'Trà sữa size M', name_normalized: 'tra sua size m', description: 'Trà sữa size M truyền thống', base_price: 39000.0, status: 'active'});
CREATE (p2:Product {product_id: 'P_MAT_M', name: 'Matcha latte M', name_normalized: 'matcha latte m', description: 'Matcha latte size M', base_price: 49000.0, status: 'active'});

CREATE (m)-[:OWNS]->(p1);
CREATE (m)-[:OWNS]->(p2);
CREATE (p1)-[:BELONGS_TO]->(cTea);

CREATE (vS:ProductVariant {variant_id: 'V_TS_S', attributes: 'size=S'});
CREATE (vM:ProductVariant {variant_id: 'V_TS_M', attributes: 'size=M'});
CREATE (vL:ProductVariant {variant_id: 'V_TS_L', attributes: 'size=L'});
CREATE (p1)-[:HAS_VARIANT]->(vS);
CREATE (p1)-[:HAS_VARIANT]->(vM);
CREATE (p1)-[:HAS_VARIANT]->(vL);

CREATE (tPearl:Topping {topping_id: 'T_PEARL', name: 'Trân châu đen', price: 7000.0, category: 'pearl'});
CREATE (tCheese:Topping {topping_id: 'T_CHEESE', name: 'Phô mai', price: 10000.0, category: 'cheese'});
CREATE (p1)-[:OFFERS_TOPPING]->(tPearl);
CREATE (p1)-[:OFFERS_TOPPING]->(tCheese);

CREATE (c:Customer {customer_id: 'C123', segment: 'gold', region: 'south'});
CREATE (o:Order {order_id: 'O1001', ts: datetime(), channel: 'takeaway', payment_method: 'card', total: 100000.0});
CREATE (c)-[:PLACED]->(o);
CREATE (o)-[:PLACED_AT]->(m);

CREATE (l:OrderLine {line_id: 'L1', qty: 1, unit_price: 39000.0});
CREATE (o)-[:HAS_LINE]->(l);
CREATE (l)-[:OF_PRODUCT]->(p1);
CREATE (l)-[:OF_VARIANT]->(vM);
CREATE (l)-[:WITH_TOPPING {qty: 1}]->(tPearl);
