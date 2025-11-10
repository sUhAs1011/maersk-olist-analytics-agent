import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.sql_agent import ask

tests = [
    "Top 5 product categories by revenue",
    "Average delivery delay in days by state",
    "How many orders per month in 2018?",
    "Share of payment types by count",
]

for q in tests:
    print("="*80)
    print("Q:", q)
    df, sql, err = ask(q)
    print("\nSQL:\n", sql)
    if err:
        print("\nERR:", err)
    else:
        print("\nRESULT (head):")
        print(df.head())
