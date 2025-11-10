import sys, hashlib
from pathlib import Path

# Ensure root import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import streamlit as st
import pandas as pd
import plotly.io as pio
import duckdb

# Core imports
from core.sql_agent import DEFAULT_DB, DEFAULT_SCHEMA
from core.orchestrator import handle_message
from core.memory import add_insight, load_insights, clear_insights
from core.report_utils import summarize_df, insights_to_markdown, markdown_to_pdf_bytes

# Theme
pio.templates.default = "plotly_dark"

# ---------- Page config ----------
st.set_page_config(page_title="Olist InsightGPT — Agent", page_icon="🧠", layout="wide")

# ---------- Load CSS ----------
css_path = Path(__file__).with_name("styles.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ---------- Tabs ----------
tab1, tab2 = st.tabs(["💬 Chat Assistant", "📊 KPI Dashboard"])

# =====================================================================================
# ✅ TAB 1: CHAT AI AGENT
# =====================================================================================
with tab1:

    st.markdown("""
    <h1 class="app-title">Olist InsightGPT — Chat Assistant</h1>
    <p class="app-subtitle">Ask questions on Olist data • Auto SQL • Insights • Export Report</p>
    """, unsafe_allow_html=True)

    # Sidebar settings
    with st.sidebar:
        st.subheader("Settings")
        db_path = st.text_input("DuckDB path", str(DEFAULT_DB))
        schema_path = st.text_input("Schema path", str(DEFAULT_SCHEMA))
        show_sql = st.toggle("Show SQL", value=True)
        st.divider()
        if st.button("Clear chat history", use_container_width=True):
            st.session_state.pop("history", None)
            st.rerun()

        # -------- Report section --------
        st.markdown("---")
        st.subheader("Report")
        report_title = st.text_input("Report title", "Olist InsightGPT — Analysis Report")
        report_author = st.text_input("Author", "Auto-Analyst")

        ins = load_insights()
        st.metric("Saved insights", len(ins))

        if st.button("Clear saved insights", use_container_width=True, type="secondary"):
            clear_insights()
            st.success("Cleared saved insights.")
            ins = []

        if len(ins) == 0:
            st.info("Run a query & click **💾 Save insight** before exporting.")
        else:
            md_text = insights_to_markdown(ins, title=report_title, author=report_author)

            with st.expander("Preview Markdown"):
                st.markdown(md_text)

            st.download_button(
                "Download Markdown", md_text.encode("utf-8"),
                file_name="olist_report.md", mime="text/markdown",
                use_container_width=True,
            )

            pdf_bytes = markdown_to_pdf_bytes(md_text)
            st.download_button(
                "Download PDF", pdf_bytes,
                file_name="olist_report.pdf", mime="application/pdf",
                use_container_width=True,
            )

    # ---------- Chat input box ----------
    if "history" not in st.session_state:
        st.session_state["history"] = []

    prompt_placeholder = "Ask: Top revenue categories, delivery delays, repeat buyers, etc."
    q = st.chat_input(prompt_placeholder)

    if q:
        with st.spinner("Thinking…"):
            md, extras = handle_message(q, schema_path=schema_path, db_path=db_path)
        st.session_state["history"].append((q, md, extras))

    # ---------- Chat history ----------
    for user, md, extras in st.session_state["history"]:
        with st.chat_message("user"): st.write(user)
        with st.chat_message("assistant"):
            with st.container(border=True):
                st.markdown(md)

                if extras.get("intent") == "sql_query":
                    df = extras.get("df")
                    sql = extras.get("sql", "")
                    t1, t2 = st.tabs(["📈 Result", "🧾 SQL"])

                    with t1:
                        if df is not None and not df.empty:
                            df_show = df.copy()
                            for c in df_show.columns:
                                if pd.api.types.is_float_dtype(df_show[c]):
                                    df_show[c] = df_show[c].round(3)
                            st.dataframe(df_show, use_container_width=True, hide_index=True)

                            st.download_button(
                                "Download CSV",
                                df.to_csv(index=False).encode("utf-8"),
                                file_name="result.csv", mime="text/csv",
                            )
                        else:
                            st.info("No rows returned.")

                    with t2:
                        if show_sql and sql:
                            st.code(sql, language="sql")

                    try: summary = summarize_df(df, user)
                    except: summary = f"**Question:** {user} — summary generated."

                    c1, c2 = st.columns([1, 5])
                    with c1:
                        key_seed = (user + (sql or ""))[:500]
                        btn_key = "save_" + hashlib.md5(key_seed.encode()).hexdigest()
                        if st.button("💾 Save insight", key=btn_key):
                            add_insight(
                                question=user, summary=summary, sql=sql,
                                sample_rows=(0 if df is None else min(len(df), 10)),
                            )
                            st.success("Insight saved.")
                    with c2:
                        with st.popover("🔎 Preview summary"):
                            st.markdown(summary)

# =====================================================================================
# ✅ TAB 2: KPI DASHBOARD
# =====================================================================================
with tab2:
    st.markdown("""
    <h1 class="app-title">📊 Olist KPI Dashboard</h1>
    <p class="app-subtitle">Fast metrics • Trends • Filters</p>
    """, unsafe_allow_html=True)

    @st.cache_data(show_spinner=False)
    def execq(sql):
        con = duckdb.connect(str(DEFAULT_DB))
        try: return con.execute(sql).fetchdf()
        finally: con.close()

    year = st.selectbox("Year", [2016, 2017, 2018], index=2)
    state = st.text_input("Filter by State (optional)")
    where = f"AND c.customer_state='{state}'" if state else ""

    df = execq(f"""
    SELECT
      COUNT(*) AS orders,
      SUM(i.price+i.freight_value) AS revenue,
      AVG(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) AS late_rate
    FROM orders o
    JOIN items i ON i.order_id=o.order_id
    JOIN customers c ON c.customer_id=o.customer_id
    WHERE EXTRACT(YEAR FROM o.order_purchase_timestamp)={year} {where}
    """)

    col1, col2, col3 = st.columns(3)
    col1.metric("Orders", f"{int(df.orders[0]):,}")
    col2.metric("Revenue (BRL)", f"{df.revenue[0]:,.0f}")
    col3.metric("Late Deliveries", f"{df.late_rate[0]*100:,.2f}%")

    ts = execq(f"""
    SELECT date_trunc('month', o.order_purchase_timestamp) AS month,
           COUNT(*) AS orders,
           SUM(i.price+i.freight_value) AS revenue
    FROM orders o
    JOIN items i ON i.order_id=o.order_id
    JOIN customers c ON c.customer_id=o.customer_id
    WHERE EXTRACT(YEAR FROM o.order_purchase_timestamp)={year} {where}
    GROUP BY 1 ORDER BY 1;
    """)

    st.write("### Orders & Revenue Over Time")
    st.line_chart(ts.set_index("month")[["orders","revenue"]])

# Footer
st.markdown("""
<div class="footer">
  Built for A.P. Moller Maersk Assignment • DuckDB · Gemini · Streamlit • © 2025
</div>
""", unsafe_allow_html=True)
