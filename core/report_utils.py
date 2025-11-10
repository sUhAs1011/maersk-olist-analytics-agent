from __future__ import annotations
import io
from pathlib import Path
import pandas as pd
from textwrap import fill
from markdown import markdown as md_to_html
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# ---------- heuristics to turn a result DF into a paragraph ----------
def summarize_df(df: pd.DataFrame, question: str) -> str:
    if df is None or df.empty:
        return f"Query: **{question}**\n\nNo rows returned."
    # choose a simple narrative
    head = df.head(10)
    cols = list(head.columns)
    para = [f"**Question:** {question}"]

    # totals if numeric
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(head[c])]
    if num_cols:
        sums = {c: float(head[c].sum()) for c in num_cols}
        topnum = max(sums, key=sums.get)
        para.append(f"- Top numeric column (by head sum): **{topnum}** = {sums[topnum]:,.2f}")

    # if looks like ranking (two cols: cat + num)
    if len(cols) == 2 and (cols[0] not in num_cols) and (cols[1] in num_cols):
        top_row = head.sort_values(cols[1], ascending=False).iloc[0]
        para.append(f"- Top **{cols[0]}**: **{top_row[cols[0]]}** with {cols[1]} = {float(top_row[cols[1]]):,.2f}")

    # if time series present
    date_cols = [c for c in cols if "date" in c.lower() or "month" in c.lower() or "timestamp" in c.lower()]
    for dc in date_cols:
        if pd.api.types.is_datetime64_any_dtype(head[dc]):
            para.append(f"- Time column detected: **{dc}** (showing {len(head)} recent/first rows).")
            break

    # include first 3 rows as bullets
    bullets = []
    for _, r in head.head(3).iterrows():
        frag = ", ".join([f"{c}={r[c]}" for c in cols[:3]])
        bullets.append(f"  - {frag}")
    if bullets:
        para.append("- Sample rows:\n" + "\n".join(bullets))

    return "\n".join(para)

# ---------- compile insights to Markdown ----------
def insights_to_markdown(insights: list[dict], title="Olist InsightGPT — Analysis Report", author="Auto-Analyst") -> str:
    lines = [f"# {title}", "", f"_Author: {author}_", ""]
    if not insights:
        lines += ["*(No insights saved yet — use **Save insight** after a query.)*"]
        return "\n".join(lines)
    for i, it in enumerate(insights, 1):
        lines += [
            f"## Insight {i}",
            f"**Time:** {it.get('timestamp','')}",
            f"**Question:** {it.get('question','')}",
            "",
            it.get("summary",""),
        ]
        if it.get("sql"):
            lines += ["", "```sql", it["sql"], "```"]
        lines.append("")
    return "\n".join(lines)

# ---------- simple Markdown → PDF (text only, no images) ----------
def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    # Convert MD to plain-ish text (strip HTML tags by keeping text content)
    # We'll do a lightweight approach: drop tags, keep lines
    # For nicer typography, you could render HTML → PDF via WeasyPrint (not used here).
    plain = _md_to_plain(markdown_text)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    x, y = 2*cm, height - 2*cm
    max_width_chars = 95

    for line in plain.splitlines():
        for wrapped in _wrap(line, max_width_chars).splitlines():
            if y < 2*cm:
                c.showPage()
                y = height - 2*cm
            c.drawString(x, y, wrapped)
            y -= 14
    c.save()
    buf.seek(0)
    return buf.read()

def _wrap(text: str, width: int) -> str:
    return "\n".join([fill(s, width=width) for s in text.split("\n")])

def _md_to_plain(markdown_text: str) -> str:
    # Very small converter: strip "**", "`", "#" and leave content
    text = markdown_text.replace("**", "").replace("`", "")
    lines = []
    for line in text.splitlines():
        line = line.lstrip("# ").strip()
        lines.append(line)
    return "\n".join(lines)
