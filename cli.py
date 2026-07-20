"""
Metadata-aware SQL agent - interactive CLI.

Pipeline per question:
  1. agent/nlsql.py      -> turn the NL question into SQL (template-based, free/local)
  2. run SQL against data/sample.db
  3. agent/lineage.py    -> explain, in plain English, where the tables in that
                            SQL come from (using the DataHub-shaped metadata catalog)
  4. agent/anomaly.py    -> if the question was scoped to a specific month, flag
                            whether the result looks statistically unusual

Run: python cli.py
Or one-shot: python cli.py "what was total revenue in electronics in may 2026"
"""
import os
import sqlite3
import sys

from agent import nlsql, lineage, anomaly

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sample.db")


def _print_header(text):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def answer_question(conn: sqlite3.Connection, question: str):
    _print_header(f"Q: {question}")

    try:
        parsed = nlsql.generate_sql(question)
    except ValueError as e:
        print(f"[nlsql] {e}")
        return

    print(f"\n[Generated SQL]  ({parsed.explanation})")
    print(parsed.sql)

    cur = conn.cursor()
    cur.execute(parsed.sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    print("\n[Result]")
    print(" | ".join(cols))
    for row in rows[:20]:
        print(" | ".join(str(v) for v in row))
    if len(rows) > 20:
        print(f"... ({len(rows) - 20} more rows)")

    tables = lineage.tables_used_in_sql(parsed.sql)
    print(f"\n[Lineage] tables involved: {', '.join(tables)}")
    print(lineage.explain_lineage_for_tables(tables))

    month = parsed.params.get("month")
    year = parsed.params.get("year")
    category = parsed.params.get("category")
    if month and year and parsed.template in ("revenue", "revenue_by_category"):
        print("\n[Anomaly check]")
        result = anomaly.check_revenue_anomaly(conn, year, month, category)
        print(result["message"])


def main():
    if not os.path.exists(DB_PATH):
        print("Sample database not found. Run `python data/seed_db.py` first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    if len(sys.argv) > 1:
        answer_question(conn, " ".join(sys.argv[1:]))
        return

    print("Metadata-aware SQL agent - type a business question, or 'quit' to exit.")
    print("Examples:")
    print("  - what was total revenue in electronics in may 2026")
    print("  - top 5 products by revenue")
    print("  - revenue by category")
    print("  - how many orders were cancelled")
    print("  - average order value")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in ("quit", "exit"):
            break
        answer_question(conn, question)

    conn.close()


if __name__ == "__main__":
    main()
