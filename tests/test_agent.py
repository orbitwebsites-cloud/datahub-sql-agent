"""
Smoke tests for the NL-to-SQL agent, lineage explainer, and anomaly checker.
Run: python -m pytest tests/ -v   (or: python tests/test_agent.py)
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import nlsql, lineage, anomaly  # noqa: E402
from data.seed_db import build as build_db, DB_PATH  # noqa: E402


class TestNLSQL(unittest.TestCase):
    def test_revenue_question(self):
        parsed = nlsql.generate_sql("what was total revenue in electronics in may 2026")
        self.assertEqual(parsed.template, "revenue")
        self.assertEqual(parsed.params["category"], "Electronics")
        self.assertEqual(parsed.params["month"], 5)
        self.assertEqual(parsed.params["year"], 2026)
        self.assertIn("SUM(oi.quantity * oi.unit_price)", parsed.sql)

    def test_top_products_question(self):
        parsed = nlsql.generate_sql("top 3 products by revenue")
        self.assertEqual(parsed.template, "top_products")
        self.assertEqual(parsed.params["n"], 3)
        self.assertIn("LIMIT 3", parsed.sql)

    def test_revenue_by_category_question(self):
        parsed = nlsql.generate_sql("revenue by category")
        self.assertEqual(parsed.template, "revenue_by_category")

    def test_unrecognized_question_raises(self):
        with self.assertRaises(ValueError):
            nlsql.generate_sql("what is the meaning of life")


class TestLineage(unittest.TestCase):
    def test_order_items_lineage_mentions_upstreams(self):
        explanation = lineage.explain_lineage("order_items")
        self.assertIn("orders", explanation)
        self.assertIn("products", explanation)

    def test_customers_is_a_source_table(self):
        explanation = lineage.explain_lineage("customers")
        self.assertIn("no upstream dependencies", explanation)

    def test_tables_used_in_sql(self):
        sql = "SELECT * FROM order_items oi JOIN orders o ON o.order_id = oi.order_id"
        tables = lineage.tables_used_in_sql(sql)
        self.assertEqual(tables, ["order_items", "orders"])


class TestAnomaly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_db()
        cls.conn = sqlite3.connect(DB_PATH)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_anomaly_month_flagged(self):
        # seed_db.py plants a deliberate demand spike in May 2026 for Electronics
        result = anomaly.check_revenue_anomaly(self.conn, 2026, 5, category="Electronics")
        self.assertTrue(result["checked"])
        self.assertIn(result["verdict"], ("unusual", "highly_unusual"))

    def test_normal_month_not_flagged(self):
        result = anomaly.check_revenue_anomaly(self.conn, 2025, 3, category="Books")
        self.assertTrue(result["checked"])
        self.assertEqual(result["verdict"], "normal")

    def test_missing_month_reported(self):
        result = anomaly.check_revenue_anomaly(self.conn, 2099, 1)
        self.assertFalse(result["checked"])


if __name__ == "__main__":
    unittest.main()
