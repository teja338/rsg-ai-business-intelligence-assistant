import re
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
    r = rows[0]
    return {"answer": f"{r['product']} generated the highest revenue: ₹{r['revenue']:,.2f}.", "data": r}

def monthly_trend():
    rows = _all("SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY month ORDER BY month")
    return {"answer": "Monthly net revenue trend is shown below.", "data": rows}

def top_region():
    rows = _all("SELECT region, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY region ORDER BY revenue DESC, region ASC LIMIT 1")
    if not rows:
        return {"answer": "No eligible sales data is available.", "data": {}}
    r = rows[0]
    return {"answer": f"{r['region']} generated the highest sales revenue: ₹{r['revenue']:,.2f}.", "data": r}

def compare_months(month_a: str, month_b: str):
    # Accept YYYY-MM only; validate before query.
    for month in (month_a, month_b):
        if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month):
            raise ValueError("Months must use YYYY-MM format, for example 2026-01.")
    rows = _all("SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 AND strftime('%Y-%m', order_date) IN (?, ?) GROUP BY month ORDER BY month", (month_a, month_b))
    values = {r['month']: r for r in rows}
    a = float(values.get(month_a, {}).get('revenue', 0) or 0)
    b = float(values.get(month_b, {}).get('revenue', 0) or 0)
    delta = round(b - a, 2)
    pct = round((delta / a) * 100, 2) if a else None
    direction = "increased" if delta > 0 else "decreased" if delta < 0 else "did not change"
    pct_text = f" ({abs(pct):.2f}%)" if pct is not None else " (percentage change unavailable because the first month has zero revenue)"
    return {
        "answer": f"Revenue {direction} by ₹{abs(delta):,.2f}{pct_text} from {month_a} to {month_b}.",
        "data": {"from_month": month_a, "from_revenue": a, "to_month": month_b, "to_revenue": b, "change": delta, "percentage_change": pct}
    }

def channel_breakdown():
    rows = _all("SELECT sales_channel, ROUND(SUM(revenue),2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY sales_channel ORDER BY revenue DESC")
    if not rows:
        return {"answer": "No eligible channel sales data is available.", "data": []}
    top = rows[0]
    return {
        "answer": f"{top['sales_channel']} is the leading sales channel with ₹{top['revenue']:,.2f} in revenue ({top['units_sold']} units across {top['transactions']} transactions).",
        "data": rows
    }

def category_breakdown():
    rows = _all("SELECT category, ROUND(SUM(revenue),2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY category ORDER BY revenue DESC")
    if not rows:
        return {"answer": "No eligible category sales data is available.", "data": []}
    top = rows[0]
    return {
        "answer": f"{top['category']} generated the highest category revenue: ₹{top['revenue']:,.2f} ({top['units_sold']} units sold).",
        "data": rows
    }

def product_breakdown():
    rows = _all("SELECT product, category, ROUND(SUM(revenue),2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY product ORDER BY revenue DESC")
    return {
        "answer": "Complete revenue and volume breakdown across all products is shown below.",
        "data": rows
    }

def region_breakdown():
    rows = _all("SELECT region, ROUND(SUM(revenue),2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transactions FROM sales_transactions WHERE is_eligible=1 GROUP BY region ORDER BY revenue DESC")
    return {
        "answer": "Regional sales performance across all territories is shown below.",
        "data": rows
    }

def filtered_revenue(dimension: str, value: str):
    allowed_dimensions = {"region", "category", "sales_channel", "product"}
    dim = dimension.lower().strip()
    if dim not in allowed_dimensions:
        raise ValueError(f"Unsupported filter dimension: {dimension}")
    sql = f"SELECT ROUND(COALESCE(SUM(revenue),0),2) AS total_revenue, COUNT(*) AS transactions, SUM(quantity) AS units_sold FROM sales_transactions WHERE is_eligible=1 AND LOWER({dim}) = LOWER(?)"
    row = _one(sql, (value.strip(),))
    rev = row.get("total_revenue", 0) or 0
    txns = row.get("transactions", 0) or 0
    units = row.get("units_sold", 0) or 0
    return {
        "answer": f"Total net revenue for {dim.replace('_', ' ')} '{value.title()}' is ₹{rev:,.2f} ({units} units across {txns} transactions).",
        "data": {"dimension": dim, "value": value.title(), "total_revenue": rev, "transactions": txns, "units_sold": units}
    }

def audit_log():
    rows = _all("SELECT transaction_id, order_date, product, status, quantity, unit_price, validation_note FROM sales_transactions WHERE is_eligible=0 ORDER BY transaction_id")
    return {
        "answer": f"Found {len(rows)} excluded transaction(s) requiring data quality review.",
        "data": rows
    }

def dataset_summary():
    return _one("SELECT COUNT(*) AS total_rows, SUM(is_eligible) AS eligible_rows, SUM(CASE WHEN is_eligible=0 THEN 1 ELSE 0 END) AS excluded_rows FROM sales_transactions")
