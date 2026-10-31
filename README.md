# RSG Mini AI Business Intelligence Assistant

A lightweight, robust full-stack application that enables business users to ask questions about sales data using natural language and receive verified, deterministic answers backed by SQLite database queries.

Built with **FastAPI + SQLite + HTML5 / CSS3 / JavaScript (Chart.js)**. 

---

## Deliverables Index

1. **Source Code & Git Repository:** Initialized and tracked locally on branch `main`.
2. **Setup and Execution Instructions:** See [Section 1 & 2](#1-setup) below.
3. **Architecture Diagram & Technical Design:** See [`docs/architecture.md`](docs/architecture.md).
4. **Automated Test Suite:** 15 test cases in [`tests/test_assistant.py`](tests/test_assistant.py) (run with `pytest -v`).
5. **AI Development Notes:** See [`AI_DEVELOPMENT_NOTES.md`](AI_DEVELOPMENT_NOTES.md) (and [Section 10](#10-ai-assisted-development-disclosure)).
6. **Technical Interview Preparation Guide:** See [`docs/interview_preparation_guide.md`](docs/interview_preparation_guide.md) (covering Agentic AI, GenAI, Vectorless RAG, LangChain, Google ADK, and Dify).

---

## Key Features

- **Transparent Data Ingestion:** Imports all 51 rows from `data/sales_data.csv`. Does not silently drop invalid rows; stores them with `is_eligible = 0` and explicit `validation_note` (48 eligible, 3 excluded).
- **Supports All 5 Assessment Questions:**
  1. *What is the total revenue?* $\rightarrow$ ₹1,439,200.00 across 48 transactions.
  2. *Which product generated the highest revenue?* $\rightarrow$ Monitor (₹473,000.00).
  3. *What is the monthly revenue trend?* $\rightarrow$ Monthly aggregation for Jan–Jun 2026.
  4. *Which region generated the highest sales?* $\rightarrow$ South (₹411,200.00).
  5. *How did revenue change between two months?* $\rightarrow$ Supports verbatim question, specific months, and 3-letter abbreviations.
- **Vectorless RAG / Intent-Based Execution:** Uses LLM or rule-based fallback strictly for intent classification and parameter extraction. Executes allowlisted, parameterized SQL; never runs arbitrary or model-generated SQL.
- **SQL Injection & Guardrails:** Defense-in-depth with AST-style SQL query validation (`validate_sql_query`) and upfront keyword blocklist.
- **Interactive UI Dashboard:** Metrics cards, suggestion chips, natural language answer card, supporting data tables, and an interactive Chart.js revenue trend chart.

---

## 1. Setup

Python 3.10+ is required.

```bash
# Clone or navigate to the repository directory
cd rsg_ai_bi_assistant

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Running the Application

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload
```

- **Web Dashboard:** Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
- **Interactive OpenAPI / Swagger Docs:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

> The SQLite database is created automatically at `data/sales.db` on initial startup. To re-import the CSV at any time, click **Reload source CSV** in the UI or call `POST /api/reload`.

---

## 3. Optional LLM Integration

The application operates seamlessly **out of the box without any external API key** using its robust deterministic rule-based interpreter.

To enable optional LLM-assisted zero-shot classification (Groq, OpenAI, or local Ollama), configure environment variables:

```bash
# Using Groq / OpenAI:
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.groq.com/openai/v1"
export LLM_MODEL="llama-3.3-70b-versatile"

# Or using local Ollama:
# export LLM_API_KEY="ollama"
# export LLM_BASE_URL="http://localhost:11434/v1"
# export LLM_MODEL="codegemma:2b"

uvicorn app.main:app --reload
```

---

## 4. Supported Questions & Phrasings

| Assessment Question | Natural Phrasings Supported | Deterministic Calculation |
| :--- | :--- | :--- |
| **1. Total revenue** | *"What is the total revenue?"*, *"Total sales"*, *"Overall revenue"* | `SELECT SUM(revenue), COUNT(*) ... WHERE is_eligible=1` |
| **2. Highest revenue product** | *"Which product generated the highest revenue?"*, *"Best selling product"* | `SELECT product, SUM(revenue) ... GROUP BY product ORDER BY revenue DESC LIMIT 1` |
| **3. Monthly revenue trend** | *"What is the monthly revenue trend?"*, *"Revenue by month"*, *"Monthly sales"* | `SELECT strftime('%Y-%m', order_date), SUM(revenue) ... GROUP BY month` |
| **4. Highest sales region** | *"Which region generated the highest sales?"*, *"Top performing region"* | `SELECT region, SUM(revenue) ... GROUP BY region ORDER BY revenue DESC LIMIT 1` |
| **5. Month comparison** | *"How did revenue change between two months?"*, *"Compare Jan and Feb 2026"* | Parameterized comparison between two ISO months with $\Delta$ and % change |

---

## 5. API Reference

### `POST /api/ask`
Accepts a natural language question and returns a structured response.

**Request:**
```json
{
  "question": "Which product generated the highest revenue?"
}
```

**Response (200 OK):**
```json
{
  "supported": true,
  "intent": "top_product",
  "answer": "Monitor generated the highest revenue: ₹473,000.00.",
  "data": {
    "product": "Monitor",
    "revenue": 473000.0,
    "units_sold": 50,
    "transactions": 9
  },
  "interpretation_method": "rules",
  "calculation": "Deterministic, read-only SQLite query"
}
```

### Other Endpoints
- `GET /api/summary`: Returns `{ total_rows: 51, eligible_rows: 48, excluded_rows: 3 }`.
- `GET /api/health`: Health status check (`{ "status": "ok" }`).
- `POST /api/reload`: Re-reads `sales_data.csv` and re-seeds SQLite.

---

## 6. Data Quality & Business Rules

All 51 rows from `data/sales_data.csv` are preserved in the SQLite table `sales_transactions` for complete data lineage.

**Eligibility Policy (`is_eligible = 1`):**
1. Transaction status must be `Completed`.
2. Quantity must be greater than zero.
3. Unit price must be present and non-negative.
4. Discount amount must be non-negative and $\le (\text{quantity} \times \text{unit\_price})$.

**Excluded Transactions (3 rows):**
- `TXN0033`: Excluded because status is `Returned`.
- `TXN0034`: Excluded because quantity is `0`.
- `TXN0051`: Excluded because `Unit_price` is missing.

Net Revenue Formula:
$$\text{Net Revenue} = (\text{Quantity} \times \text{Unit Price}) - \text{Discount Amount}$$

---

## 7. Automated Tests

The test suite includes **15 automated tests** covering valid questions, verbatim phrasing, abbreviations, invalid questions, SQL injection attempts, query safety guardrails, and API endpoints.

Run tests from the project root:

```bash
pytest -v
```

Output:
```text
tests/test_assistant.py::test_csv_import_preserves_all_rows_and_excludes_three PASSED
tests/test_assistant.py::test_total_revenue_returns_structured_result PASSED
tests/test_assistant.py::test_top_product_question PASSED
tests/test_assistant.py::test_monthly_trend_returns_months PASSED
tests/test_assistant.py::test_monthly_trend_synonyms PASSED
tests/test_assistant.py::test_region_question PASSED
tests/test_assistant.py::test_month_comparison_specific_months PASSED
tests/test_assistant.py::test_verbatim_question_five_between_two_months PASSED
tests/test_assistant.py::test_month_abbreviations_comparison PASSED
tests/test_assistant.py::test_unsupported_question_does_not_execute_sql PASSED
tests/test_assistant.py::test_short_question_is_rejected PASSED
tests/test_assistant.py::test_sql_injection_attempt_is_treated_as_unsupported PASSED
tests/test_assistant.py::test_validate_sql_query_guardrails PASSED
tests/test_assistant.py::test_health_check_endpoint PASSED
tests/test_assistant.py::test_api_reload_endpoint PASSED

======================== 15 passed in 1.89s =========================
```

---

## 8. Architecture & Interview Resources

- Detailed Architecture Document: [`docs/architecture.md`](docs/architecture.md)
- Complete AI Development Notes: [`AI_DEVELOPMENT_NOTES.md`](AI_DEVELOPMENT_NOTES.md)
- Technical Interview Preparation Guide: [`docs/interview_preparation_guide.md`](docs/interview_preparation_guide.md)

---

## 9. AI-Assisted Development Disclosure

- **AI tools used:** Antigravity (Google DeepMind agentic coding assistant with Gemini 3.8 Flash/Pro), Claude 3.7 Sonnet / Cursor, and local Ollama (`codegemma:2b`).
- **How AI was used:** Architectural trade-off analysis (Vectorless RAG vs Text-to-SQL), ETL cleansing logic formulation, regex month extractor authoring, edge case test generation, and Chart.js UI integration.
- **Problems encountered:** 
  1. Verbatim Question 5 (*"How did revenue change between two months?"*) fell through to `total_revenue` because no specific month names were in the prompt.
  2. SQL injection string `DROP TABLE sales_transactions; --` contained the substring `sales`, causing naive keyword matching to classify it as a revenue question.
  3. Running `pytest -q` failed with `ModuleNotFoundError` without `pytest.ini`.
  4. Short month abbreviations (*Jan*, *Feb*) were initially unrecognized.
- **Debugging:** Added fallback for month comparisons without explicit months; hardened keyword matching with regex word boundaries `\b` and an upfront DDL blocklist; configured `pytest.ini` with `pythonpath = .`; expanded month dictionary with abbreviations.
- **What I would improve with another day:** Conversational multi-turn memory, dynamic multi-dimensional slice-and-dice queries, drag-and-drop CSV upload with LLM schema mapping, and interactive visual drill-down.
