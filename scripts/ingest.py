import argparse, os, json
from pathlib import Path
import pandas as pd
import duckdb

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "product_category_translation": "product_category_name_translation.csv",
}

DATE_COLS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

NUMERIC_CASTS = {
    "items": {
        "price": "float64",
        "freight_value": "float64",
        "shipping_limit_date": None,  # cast later to datetime
    },
    "payments": {
        "payment_sequential": "Int64",
        "payment_installments": "Int64",
        "payment_value": "float64",
    },
    "products": {
        "product_weight_g": "float64",
        "product_length_cm": "float64",
        "product_height_cm": "float64",
        "product_width_cm": "float64",
    },
}

def read_csv_clean(path: Path, name: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    # strip whitespace on strings
    for c in df.select_dtypes(include=["object"]).columns:
        df[c] = df[c].astype(str).str.strip()
        # normalize empty strings to NA
        df[c] = df[c].replace({"": pd.NA, "nan": pd.NA})
    # numeric casts
    if name in NUMERIC_CASTS:
        for col, dtype in NUMERIC_CASTS[name].items():
            if col in df.columns and dtype:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)
    # date casts
    if name in DATE_COLS:
        for col in DATE_COLS[name]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    # special case: items.shipping_limit_date
    if name == "items" and "shipping_limit_date" in df.columns:
        df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce", utc=True)
    return df

def write_parquet(df: pd.DataFrame, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path

def create_duckdb(parquet_map: dict, db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path.as_posix())
    con.execute("PRAGMA threads=4;")
    # Create tables from parquet (schema will be inferred from parquet types)
    for name, p in parquet_map.items():
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_parquet('{p.as_posix()}');")
    # Basic clustering for common access patterns (improves locality)
    con.execute("CREATE OR REPLACE TABLE orders AS SELECT * FROM orders ORDER BY order_purchase_timestamp;")
    con.execute("CREATE OR REPLACE TABLE items AS SELECT * FROM items ORDER BY order_id;")
    con.execute("CREATE OR REPLACE TABLE payments AS SELECT * FROM payments ORDER BY order_id;")
    con.execute("CREATE OR REPLACE TABLE reviews AS SELECT * FROM reviews ORDER BY review_creation_date;")
    con.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, help="Folder containing Olist CSVs")
    ap.add_argument("--processed-dir", default="data/processed", help="Folder to write parquet")
    ap.add_argument("--db-path", default="db/olist.duckdb", help="DuckDB output path")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)
    db_path = Path(args.db_path)

    # Validate presence of CSVs
    paths = {}
    missing = []
    for k, fname in RAW_FILES.items():
        p = raw_dir / fname
        if not p.exists():
            missing.append(p.as_posix())
        else:
            paths[k] = p
    if missing:
        raise FileNotFoundError("Missing required CSVs:\n" + "\n".join(missing))

    # Read → clean → parquet
    parquet_map = {}
    for name, p in paths.items():
        print(f"→ Loading {name} from {p.name}")
        df = read_csv_clean(p, name)
        # quick dedup pass on obvious keys (kept simple)
        if name in {"customers","sellers","products","geolocation","product_category_translation"}:
            df = df.drop_duplicates()
        pq = write_parquet(df, processed_dir, name)
        parquet_map[name] = pq
        print(f"  ✓ {name}: {len(df):,} rows → {pq.name}")

    # Build DuckDB
    create_duckdb(parquet_map, db_path)
    print(f"✅ DuckDB ready at {db_path}")

if __name__ == "__main__":
    main()
