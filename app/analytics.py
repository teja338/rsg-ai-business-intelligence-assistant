from .database import get_connection

# All SQL is authored here. User text and LLM output never become executable SQL.

def _one(sql, params=()):
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else {}

def _all(sql, params=()):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def total_revenue():
    row = _one("SELECT ROUND(COALESCE(SUM(revenue),0),2) AS total_revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1")
    return {"answer": f"Total net revenue is ₹{row['total_revenue']:,.2f} across {row['transactions']} eligible completed transactions.", "data": row}

def top_product():
    rows = _all("SELECT product, ROUND(SUM(revenue),2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY product ORDER BY revenue DESC, product ASC LIMIT 1")
    if not rows:
        return {"answer": "No eligible sales data is available.", "data": {}}
    r=rows[0]
    return {"answer": f"{r['product']} generated the highest revenue: ₹{r['revenue']:,.2f}.", "data": r}

def monthly_trend():
    rows = _all("SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY month ORDER BY month")
    return {"answer": "Monthly net revenue trend is shown below.", "data": rows}

def top_region():
    rows = _all("SELECT region, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY region ORDER BY revenue DESC, region ASC LIMIT 1")
    if not rows:
        return {"answer": "No eligible sales data is available.", "data": {}}
    r=rows[0]
    return {"answer": f"{r['region']} generated the highest sales revenue: ₹{r['revenue']:,.2f}.", "data": r}

def compare_months(month_a: str, month_b: str):
    # Accept YYYY-MM only; validate before query.
    import re
    for month in (month_a, month_b):
        if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month):
            raise ValueError("Months must use YYYY-MM format, for example 2026-01.")
    rows = _all("SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 AND strftime('%Y-%m', order_date) IN (?, ?) GROUP BY month ORDER BY month", (month_a, month_b))
    values = {r['month']: r for r in rows}
    a = float(values.get(month_a, {}).get('revenue', 0) or 0)
    b = float(values.get(month_b, {}).get('revenue', 0) or 0)
    delta = round(b-a, 2)
    pct = round((delta/a)*100, 2) if a else None
    direction = "increased" if delta > 0 else "decreased" if delta < 0 else "did not change"
    pct_text = f" ({abs(pct):.2f}%)" if pct is not None else " (percentage change unavailable because the first month has zero revenue)"
    return {"answer": f"Revenue {direction} by ₹{abs(delta):,.2f}{pct_text} from {month_a} to {month_b}.", "data": {"from_month": month_a, "from_revenue": a, "to_month": month_b, "to_revenue": b, "change": delta, "percentage_change": pct}}

def dataset_summary():
    return _one("SELECT COUNT(*) AS total_rows, SUM(is_eligible) AS eligible_rows, SUM(CASE WHEN is_eligible=0 THEN 1 ELSE 0 END) AS excluded_rows FROM sales_transactions")
