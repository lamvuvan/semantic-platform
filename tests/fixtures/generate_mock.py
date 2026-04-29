"""Generator dữ liệu mock F&B cho Knowledge Graph.

Sinh ra:
- Cypher seed script (`seed_full.cypher`) chạy được bằng `cypher-shell -f`
- Hoặc CSV theo schema gold (cho loader pipeline)

Sử dụng:
    python -m tests.fixtures.generate_mock --output tests/fixtures/seed_full.cypher
    python -m tests.fixtures.generate_mock --csv-dir /tmp/kg-csv

Tham số kiểm soát quy mô (mặc định ở mức demo, đủ chạy local):
    --merchants 5  --customers 50  --orders 200  --days 90
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TextIO

# ────────────────────────────────────────────────────────────────────────────
# Master data tĩnh (Vietnamese F&B realistic)
# ────────────────────────────────────────────────────────────────────────────

MERCHANTS_SEED = [
    {"merchant_id": "M01", "name": "Highlands Q1", "brand": "Highlands Coffee", "region": "south", "segment": "premium"},
    {"merchant_id": "M02", "name": "Phúc Long Q3", "brand": "Phúc Long", "region": "south", "segment": "premium"},
    {"merchant_id": "M03", "name": "Tocotoco Q5", "brand": "Tocotoco", "region": "south", "segment": "mass"},
    {"merchant_id": "M04", "name": "Cộng HN Hồ Tây", "brand": "Cộng Cà Phê", "region": "north", "segment": "premium"},
    {"merchant_id": "M05", "name": "Gong Cha Đà Nẵng", "brand": "Gong Cha", "region": "central", "segment": "premium"},
]

# Cây phân loại đa cấp.
CATEGORIES_TREE = {
    "CAT_BEVERAGE": {"name": "Đồ uống", "parent": None},
    "CAT_TEA": {"name": "Trà", "parent": "CAT_BEVERAGE"},
    "CAT_MILKTEA": {"name": "Trà sữa", "parent": "CAT_TEA"},
    "CAT_FRUITTEA": {"name": "Trà trái cây", "parent": "CAT_TEA"},
    "CAT_PURETEA": {"name": "Trà thuần", "parent": "CAT_TEA"},
    "CAT_COFFEE": {"name": "Cà phê", "parent": "CAT_BEVERAGE"},
    "CAT_BLACKCOFFEE": {"name": "Cà phê đen", "parent": "CAT_COFFEE"},
    "CAT_MILKCOFFEE": {"name": "Cà phê sữa", "parent": "CAT_COFFEE"},
    "CAT_SPECIALTY": {"name": "Specialty", "parent": "CAT_COFFEE"},
    "CAT_SMOOTHIE": {"name": "Sinh tố", "parent": "CAT_BEVERAGE"},
    "CAT_FOOD": {"name": "Đồ ăn", "parent": None},
    "CAT_SNACK": {"name": "Snack", "parent": "CAT_FOOD"},
    "CAT_DESSERT": {"name": "Tráng miệng", "parent": "CAT_FOOD"},
}

# (product_id, name, description, category_id, base_price, available_at_merchants)
PRODUCTS_SEED = [
    ("P001", "Trà sữa truyền thống", "Trà sữa truyền thống vị nguyên bản", "CAT_MILKTEA", 39000, ["M02", "M03", "M05"]),
    ("P002", "Trà sữa matcha", "Trà sữa matcha Nhật Bản đậm vị", "CAT_MILKTEA", 49000, ["M02", "M03", "M05"]),
    ("P003", "Hồng trà sữa", "Hồng trà sữa Anh quốc", "CAT_MILKTEA", 45000, ["M02", "M05"]),
    ("P004", "Olong sữa", "Trà olong sữa thơm dịu", "CAT_MILKTEA", 47000, ["M02", "M05"]),
    ("P005", "Trà đào cam sả", "Trà đào cam sả tươi mát", "CAT_FRUITTEA", 55000, ["M01", "M02"]),
    ("P006", "Trà vải", "Trà vải mát lạnh", "CAT_FRUITTEA", 49000, ["M01", "M02"]),
    ("P007", "Trà chanh", "Trà chanh truyền thống", "CAT_FRUITTEA", 35000, ["M01", "M02", "M03"]),
    ("P008", "Trà xanh", "Trà xanh thuần vị", "CAT_PURETEA", 30000, ["M02"]),
    ("P009", "Cà phê đen", "Cà phê đen Robusta đậm", "CAT_BLACKCOFFEE", 35000, ["M01", "M04"]),
    ("P010", "Cà phê sữa", "Cà phê sữa đá Sài Gòn", "CAT_MILKCOFFEE", 39000, ["M01", "M04"]),
    ("P011", "Bạc xỉu", "Bạc xỉu nhiều sữa", "CAT_MILKCOFFEE", 45000, ["M01", "M04"]),
    ("P012", "Latte", "Latte espresso + sữa nóng", "CAT_SPECIALTY", 55000, ["M01", "M04"]),
    ("P013", "Cappuccino", "Cappuccino bọt sữa dày", "CAT_SPECIALTY", 55000, ["M01", "M04"]),
    ("P014", "Espresso", "Espresso Ý nguyên chất", "CAT_SPECIALTY", 45000, ["M01", "M04"]),
    ("P015", "Sinh tố bơ", "Sinh tố bơ sáp đặc", "CAT_SMOOTHIE", 49000, ["M01", "M03"]),
    ("P016", "Sinh tố dâu", "Sinh tố dâu Đà Lạt", "CAT_SMOOTHIE", 49000, ["M01", "M03"]),
    ("P017", "Bánh flan", "Bánh flan caramel", "CAT_DESSERT", 25000, ["M01", "M02", "M04"]),
    ("P018", "Bánh mousse chocolate", "Mousse socola Bỉ", "CAT_DESSERT", 45000, ["M01", "M04"]),
    ("P019", "Bánh mì gà", "Bánh mì gà nướng", "CAT_SNACK", 35000, ["M01", "M04"]),
    ("P020", "Khoai tây chiên", "Khoai tây chiên giòn", "CAT_SNACK", 30000, ["M01", "M03"]),
]

# Variant chuẩn cho đồ uống.
DRINK_VARIANTS = [
    ("V_S", {"size": "S", "volume_ml": 350}, -5000),
    ("V_M", {"size": "M", "volume_ml": 500}, 0),
    ("V_L", {"size": "L", "volume_ml": 700}, 7000),
]
ICE_VARIANTS = [
    ("V_ICE_70", {"ice": "70%"}, 0),
    ("V_ICE_30", {"ice": "30%"}, 0),
    ("V_ICE_0", {"ice": "0%"}, 0),
]
SUGAR_VARIANTS = [
    ("V_SUG_100", {"sugar": "100%"}, 0),
    ("V_SUG_50", {"sugar": "50%"}, 0),
    ("V_SUG_0", {"sugar": "0%"}, 0),
]

TOPPINGS_SEED = [
    ("T01", "Trân châu đen", 7000, "pearl"),
    ("T02", "Trân châu trắng", 7000, "pearl"),
    ("T03", "Pudding trứng", 9000, "pudding"),
    ("T04", "Phô mai foam", 12000, "cheese"),
    ("T05", "Thạch dừa", 8000, "jelly"),
    ("T06", "Thạch trái cây", 8000, "jelly"),
    ("T07", "Kem cheese", 10000, "cream"),
    ("T08", "Đậu đỏ", 8000, "bean"),
    ("T09", "Hạt dẻ Hàn", 10000, "nut"),
    ("T10", "Whipping kem", 9000, "cream"),
]

# Topping nào phù hợp với category nào — để gắn OFFERS_TOPPING có nghĩa.
TOPPING_BY_CATEGORY = {
    "CAT_MILKTEA": ["T01", "T02", "T03", "T04", "T05", "T08"],
    "CAT_FRUITTEA": ["T05", "T06", "T07"],
    "CAT_PURETEA": ["T05", "T06"],
    "CAT_SPECIALTY": ["T07", "T10"],
    "CAT_SMOOTHIE": ["T07", "T10"],
}

CHANNELS = ["dine-in", "takeaway", "delivery"]
PAYMENT_METHODS = ["cash", "card", "momo", "zalopay", "vnpay"]
CUSTOMER_SEGMENTS = ["bronze", "silver", "gold", "platinum"]
LOYALTY_TIERS = ["new", "regular", "vip"]
REGIONS = ["north", "central", "south"]


@dataclass
class MockDataset:
    merchants: list[dict] = field(default_factory=list)
    categories: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    variants: list[dict] = field(default_factory=list)
    toppings: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    order_lines: list[dict] = field(default_factory=list)

    # edges
    e_owns: list[tuple[str, str]] = field(default_factory=list)
    e_belongs: list[tuple[str, str]] = field(default_factory=list)
    e_cat_parent: list[tuple[str, str]] = field(default_factory=list)
    e_has_variant: list[tuple[str, str]] = field(default_factory=list)
    e_offers_topping: list[tuple[str, str]] = field(default_factory=list)
    e_placed: list[tuple[str, str]] = field(default_factory=list)
    e_placed_at: list[tuple[str, str]] = field(default_factory=list)
    e_has_line: list[tuple[str, str]] = field(default_factory=list)
    e_line_of_product: list[tuple[str, str]] = field(default_factory=list)
    e_line_of_variant: list[tuple[str, str]] = field(default_factory=list)
    e_line_with_topping: list[tuple[str, str, int]] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def _hash_phone(phone: str, salt: str = "sp-mock-salt") -> str:
    return hashlib.sha256((salt + phone).encode()).hexdigest()


# ────────────────────────────────────────────────────────────────────────────
# Generation
# ────────────────────────────────────────────────────────────────────────────

def generate(
    n_merchants: int = 5,
    n_customers: int = 50,
    n_orders: int = 200,
    days: int = 90,
    seed: int = 42,
) -> MockDataset:
    rng = random.Random(seed)
    ds = MockDataset()

    # Merchants
    ds.merchants = MERCHANTS_SEED[:n_merchants]

    # Categories + parent edges
    for cid, info in CATEGORIES_TREE.items():
        ds.categories.append({"category_id": cid, "name": info["name"]})
        if info["parent"]:
            ds.e_cat_parent.append((cid, info["parent"]))

    # Products (chỉ sản phẩm có ít nhất 1 merchant trong scope)
    valid_merchant_ids = {m["merchant_id"] for m in ds.merchants}
    for pid, name, desc, cat, price, merchants in PRODUCTS_SEED:
        merchants_in_scope = [m for m in merchants if m in valid_merchant_ids]
        if not merchants_in_scope:
            continue
        ds.products.append({
            "product_id": pid,
            "name": name,
            "name_normalized": _normalize(name),
            "description": desc,
            "base_price": float(price),
            "status": "active",
        })
        ds.e_belongs.append((pid, cat))
        for mid in merchants_in_scope:
            ds.e_owns.append((mid, pid))

        # Variant: drink → all 3 axes; food → 1 size duy nhất
        is_drink = cat not in ("CAT_SNACK", "CAT_DESSERT")
        if is_drink:
            for axis_idx, axis in enumerate([DRINK_VARIANTS, ICE_VARIANTS, SUGAR_VARIANTS]):
                for vid_suffix, attrs, delta in axis:
                    vid = f"{pid}_{vid_suffix}"
                    ds.variants.append({
                        "variant_id": vid,
                        "attributes": json.dumps(attrs, ensure_ascii=False),
                        "price_delta": float(delta),
                    })
                    ds.e_has_variant.append((pid, vid))
            # Topping cho category liên quan
            for tid in TOPPING_BY_CATEGORY.get(cat, []):
                ds.e_offers_topping.append((pid, tid))
        else:
            vid = f"{pid}_DEFAULT"
            ds.variants.append({
                "variant_id": vid,
                "attributes": json.dumps({"size": "default"}),
                "price_delta": 0.0,
            })
            ds.e_has_variant.append((pid, vid))

    # Toppings
    for tid, name, price, t_cat in TOPPINGS_SEED:
        ds.toppings.append({
            "topping_id": tid,
            "name": name,
            "price": float(price),
            "category": t_cat,
        })

    # Customers
    base_signup = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(n_customers):
        cid = f"C{i+1:04d}"
        phone = f"09{rng.randint(10000000, 99999999)}"
        signup = base_signup + timedelta(days=rng.randint(0, 700))
        ds.customers.append({
            "customer_id": cid,
            "hashed_phone": _hash_phone(phone),
            "segment": rng.choice(CUSTOMER_SEGMENTS),
            "loyalty_tier": rng.choice(LOYALTY_TIERS),
            "signup_at": signup.isoformat(),
            "region": rng.choice(REGIONS),
        })

    # Orders + Lines
    now = datetime.now(timezone.utc)
    customer_ids = [c["customer_id"] for c in ds.customers]
    merchant_ids = [m["merchant_id"] for m in ds.merchants]
    products_by_merchant: dict[str, list[str]] = {}
    for mid, pid in ds.e_owns:
        products_by_merchant.setdefault(mid, []).append(pid)

    variants_by_product: dict[str, list[str]] = {}
    for pid, vid in ds.e_has_variant:
        variants_by_product.setdefault(pid, []).append(vid)

    toppings_by_product: dict[str, list[str]] = {}
    for pid, tid in ds.e_offers_topping:
        toppings_by_product.setdefault(pid, []).append(tid)

    for i in range(n_orders):
        order_id = f"O{i+1:06d}"
        merchant_id = rng.choice(merchant_ids)
        customer_id = rng.choice(customer_ids)
        ts = now - timedelta(days=rng.randint(0, days), minutes=rng.randint(0, 1440))
        channel = rng.choice(CHANNELS)
        payment = rng.choice(PAYMENT_METHODS)

        # 1-3 lines
        n_lines = rng.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
        candidate_products = products_by_merchant.get(merchant_id, [])
        if not candidate_products:
            continue
        chosen_pids = rng.sample(candidate_products, min(n_lines, len(candidate_products)))
        order_total = 0.0
        for j, pid in enumerate(chosen_pids):
            line_id = f"L{i+1:06d}_{j+1}"
            qty = rng.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
            # Lookup base price
            base_price = next(p["base_price"] for p in ds.products if p["product_id"] == pid)
            unit_price = float(base_price)
            order_total += unit_price * qty

            ds.order_lines.append({
                "line_id": line_id,
                "qty": qty,
                "unit_price": unit_price,
                "discount": 0.0,
            })
            ds.e_has_line.append((order_id, line_id))
            ds.e_line_of_product.append((line_id, pid))
            # Pick variant: ưu tiên Size M
            vids = variants_by_product.get(pid, [])
            if vids:
                # Bias size M
                v_size = next((v for v in vids if v.endswith("_V_M")), None) or rng.choice(vids)
                ds.e_line_of_variant.append((line_id, v_size))
            # 50% có topping nếu category cho phép
            if rng.random() < 0.5:
                tids = toppings_by_product.get(pid, [])
                if tids:
                    n_top = rng.choices([1, 2], weights=[0.7, 0.3])[0]
                    for tid in rng.sample(tids, min(n_top, len(tids))):
                        ds.e_line_with_topping.append((line_id, tid, 1))

        ds.orders.append({
            "order_id": order_id,
            "ts": ts.isoformat(),
            "channel": channel,
            "payment_method": payment,
            "total": round(order_total, 2),
            "currency": "VND",
        })
        ds.e_placed.append((customer_id, order_id))
        ds.e_placed_at.append((order_id, merchant_id))

    return ds


# ────────────────────────────────────────────────────────────────────────────
# Cypher emitter
# ────────────────────────────────────────────────────────────────────────────

def _props(d: dict, exclude: tuple[str, ...] = ()) -> str:
    parts = []
    for k, v in d.items():
        if k in exclude:
            continue
        if isinstance(v, str):
            esc = v.replace("\\", "\\\\").replace("'", "\\'")
            parts.append(f"{k}: '{esc}'")
        elif v is None:
            parts.append(f"{k}: null")
        elif isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        else:
            parts.append(f"{k}: {v}")
    return "{" + ", ".join(parts) + "}"


def emit_cypher(ds: MockDataset, out: TextIO) -> None:
    out.write("// Auto-generated mock seed — KHÔNG sửa tay.\n")
    out.write("// Sinh từ tests/fixtures/generate_mock.py\n\n")

    # Merchants
    for m in ds.merchants:
        out.write(f"MERGE (n:Merchant {{merchant_id: '{m['merchant_id']}'}}) SET n += {_props(m, ('merchant_id',))};\n")
    # Categories
    for c in ds.categories:
        out.write(f"MERGE (n:Category {{category_id: '{c['category_id']}'}}) SET n += {_props(c, ('category_id',))};\n")
    # Category parent edges (PART_OF)
    for child, parent in ds.e_cat_parent:
        out.write(
            f"MATCH (a:Category {{category_id: '{child}'}}), (b:Category {{category_id: '{parent}'}}) "
            f"MERGE (a)-[:PART_OF]->(b);\n"
        )
    # Products
    for p in ds.products:
        out.write(f"MERGE (n:Product {{product_id: '{p['product_id']}'}}) SET n += {_props(p, ('product_id',))};\n")
    # Variants
    for v in ds.variants:
        out.write(f"MERGE (n:ProductVariant {{variant_id: '{v['variant_id']}'}}) SET n += {_props(v, ('variant_id',))};\n")
    # Toppings
    for t in ds.toppings:
        out.write(f"MERGE (n:Topping {{topping_id: '{t['topping_id']}'}}) SET n += {_props(t, ('topping_id',))};\n")
    # Customers
    for c in ds.customers:
        out.write(f"MERGE (n:Customer {{customer_id: '{c['customer_id']}'}}) SET n += {_props(c, ('customer_id',))};\n")

    # Edges master
    for mid, pid in ds.e_owns:
        out.write(
            f"MATCH (m:Merchant {{merchant_id: '{mid}'}}), (p:Product {{product_id: '{pid}'}}) MERGE (m)-[:OWNS]->(p);\n"
        )
    for pid, cid in ds.e_belongs:
        out.write(
            f"MATCH (p:Product {{product_id: '{pid}'}}), (c:Category {{category_id: '{cid}'}}) MERGE (p)-[:BELONGS_TO]->(c);\n"
        )
    for pid, vid in ds.e_has_variant:
        out.write(
            f"MATCH (p:Product {{product_id: '{pid}'}}), (v:ProductVariant {{variant_id: '{vid}'}}) MERGE (p)-[:HAS_VARIANT]->(v);\n"
        )
    for pid, tid in ds.e_offers_topping:
        out.write(
            f"MATCH (p:Product {{product_id: '{pid}'}}), (t:Topping {{topping_id: '{tid}'}}) MERGE (p)-[:OFFERS_TOPPING]->(t);\n"
        )

    # Orders + Lines
    for o in ds.orders:
        out.write(
            f"MERGE (n:Order {{order_id: '{o['order_id']}'}}) "
            f"SET n.ts = datetime('{o['ts']}'), n.channel = '{o['channel']}', "
            f"n.payment_method = '{o['payment_method']}', n.total = {o['total']}, n.currency = '{o['currency']}';\n"
        )
    for line in ds.order_lines:
        out.write(
            f"MERGE (n:OrderLine {{line_id: '{line['line_id']}'}}) "
            f"SET n.qty = {line['qty']}, n.unit_price = {line['unit_price']}, n.discount = {line['discount']};\n"
        )

    # Edges fact
    for cid, oid in ds.e_placed:
        out.write(
            f"MATCH (c:Customer {{customer_id: '{cid}'}}), (o:Order {{order_id: '{oid}'}}) MERGE (c)-[:PLACED]->(o);\n"
        )
    for oid, mid in ds.e_placed_at:
        out.write(
            f"MATCH (o:Order {{order_id: '{oid}'}}), (m:Merchant {{merchant_id: '{mid}'}}) MERGE (o)-[:PLACED_AT]->(m);\n"
        )
    for oid, lid in ds.e_has_line:
        out.write(
            f"MATCH (o:Order {{order_id: '{oid}'}}), (l:OrderLine {{line_id: '{lid}'}}) MERGE (o)-[:HAS_LINE]->(l);\n"
        )
    for lid, pid in ds.e_line_of_product:
        out.write(
            f"MATCH (l:OrderLine {{line_id: '{lid}'}}), (p:Product {{product_id: '{pid}'}}) MERGE (l)-[:OF_PRODUCT]->(p);\n"
        )
    for lid, vid in ds.e_line_of_variant:
        out.write(
            f"MATCH (l:OrderLine {{line_id: '{lid}'}}), (v:ProductVariant {{variant_id: '{vid}'}}) MERGE (l)-[:OF_VARIANT]->(v);\n"
        )
    for lid, tid, qty in ds.e_line_with_topping:
        out.write(
            f"MATCH (l:OrderLine {{line_id: '{lid}'}}), (t:Topping {{topping_id: '{tid}'}}) "
            f"MERGE (l)-[r:WITH_TOPPING]->(t) SET r.qty = {qty};\n"
        )


# ────────────────────────────────────────────────────────────────────────────
# CSV emitter (theo format gold cho loader)
# ────────────────────────────────────────────────────────────────────────────

def emit_csv(ds: MockDataset, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "kg_nodes_merchant": ds.merchants,
        "kg_nodes_category": ds.categories,
        "kg_nodes_product": ds.products,
        "kg_nodes_product_variant": ds.variants,
        "kg_nodes_topping": ds.toppings,
        "kg_nodes_customer": ds.customers,
        "kg_nodes_order": ds.orders,
        "kg_nodes_order_line": ds.order_lines,
    }
    for name, rows in tables.items():
        path = out_dir / f"{name}.csv"
        if not rows:
            path.write_text("")
            continue
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    # edges
    edge_files = {
        "kg_edges_merchant_owns_product": [{"src": s, "dst": d} for s, d in ds.e_owns],
        "kg_edges_product_category": [{"src": s, "dst": d} for s, d in ds.e_belongs],
        "kg_edges_category_parent": [{"src": s, "dst": d} for s, d in ds.e_cat_parent],
        "kg_edges_product_variant": [{"src": s, "dst": d} for s, d in ds.e_has_variant],
        "kg_edges_product_topping": [{"src": s, "dst": d} for s, d in ds.e_offers_topping],
        "kg_edges_customer_placed_order": [{"src": s, "dst": d} for s, d in ds.e_placed],
        "kg_edges_order_placed_at_merchant": [{"src": s, "dst": d} for s, d in ds.e_placed_at],
        "kg_edges_order_has_line": [{"src": s, "dst": d} for s, d in ds.e_has_line],
        "kg_edges_line_of_product": [{"src": s, "dst": d} for s, d in ds.e_line_of_product],
        "kg_edges_line_of_variant": [{"src": s, "dst": d} for s, d in ds.e_line_of_variant],
        "kg_edges_line_with_topping": [{"src": s, "dst": d, "qty": q} for s, d, q in ds.e_line_with_topping],
    }
    for name, rows in edge_files.items():
        path = out_dir / f"{name}.csv"
        if not rows:
            path.write_text("src,dst\n")
            continue
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merchants", type=int, default=5)
    parser.add_argument("--customers", type=int, default=50)
    parser.add_argument("--orders", type=int, default=200)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, help="Cypher seed output file")
    parser.add_argument("--csv-dir", type=Path, help="Directory để xuất CSV theo format gold")
    parser.add_argument("--summary", action="store_true", help="In thống kê dataset")
    args = parser.parse_args()

    ds = generate(
        n_merchants=args.merchants,
        n_customers=args.customers,
        n_orders=args.orders,
        days=args.days,
        seed=args.seed,
    )

    if args.summary or (not args.output and not args.csv_dir):
        summary = {
            "merchants": len(ds.merchants),
            "categories": len(ds.categories),
            "products": len(ds.products),
            "variants": len(ds.variants),
            "toppings": len(ds.toppings),
            "customers": len(ds.customers),
            "orders": len(ds.orders),
            "order_lines": len(ds.order_lines),
            "e_owns": len(ds.e_owns),
            "e_offers_topping": len(ds.e_offers_topping),
            "e_line_with_topping": len(ds.e_line_with_topping),
        }
        print(json.dumps(summary, indent=2))

    if args.output:
        with args.output.open("w") as f:
            emit_cypher(ds, f)
        print(f"wrote Cypher seed → {args.output}")

    if args.csv_dir:
        emit_csv(ds, args.csv_dir)
        print(f"wrote CSV → {args.csv_dir}")


if __name__ == "__main__":
    main()
