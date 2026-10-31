import io
import pytest
from fastapi.testclient import TestClient
from app import database
from app.ingestion import load_csv
from app.main import app
from app import analytics
from app.interpreter import deterministic_interpret, validate_sql_query

@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test_sales.db"
    monkeypatch.setattr(database, "DB_PATH", db)
    load_csv(database.Path(__file__).resolve().parents[1] / "data" / "sales_data.csv", db)
    with TestClient(app) as test_client:
        yield test_client

# 1. Data Ingestion & Quality Tests
def test_csv_import_preserves_all_rows_and_excludes_three(client):
    summary = analytics.dataset_summary()
    assert summary["total_rows"] == 51
    assert summary["eligible_rows"] == 48
    assert summary["excluded_rows"] == 3

# 2. Assessment Question 1: Total Revenue
def test_total_revenue_returns_structured_result(client):
    response = client.post('/api/ask', json={"question": "What is the total revenue?"})
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["intent"] == "total_revenue"
    assert body["data"]["transactions"] == 48
    assert body["data"]["total_revenue"] == 1439200.0

# 3. Assessment Question 2: Highest Revenue Product
def test_top_product_question(client):
    response = client.post('/api/ask', json={"question": "Which product generated the highest revenue?"})
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["intent"] == "top_product"
    assert body["data"]["product"] == "Monitor"
    assert body["data"]["revenue"] == 473000.0

# 4. Assessment Question 3: Monthly Revenue Trend
def test_monthly_trend_returns_months(client):
    response = client.post('/api/ask', json={"question": "What is the monthly revenue trend?"})
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert len(body["data"]) == 6
    assert body["data"][0]["month"] == "2026-01"
    assert body["data"][-1]["month"] == "2026-06"

def test_monthly_trend_synonyms(client):
    response = client.post('/api/ask', json={"question": "Show revenue by month"})
    assert response.status_code == 200
    assert response.json()["intent"] == "monthly_trend"

# 5. Assessment Question 4: Highest Sales Region
def test_region_question(client):
    response = client.post('/api/ask', json={"question": "Which region generated the highest sales?"})
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["intent"] == "top_region"
    assert body["data"]["region"] == "South"
    assert body["data"]["revenue"] == 411200.0

# 6. Assessment Question 5: Revenue Change Between Months
def test_month_comparison_specific_months(client):
    response = client.post('/api/ask', json={"question": "How did revenue change between January and February 2026?"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["from_month"] == "2026-01"
    assert data["to_month"] == "2026-02"
    assert data["from_revenue"] == 210250.0
    assert data["to_revenue"] == 234600.0
    assert data["change"] == 24350.0
    assert data["percentage_change"] == 11.58

def test_verbatim_question_five_between_two_months(client):
    """Tests the exact phrasing from the assessment specification: 'How did revenue change between two months?'"""
    response = client.post('/api/ask', json={"question": "How did revenue change between two months?"})
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["intent"] == "compare_months"
    assert body["data"]["from_month"] == "2026-01"
    assert body["data"]["to_month"] == "2026-02"

def test_month_abbreviations_comparison(client):
    response = client.post('/api/ask', json={"question": "Revenue change between Jan and Mar 2026"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["from_month"] == "2026-01"
    assert data["to_month"] == "2026-03"

# 7. Unsupported, Edge Cases & Error Handling
def test_unsupported_question_does_not_execute_sql(client):
    response = client.post('/api/ask', json={"question": "Tell me a joke about cats"})
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert "couldn't map that question" in body["answer"]

def test_short_question_is_rejected(client):
    response = client.post('/api/ask', json={"question": "hi"})
    assert response.status_code == 422

def test_sql_injection_attempt_is_treated_as_unsupported(client):
    response = client.post('/api/ask', json={"question": "DROP TABLE sales_transactions; --"})
    assert response.status_code == 200
    assert response.json()["supported"] is False

# 8. Query Safety Validator Tests
def test_validate_sql_query_guardrails():
    is_valid, _ = validate_sql_query("SELECT * FROM sales_transactions WHERE is_eligible=1")
    assert is_valid is True

    is_valid, _ = validate_sql_query("WITH cte AS (SELECT product FROM sales_transactions) SELECT * FROM cte")
    assert is_valid is True

    is_valid, reason = validate_sql_query("DROP TABLE sales_transactions")
    assert is_valid is False
    assert "Only SELECT/read-only queries are permitted" in reason

    is_valid, reason = validate_sql_query("DELETE FROM sales_transactions WHERE region='North'")
    assert is_valid is False

    is_valid, reason = validate_sql_query("UPDATE sales_transactions SET revenue=0")
    assert is_valid is False

    is_valid, reason = validate_sql_query("SELECT 1; DROP TABLE sales_transactions")
    assert is_valid is False
    assert "Multi-statement queries are forbidden" in reason

# 9. Extended Analytics Features
def test_channel_breakdown_question(client):
    response = client.post('/api/ask', json={"question": "Which sales channel generated the highest revenue?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "channel_breakdown"
    assert len(body["data"]) == 2
    assert body["data"][0]["sales_channel"] == "Online"
    assert body["data"][0]["revenue"] == 746750.0

def test_category_breakdown_question(client):
    response = client.post('/api/ask', json={"question": "What is the revenue breakdown by category?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "category_breakdown"
    assert len(body["data"]) == 3
    assert body["data"][0]["category"] == "Accessories"

def test_product_breakdown_question(client):
    response = client.post('/api/ask', json={"question": "Show revenue for all products"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "product_breakdown"
    assert len(body["data"]) == 7

def test_region_breakdown_question(client):
    response = client.post('/api/ask', json={"question": "Show sales by all regions"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "region_breakdown"
    assert len(body["data"]) == 4

def test_filtered_revenue_north_region(client):
    response = client.post('/api/ask', json={"question": "What is the revenue in North region?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "filtered_revenue"
    assert body["data"]["value"] == "North"
    assert body["data"]["total_revenue"] == 384450.0

def test_audit_log_question(client):
    response = client.post('/api/ask', json={"question": "Why were records excluded?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "audit_log"
    assert len(body["data"]) == 3
    txns = {r["transaction_id"] for r in body["data"]}
    assert txns == {"TXN0033", "TXN0034", "TXN0051"}

# 10. Health, Dedicated APIs & File Upload
def test_health_check_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_api_reload_endpoint(client):
    response = client.post('/api/reload')
    assert response.status_code == 200
    data = response.json()
    assert data["rows_loaded"] == 51
    assert data["eligible_rows"] == 48
    assert data["excluded_rows"] == 3

def test_api_channels_and_categories_endpoints(client):
    ch_res = client.get('/api/channels')
    assert ch_res.status_code == 200
    assert len(ch_res.json()["data"]) == 2

    cat_res = client.get('/api/categories')
    assert cat_res.status_code == 200
    assert len(cat_res.json()["data"]) == 3

    aud_res = client.get('/api/audit')
    assert aud_res.status_code == 200
    assert len(aud_res.json()["data"]) == 3

def test_upload_csv_endpoint(client):
    csv_sample = (
        "Transaction_Id,Order_date,Product,Category,Region,Sales_channel,Quantity,Unit_price,Discount_amount,Status\n"
        "TXN9001,01-01-2026,Laptop Stand,Accessories,North,Online,10,1000,0,Completed\n"
        "TXN9002,02-01-2026,Monitor,Electronics,South,Retail,5,5000,100,Completed\n"
    )
    files = {"file": ("test_sales.csv", io.BytesIO(csv_sample.encode("utf-8")), "text/csv")}
    response = client.post('/api/upload', files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["rows_loaded"] == 2
    assert data["eligible_rows"] == 2
    assert data["excluded_rows"] == 0

def test_upload_invalid_csv_rejected(client):
    invalid_csv = "Transaction_Id,Wrong_Header\nTXN1,Val\n"
    files = {"file": ("bad.csv", io.BytesIO(invalid_csv.encode("utf-8")), "text/csv")}
    response = client.post('/api/upload', files=files)
    assert response.status_code == 422
