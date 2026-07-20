"""
Flags when a query result looks inconsistent with historical patterns.

Approach: pull the same metric (revenue) for every other month in the
dataset, compute mean + population stddev as a baseline, then z-score the
month being asked about against that baseline. This is a simple, fully
explainable statistical method - appropriate for a small demo dataset,
and easy to swap for something fancier (seasonal decomposition, STL,
Prophet) without touching the rest of the pipeline.

Threshold: |z| > 2.0 is flagged as "unusual" (roughly the top/bottom ~5%
under a normal approximation). |z| > 3.0 is flagged as "highly unusual".
"""
import sqlite3
import statistics


def _monthly_revenue_series(conn: sqlite3.Connection, category=None):
    cat_filter = "AND p.category = ?" if category else ""
    params = [category] if category else []
    sql = f"""
        SELECT strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.status = 'completed' {cat_filter}
        GROUP BY month
        ORDER BY month;
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()  # list of (month, revenue)


def check_revenue_anomaly(conn: sqlite3.Connection, year: int, month: int, category=None):
    """
    Returns a dict: {
        checked: bool, target_month, target_value, baseline_mean, baseline_stddev,
        z_score, verdict: "normal" | "unusual" | "highly_unusual" | "no_baseline",
        message: str
    }
    """
    if year is None or month is None:
        return {"checked": False, "message": "No specific month/year in this question - skipping anomaly check."}

    series = _monthly_revenue_series(conn, category)
    target_key = f"{year:04d}-{month:02d}"
    target_value = None
    history_values = []
    for m, rev in series:
        if m == target_key:
            target_value = rev or 0.0
        else:
            history_values.append(rev or 0.0)

    if target_value is None:
        return {"checked": False, "message": f"No order data found for {target_key} - nothing to compare."}

    if len(history_values) < 3:
        return {
            "checked": True, "target_month": target_key, "target_value": target_value,
            "verdict": "no_baseline",
            "message": f"Only {len(history_values)} other month(s) of history available - too little to judge normal vs. unusual.",
        }

    mean = statistics.mean(history_values)
    stdev = statistics.pstdev(history_values) or 1e-9  # avoid div by zero
    z = (target_value - mean) / stdev

    if abs(z) > 3.0:
        verdict = "highly_unusual"
    elif abs(z) > 2.0:
        verdict = "unusual"
    else:
        verdict = "normal"

    direction = "higher" if z > 0 else "lower"
    scope = f" for {category}" if category else ""
    message = (
        f"{target_key}{scope}: ${target_value:,.2f} vs. historical average "
        f"${mean:,.2f} (+/- ${stdev:,.2f}) across {len(history_values)} other months "
        f"-> z-score {z:+.2f} ({direction} than typical)."
    )
    if verdict == "normal":
        message += " This is within the normal range."
    elif verdict == "unusual":
        message += " [FLAG] This is unusual - worth a second look before trusting the number at face value."
    else:
        message += " [FLAG] This is highly unusual - likely a data issue, a real one-off event, or a pipeline bug. Investigate before reporting this number."

    return {
        "checked": True,
        "target_month": target_key,
        "target_value": target_value,
        "baseline_mean": mean,
        "baseline_stddev": stdev,
        "z_score": z,
        "verdict": verdict,
        "message": message,
    }
