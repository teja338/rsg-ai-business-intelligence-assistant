import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_transactions (
    transaction_id TEXT PRIMARY KEY,
    order_date TEXT,
    product TEXT,
    category TEXT,
    region TEXT,
    sales_channel TEXT,
    quantity INTEGER,
    unit_price REAL,
    discount_amount REAL,
    status TEXT,
    revenue REAL,
    is_eligible INTEGER NOT NULL DEFAULT 0,
    validation_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_transactions(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_transactions(product);
CREATE INDEX IF NOT EXISTS idx_sales_region ON sales_transactions(region);
"""

@contextmanager
def get_connection(db_path: Path | str | None = None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def initialize_database(db_path: Path | str | None = None):
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
