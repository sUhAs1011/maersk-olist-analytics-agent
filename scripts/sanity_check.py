from pathlib import Path
import duckdb, pandas as pd
from tabulate import tabulate

DB_PATH = "db/olist.duckdb"
REPORT_MD = "docs/ingest_report.md"

FK_CHECKS = [
    # (child_table, child_key, parent_table, parent_key, label)
    ("items", "order_id", "orders", "order_id", "items→orders"),
    ("items", "product_id", "products", "product_id", "items→products"),
    ("orders", "customer_id", "customers", "customer_id", "orders→customers"),
    ("payments", "order_id", "orders", "order_id", "payments→orders"),
    ("reviews", "order_id", "orders", "order_id", "reviews→orders"),
]

KEY_NULLS = [
    ("orders", ["order_id", "customer_id"]),
    ("items", ["order_id", "product_id"]),
    ("payments", ["order_id"]),
    ("reviews", ["order_id", "review_score"]),
    ("customers", ["customer_id"]),
    ("products", ["product_id"]),
    ("sellers", ["seller_id"]),
]

def row_counts(con):
    q = """
    SELECT table_name, row_count
    FROM duckdb_tables() WHERE database_name='memory' = FALSE;
    """
    # Better: use information_schema
    q = """
    SELECT table_name,
           (SELECT COUNT(*) FROM (SELECT * FROM main.||table_name||)) AS row_count
    FROM information_schema.tables
    WHERE table_schema='main'
    ORDER BY table_name;
    """
    # Use Python approach to loop over tables for clarity
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY 1"
    ).fetchall()]
    data = []
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        data.append((t, n))
    return pd.DataFrame(data, columns=["table", "rows"])

def null_rates(con):
    rows = []
    for t, cols in KEY_NULLS:
        total = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for c in cols:
            nnull = con.execute(f"SELECT COUNT(*) FROM {t} WHERE {c} IS NULL").fetchone()[0]
            rows.append((t, c, total, nnull, round((nnull/total*100) if total else 0, 4)))
    return pd.DataFrame(rows, columns=["table","column","total_rows","null_rows","null_pct"])

def fk_violations(con):
    rows = []
    for child, ckey, parent, pkey, label in FK_CHECKS:
        n = con.execute(f"""
            SELECT COUNT(*) FROM {child} ch
            LEFT JOIN {parent} p ON ch.{ckey} = p.{pkey}
            WHERE p.{pkey} IS NULL
        """).fetchone()[0]
        rows.append((label, child, ckey, parent, pkey, n))
    return pd.DataFrame(rows, columns=["check","child_table","child_key","parent_table","parent_key","violations"])

def write_report(rc_df, nr_df, fk_df):
    Path("docs").mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("# Ingestion & Sanity Report\n\n")
        f.write("## Row counts\n\n")
        f.write(tabulate(rc_df, headers="keys", tablefmt="github"))
        f.write("\n\n## Key column null rates\n\n")
        f.write(tabulate(nr_df, headers="keys", tablefmt="github"))
        f.write("\n\n## Referential integrity (violations)\n\n")
        f.write(tabulate(fk_df, headers="keys", tablefmt="github"))
        f.write("\n")

def main():
    con = duckdb.connect(DB_PATH)
    rc = row_counts(con)
    nr = null_rates(con)
    fk = fk_violations(con)
    write_report(rc, nr, fk)
    con.close()
    print("✅ Wrote docs/ingest_report.md")

if __name__ == "__main__":
    main()
