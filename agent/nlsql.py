"""
Natural language -> SQL, template-based, zero paid API required.

This module recognizes a fixed set of business-question *shapes* (revenue
by category/month, top-N products, order counts, average order value,
cancellation rate, top customers) via keyword + regex entity extraction,
then fills a parametrized SQL template. It is intentionally NOT a general
NL2SQL model - it is a fast, free, fully-offline layer that covers the
question patterns this demo's dataset supports well.

--- Extensibility: plugging in a real local LLM ---
If you want open-ended NL2SQL instead of template matching, the natural
drop-in point is `generate_sql()` below: replace the `_match_template(...)`
call with a call to a local model server, e.g. Ollama running a small
open-weight model (`ollama run sqlcoder` or `ollama run llama3.1`):

    import requests
    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": "sqlcoder",
        "prompt": build_schema_aware_prompt(question, schema_ddl),
        "stream": False,
    })
    sql = resp.json()["response"]

That keeps the whole pipeline free/local - Ollama has no cost and no API
key. We didn't wire it in by default so the hackathon demo has zero
external dependencies to install/run, but the seam is here.
"""
import re

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

CATEGORIES = ["Electronics", "Home & Kitchen", "Sports", "Books", "Toys"]
REGIONS = ["Northeast", "Midwest", "South", "West"]


class ParsedQuestion:
    def __init__(self, template, params, sql, explanation):
        self.template = template
        self.params = params
        self.sql = sql
        self.explanation = explanation


def _extract_month_year(text):
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else None
    month = None
    for name, num in MONTHS.items():
        if re.search(rf"\b{name}\b", text):
            month = num
            break
    return month, year


def _extract_category(text):
    for cat in CATEGORIES:
        if cat.lower() in text.lower() or cat.split()[0].lower() in text.lower():
            return cat
    return None


def _extract_region(text):
    for r in REGIONS:
        if r.lower() in text.lower():
            return r
    return None


def _extract_top_n(text, default=5):
    m = re.search(r"\btop\s+(\d+)\b", text)
    if m:
        return int(m.group(1))
    return default


def generate_sql(question: str) -> ParsedQuestion:
    """Main entrypoint: NL question in, ParsedQuestion (with .sql) out."""
    q = question.lower().strip()
    month, year = _extract_month_year(q)
    category = _extract_category(q)
    region = _extract_region(q)

    date_filter_parts = []
    if year:
        date_filter_parts.append(f"strftime('%Y', o.order_date) = '{year}'")
    if month:
        date_filter_parts.append(f"strftime('%m', o.order_date) = '{month:02d}'")
    date_filter = (" AND " + " AND ".join(date_filter_parts)) if date_filter_parts else ""

    # 1a. Top N products / customers - must be checked before the generic
    # "revenue" keyword match below, since these questions also say "revenue".
    if "top" in q and "product" in q:
        n = _extract_top_n(q)
        cat_filter = f" AND p.category = '{category}'" if category else ""
        sql = f"""
SELECT p.name, p.category,
       SUM(oi.quantity * oi.unit_price) AS total_revenue,
       SUM(oi.quantity) AS units_sold
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'{date_filter}{cat_filter}
GROUP BY p.product_id
ORDER BY total_revenue DESC
LIMIT {n};
""".strip()
        return ParsedQuestion("top_products", {"n": n, "category": category}, sql,
                               f"Top {n} products by revenue" + (f" in {category}" if category else ""))

    if "top" in q and "customer" in q:
        n = _extract_top_n(q)
        sql = f"""
SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer_name, c.region,
       SUM(oi.quantity * oi.unit_price) AS total_spent
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.status = 'completed'{date_filter}
GROUP BY c.customer_id
ORDER BY total_spent DESC
LIMIT {n};
""".strip()
        return ParsedQuestion("top_customers", {"n": n}, sql, f"Top {n} customers by total spend")

    # 1. Revenue broken down by category (trend / anomaly-check friendly) - must
    # be checked before the generic "revenue" match below, since this question
    # shape also contains the word "revenue".
    if "by category" in q or "each category" in q or "per category" in q:
        sql = f"""
SELECT p.category,
       strftime('%Y-%m', o.order_date) AS month,
       COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'{date_filter}
GROUP BY p.category, month
ORDER BY month, p.category;
""".strip()
        return ParsedQuestion("revenue_by_category", {"month": month, "year": year}, sql,
                               "Revenue and order count per category per month")

    # 2. Revenue questions (optionally scoped by category/month/year)
    if "revenue" in q or "sales total" in q or ("how much" in q and "made" in q):
        cat_filter = f" AND p.category = '{category}'" if category else ""
        sql = f"""
SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'{date_filter}{cat_filter};
""".strip()
        scope = []
        if category:
            scope.append(category)
        if month:
            scope.append([k for k, v in MONTHS.items() if v == month][0].capitalize())
        if year:
            scope.append(str(year))
        explanation = "Total revenue" + (f" for {', '.join(scope)}" if scope else " (all time)")
        return ParsedQuestion("revenue", {"category": category, "month": month, "year": year}, sql, explanation)

    # 5. Order counts (optionally by region/month/status)
    if "how many orders" in q or "order count" in q or "number of orders" in q:
        status_filter = ""
        if "cancel" in q:
            status_filter = " AND o.status = 'cancelled'"
        elif "return" in q:
            status_filter = " AND o.status = 'returned'"
        region_filter = ""
        if region:
            region_filter = f" AND c.region = '{region}'"
        sql = f"""
SELECT COUNT(*) AS order_count
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE 1=1{status_filter}{region_filter}{date_filter};
""".strip()
        scope = []
        if region:
            scope.append(region)
        if month:
            scope.append([k for k, v in MONTHS.items() if v == month][0].capitalize())
        if year:
            scope.append(str(year))
        explanation = "Order count" + (f" for {', '.join(scope)}" if scope else "")
        return ParsedQuestion("order_count", {"region": region, "month": month, "year": year}, sql, explanation)

    # 6. Average order value
    if "average order value" in q or "aov" in q:
        sql = f"""
SELECT AVG(order_total) AS average_order_value FROM (
    SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS order_total
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    WHERE o.status = 'completed'{date_filter}
    GROUP BY o.order_id
);
""".strip()
        return ParsedQuestion("avg_order_value", {"month": month, "year": year}, sql, "Average order value")

    # 7. Cancellation / return rate
    if "cancellation rate" in q or "return rate" in q or "cancel rate" in q:
        sql = """
SELECT
    ROUND(100.0 * SUM(CASE WHEN status IN ('cancelled', 'returned') THEN 1 ELSE 0 END) / COUNT(*), 2) AS problem_rate_pct,
    COUNT(*) AS total_orders
FROM orders;
""".strip()
        return ParsedQuestion("cancel_rate", {}, sql, "Cancellation + return rate across all orders")

    # Fallback: unrecognized question shape
    raise ValueError(
        "Couldn't match this question to a known template. Supported shapes: "
        "revenue [by category/month], revenue by category, top N products, "
        "top N customers, order counts [by region/status/month], average order value, "
        "cancellation/return rate. See agent/nlsql.py docstring for extending with a local LLM."
    )
