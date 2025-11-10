# core/schema_utils.py
import argparse, json
from pathlib import Path
import duckdb

# Resolve repo root = parent of this file's directory
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "db" / "olist.duckdb"
DOCS_DIR = REPO_ROOT / "docs"

HINTS = {
    "orders.order_purchase_timestamp": "UTC timestamp when order was placed",
    "orders.order_estimated_delivery_date": "Estimated delivery date",
    "orders.order_delivered_customer_date": "Actual delivery date to customer",
    "items.price": "Item price in BRL",
    "items.freight_value": "Shipping (freight) value in BRL",
    "payments.payment_value": "Total paid value for the order",
    "reviews.review_score": "Customer review score (1-5)",
    "products.product_category_name": "Original Portuguese category name",
    "product_category_translation.product_category_name_english": "Category name in English",
}

def get_schema(db_path: Path):
    con = duckdb.connect(str(db_path))
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY 1"
    ).fetchall()]
    schema = {}
    for t in tables:
        cols = con.execute(f"PRAGMA table_info('{t}')").fetchall()
        schema[t] = []
        for c in cols:
            col = {"name": c[1], "type": c[2]}
            key = f"{t}.{c[1]}"
            if key in HINTS:
                col["hint"] = HINTS[key]
            schema[t].append(col)
    con.close()
    return schema

def write_schema_files(schema, out_json: Path, out_md: Path):
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Olist DB Schema\n\n")
        for t, cols in schema.items():
            f.write(f"## {t}\n\n")
            for c in cols:
                hint = f" – {c['hint']}" if "hint" in c else ""
                f.write(f"- `{c['name']}` ({c['type']}){hint}\n")
            f.write("\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path", type=str, default=str(DEFAULT_DB))
    ap.add_argument("--out-json", type=str, default=str(DOCS_DIR / "schema.json"))
    ap.add_argument("--out-md", type=str, default=str(DOCS_DIR / "schema.md"))
    args = ap.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at: {db_path}\n"
                                f"Tip: run ingest first or pass --db-path with the correct absolute path.")

    schema = get_schema(db_path)
    write_schema_files(schema, Path(args.out_json), Path(args.out_md))
    print(f"✅ Wrote {args.out_json} and {args.out_md}")
