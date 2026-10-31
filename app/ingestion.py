import csv
import io
from datetime import datetime
from pathlib import Path
from .database import get_connection, initialize_database

REQUIRED_COLUMNS = {
    "Transaction_Id", "Order_date", "Product", "Category", "Region",
    "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
}

DATE_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d")

def _parse_date(date_str: str) -> str | None:
    cleaned = (date_str or "").strip()
    if not cleaned:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            pass
    return None

def load_csv_stream(handle, db_path: Path | str | None = None) -> dict:
    """Internal helper to process a CSV DictReader stream."""
    initialize_database(db_path)
    reader = csv.DictReader(handle)
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    
    inserted = invalid = 0
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM sales_transactions")
        for row in reader:
            notes = []
            txn_id = (row.get("Transaction_Id") or "").strip()
            order_date = _parse_date(row.get("Order_date", ""))
            if not order_date:
                notes.append("invalid or missing order date")

            product = (row.get("Product") or "").strip() or None
            category = (row.get("Category") or "").strip() or None
            region = (row.get("Region") or "").strip() or None
            channel = (row.get("Sales_channel") or "").strip() or None
            status = (row.get("Status") or "").strip().title() or None

            try:
                quantity = int(row.get("Quantity", ""))
            except (TypeError, ValueError):
                quantity = None
                notes.append("missing or invalid quantity")

            try:
                unit_price = float(row.get("Unit_price", ""))
            except (TypeError, ValueError):
                unit_price = None
                notes.append("missing or invalid unit price")

            try:
                discount = float(row.get("Discount_amount", "") or 0)
            except (TypeError, ValueError):
                discount = None
                notes.append("invalid discount amount")

            if not txn_id:
                notes.append("missing transaction id")
            if not product or not category or not region or not channel:
                notes.append("missing descriptive field")
            if quantity is not None and quantity <= 0:
                notes.append("quantity must be greater than zero")
            if unit_price is not None and unit_price < 0:
                notes.append("unit price cannot be negative")
            if discount is not None and discount < 0:
                notes.append("discount cannot be negative")

            gross = quantity * unit_price if quantity is not None and unit_price is not None else None
            if gross is not None and discount is not None and discount > gross:
                notes.append("discount exceeds gross amount")
            if status != "Completed":
                notes.append("non-completed transaction excluded from revenue")

            eligible = not notes
            revenue = round(gross - discount, 2) if eligible else None

            try:
                conn.execute("""INSERT INTO sales_transactions
                (transaction_id, order_date, product, category, region, sales_channel,
                 quantity, unit_price, discount_amount, status, revenue, is_eligible, validation_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn_id, order_date, product, category, region, channel, quantity,
                 unit_price, discount, status, revenue, int(eligible), "; ".join(notes) or None))
                inserted += 1
                if not eligible:
                    invalid += 1
            except Exception as exc:
                raise ValueError(f"Could not import transaction {txn_id or '<unknown>'}: {exc}") from exc
        conn.commit()
    return {"rows_loaded": inserted, "excluded_rows": invalid, "eligible_rows": inserted - invalid}

def load_csv(csv_path: Path | str, db_path: Path | str | None = None) -> dict:
    """Load source rows from a file path."""
    csv_path = Path(csv_path)
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        return load_csv_stream(handle, db_path)

def load_csv_text(csv_text: str, db_path: Path | str | None = None) -> dict:
    """Load source rows from raw string content."""
    stream = io.StringIO(csv_text)
    return load_csv_stream(stream, db_path)
