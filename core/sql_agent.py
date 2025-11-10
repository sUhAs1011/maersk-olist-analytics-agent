# core/sql_agent.py
import os, re, json
from pathlib import Path

import duckdb
import pandas as pd
import sqlparse
from dotenv import load_dotenv
import google.generativeai as genai

# --------------------------------------------------------------------------------------
# Env & paths (patched to load .env reliably)
# --------------------------------------------------------------------------------------

# Locate repo root (parent of /core)
REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"

# Force load .env from repo root
load_dotenv(dotenv_path=ENV_PATH, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # default current model

if not GEMINI_API_KEY:
    raise RuntimeError(f"❌ GEMINI_API_KEY not found. Expected in: {ENV_PATH}")

genai.configure(api_key=GEMINI_API_KEY)

DEFAULT_DB = REPO_ROOT / "db" / "olist.duckdb"
DEFAULT_SCHEMA = REPO_ROOT / "docs" / "schema.json"

# --------------------------------------------------------------------------------------
# Prompt & examples
# --------------------------------------------------------------------------------------
_SYS_PROMPT = """You convert a user's analytics question into a SINGLE DuckDB SQL SELECT (or CTE+SELECT).
Rules:
- Output only SQL (no prose).
- Use ONLY the provided schema (tables/columns).
- No DDL/DML and no modifications (no CREATE/INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE).
- Prefer ANSI SQL.
- Add clear aliases for aggregates (e.g., AS revenue).
"""

_EXAMPLES = [
    ("Top 5 product categories by revenue",
     """WITH rev AS (
  SELECT i.product_id, (i.price + i.freight_value) AS line_rev
  FROM items i
)
SELECT p.product_category_name, SUM(r.line_rev) AS revenue
FROM rev r
JOIN products p ON p.product_id = r.product_id
GROUP BY 1
ORDER BY revenue DESC
LIMIT 5;"""),

    ("Average delivery delay (days) by state",
     """SELECT c.customer_state,
       AVG(date_diff('day', o.order_estimated_delivery_date, o.order_delivered_customer_date)) AS avg_delay_days
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY 1
ORDER BY avg_delay_days DESC;"""),

    ("How many orders per month in 2018?",
     """SELECT date_trunc('month', o.order_purchase_timestamp) AS month,
       COUNT(*) AS orders
FROM orders o
WHERE EXTRACT(YEAR FROM o.order_purchase_timestamp) = 2018
GROUP BY 1
ORDER BY 1;"""),

    ("Share of payment types by count",
     """SELECT payment_type, COUNT(*) AS cnt
FROM payments
GROUP BY 1
ORDER BY cnt DESC;"""),

    ("Average review score by product category (top 10)",
     """SELECT p.product_category_name, AVG(r.review_score) AS avg_score
FROM items i
JOIN products p ON p.product_id = i.product_id
JOIN reviews r ON r.order_id = i.order_id
GROUP BY 1
ORDER BY avg_score DESC
LIMIT 10;"""),

    ("Top 10 cities by total freight value",
     """SELECT c.customer_city, SUM(i.freight_value) AS total_freight
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN items i ON i.order_id = o.order_id
GROUP BY 1
ORDER BY total_freight DESC
LIMIT 10;"""),

    ("Overall late delivery rate",
     """SELECT
  100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END)
  / NULLIF(COUNT(*),0) AS late_rate_pct
FROM orders o
WHERE o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL;"""),

    ("Top categories by revenue with English names",
     """WITH line AS (
  SELECT i.product_id, (i.price + i.freight_value) AS line_rev
  FROM items i
)
SELECT t.product_category_name_english AS category_en,
       SUM(l.line_rev) AS revenue
FROM line l
JOIN products p ON p.product_id = l.product_id
LEFT JOIN product_category_translation t
  ON t.product_category_name = p.product_category_name
GROUP BY 1
ORDER BY revenue DESC
LIMIT 10;"""),
]

# --------------------------------------------------------------------------------------
# Prompt builders
# --------------------------------------------------------------------------------------
def _schema_text(schema_json: dict) -> str:
    parts = []
    for t, cols in schema_json.items():
        cols_str = ", ".join([f"{c['name']}:{c.get('type','')}" for c in cols])
        parts.append(f"{t}({cols_str})")
    return "\n".join(parts)

def _examples_text() -> str:
    return "\n\n".join([f"-- Q: {q}\n{sql}" for q, sql in _EXAMPLES])

def build_prompt(schema_json: dict, question: str) -> str:
    return f"""{_SYS_PROMPT}

SCHEMA:
{_schema_text(schema_json)}

EXAMPLES:
{_examples_text()}

Now write only SQL for:
Q: {question}
SQL:
""".strip()

# --------------------------------------------------------------------------------------
# Safety & helpers
# --------------------------------------------------------------------------------------
def is_safe_select(sql: str) -> bool:
    statements = [s for s in sqlparse.split(sql) if s.strip()]
    if len(statements) != 1:
        return False
    sql_up = statements[0].upper()
    banned = ["INSERT","UPDATE","DELETE","DROP","ALTER","CREATE",
              "REPLACE","TRUNCATE","ATTACH","DETACH","PRAGMA","COPY"]
    if any(b in sql_up for b in banned):
        return False
    first = sqlparse.parse(statements[0])[0]
    tokens = [t for t in first.tokens if not t.is_whitespace]
    head = tokens[0].value.upper() if tokens else ""
    return head.startswith("SELECT") or head.startswith("WITH")

_CODE_FENCE_RE = re.compile(r"```sql\s*(.*?)```", flags=re.I|re.S)
def _extract_code_block(text: str) -> str:
    m = _CODE_FENCE_RE.search(text or "")
    if m:
        return m.group(1).strip()
    return (text or "").strip().strip("`")

def _call_gemini(prompt: str, model: str) -> str:
    try:
        return genai.GenerativeModel(model).generate_content(prompt).text
    except Exception as e:
        if "NotFound" in str(e):
            for alt in ["gemini-1.5-flash-8b","gemini-1.5-pro-002"]:
                try: return genai.GenerativeModel(alt).generate_content(prompt).text
                except: pass
        raise

# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
def generate_sql(question: str, schema_json: dict, model: str = MODEL) -> str:
    prompt = build_prompt(schema_json, question)
    return _extract_code_block(_call_gemini(prompt, model))

def execute_sql(sql: str, db_path: Path | str = DEFAULT_DB):
    db_path = Path(db_path)
    con = duckdb.connect(str(db_path))
    try:    return con.execute(sql).fetchdf(), None
    except Exception as e: return None, str(e)
    finally: con.close()

def ask(question: str,
        schema_path: Path | str = DEFAULT_SCHEMA,
        db_path: Path | str = DEFAULT_DB,
        retry: bool = True):

    schema_path = Path(schema_path)
    db_path = Path(db_path)

    if not schema_path.exists(): raise FileNotFoundError(f"Schema not found: {schema_path}")
    if not db_path.exists(): raise FileNotFoundError(f"DuckDB not found: {db_path}")

    schema_json = json.load(open(schema_path,"r",encoding="utf-8"))
    sql = generate_sql(question, schema_json)

    if not is_safe_select(sql): return None, sql, "❌ Unsafe SQL blocked"

    df, err = execute_sql(sql, db_path)

    if err and retry:
        repair = build_prompt(schema_json, question) + f"\n\nError:\n{err}\nFix SQL only:"
        try:
            sql2 = _extract_code_block(_call_gemini(repair, MODEL))
            if is_safe_select(sql2):
                return execute_sql(sql2, db_path)[0], sql2, None
        except: pass

    return df, sql, err
