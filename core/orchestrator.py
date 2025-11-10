from __future__ import annotations
import os
from typing import Literal, Tuple, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

from .sql_agent import ask as ask_sql  # uses your working sql_agent

# Load env + configure Gemini
REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=True)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

Intent = Literal["sql_query", "explain_term", "translate"]

_INTENT_SYS = """Classify the user's message into one of:
- sql_query: They want analytics against the e-commerce database (tables like orders, items, products).
- explain_term: They asked to explain a commerce/logistics term (e.g., freight value, AOV, lead time).
- translate: They asked to translate a phrase to/from English.

Return only the label: sql_query OR explain_term OR translate.
"""

def detect_intent(message: str) -> Intent:
    prompt = f"{_INTENT_SYS}\n\nUser: {message}\nLabel:"
    text = genai.GenerativeModel(MODEL).generate_content(prompt).text.strip().lower()
    if "translate" in text: return "translate"
    if "explain" in text: return "explain_term"
    return "sql_query"

_TERMS = {
    "freight value": "Shipping fee charged for delivering items for an order; in Olist it's the `freight_value` column on order items.",
    "aov": "Average order value = total revenue / number of orders.",
    "lead time": "Time between order placement and delivery to the customer.",
    "sla": "Service Level Agreement: expected service quality/time (e.g., delivery time promise).",
}

def explain_term(term: str) -> str:
    # simple seed + LLM polish
    seed = ""
    for k,v in _TERMS.items():
        if k in term.lower():
            seed = v; break
    user_q = f"Explain briefly the term in e-commerce/logistics context: {term}"
    if seed:
        user_q += f"\n\nSeed context: {seed}"
    res = genai.GenerativeModel(MODEL).generate_content(user_q)
    return res.text.strip()

def translate_text(text: str, target_lang: str = "English") -> str:
    prompt = f"Translate to {target_lang}. Keep only translated text, no extra words:\n\n{text}"
    res = genai.GenerativeModel(MODEL).generate_content(prompt)
    return res.text.strip()

def handle_message(message: str,
                   schema_path: str | Path,
                   db_path: str | Path) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (markdown_response, extras)
    extras may include {"sql": "...", "df": pandas.DataFrame}
    """
    intent = detect_intent(message)
    if intent == "explain_term":
        ans = explain_term(message)
        return ans, {"intent":"explain_term"}
    if intent == "translate":
        # crude detection for "to <lang>"
        tgt = "English"
        lowered = message.lower()
        if "to portuguese" in lowered: tgt = "Portuguese"
        elif "to spanish" in lowered: tgt = "Spanish"
        elif "to french" in lowered: tgt = "French"
        ans = translate_text(message, target_lang=tgt)
        return ans, {"intent":"translate","target_lang":tgt}

    # default: sql_query
    df, sql, err = ask_sql(message, schema_path=schema_path, db_path=db_path, retry=True)
    if err:
        md = f"**I tried to run SQL but hit an error:**\n\n```\n{err}\n```\n\n**Generated SQL:**\n```sql\n{sql}\n```"
        return md, {"intent":"sql_query","sql":sql,"error":err,"df":None}
    else:
        # small textual summary
        md = f"**Answer based on the data:**\n\nShowing top rows below.\n\n**SQL used:**\n```sql\n{sql}\n```"
        return md, {"intent":"sql_query","sql":sql,"df":df}
