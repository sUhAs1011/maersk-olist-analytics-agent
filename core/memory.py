from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

# Store “insights” in repo_root/data/cache/insights.json
REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "cache"
INSIGHTS_PATH = CACHE_DIR / "insights.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def load_insights() -> list[dict]:
    if INSIGHTS_PATH.exists():
        try:
            return json.loads(INSIGHTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_insights(items: list[dict]):
    INSIGHTS_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

def add_insight(question: str, summary: str, sql: str | None, sample_rows: int | None = None):
    items = load_insights()
    items.append({
        "timestamp": _now(),
        "question": question,
        "summary": summary,
        "sql": sql or "",
        "sample_rows": sample_rows or 0
    })
    save_insights(items)

def clear_insights():
    save_insights([])
