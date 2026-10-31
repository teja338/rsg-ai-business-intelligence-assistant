# RSG Mini AI Business Intelligence Assistant

A lightweight, robust full-stack application that enables business users to ask questions about sales data using natural language and receive verified, deterministic answers backed by SQLite database queries.

Built with **FastAPI + SQLite + HTML5 / CSS3 / JavaScript (Chart.js)**.

---

## Deliverables Index

1. **Source Code & Git Repository:** Initialized and tracked locally on branch `main`.
2. **Setup and Execution Instructions:** See Sections 1 and 2.
3. **Architecture Diagram & Technical Design:** See [`docs/architecture.md`](docs/architecture.md).
4. **Automated Test Suite:** 24 test cases in [`tests/test_assistant.py`](tests/test_assistant.py).
5. **AI Development Notes:** See [`AI_DEVELOPMENT_NOTES.md`](AI_DEVELOPMENT_NOTES.md).
6. **Technical Interview Preparation Guide:** See [`docs/interview_preparation_guide.md`](docs/interview_preparation_guide.md).

---
## 🎥 Project Demonstration

Watch the complete demonstration of the RSG Mini AI Business Intelligence Assistant.

**[▶ Watch Project Demo Video](https://drive.google.com/file/d/1JoB4mHv5MB3WKazAv7YNb81vujNnyj8D/view?usp=drive_link)**

The demonstration covers:

- Application dashboard and interface.
- Natural-language business questions.
- AI-powered question interpretation.
- Database-backed analytics and verified results.
- Monthly trends and revenue comparisons.
- API documentation and application workflow.

*Note: Open the video using the link above. Google Drive access is set to anyone with the link (Viewer).*
## Key Features

### 1. Transparent Data Ingestion and Audit

- Imports all 51 rows from `data/sales_data.csv`.
- Preserves invalid records instead of silently deleting them.
- Uses `is_eligible` and `validation_note` to track data quality.
- 48 eligible transactions and 3 excluded transactions.

### 2. Supports All Five Core Assessment Questions

1. **What is the total revenue?**  
   Result: ₹14,39,200.00 across 48 eligible transactions.

2. **Which product generated the highest revenue?**  
   Result: Monitor – ₹4,73,000.00.

3. **What is the monthly revenue trend?**  
   Result: Monthly revenue aggregation from January to June 2026.

4. **Which region generated the highest sales?**  
   Result: South – ₹4,11,200.00.

5. **How did revenue change between two months?**  
   Supports the original assessment question, specific month names, and three-letter month abbreviations.

### 3. Extended Business Intelligence

- **Sales Channel Breakdown:** Online (₹7,46,750) vs. Retail (₹6,92,450).
- **Product Category Performance:** Accessories (₹5,33,100), Electronics (₹4,73,000), Furniture (₹4,33,100).
- **Regional Breakdown:** Comparison across South, North, East, and West.
- **Filtered Revenue:** Filter sales by region, category, or channel.
- **Data Quality Audit:** Inspect excluded transactions and their validation notes.

### 4. Interactive Dashboard

- Interactive charts for monthly trends, categories, sales channels, and regions.
- One-click CSV export of supporting figures.
- CSV upload with validation and database reload.
- Clickable excluded-records card for audit inspection.
- Structured answers with supporting figures and SQL information.

### 5. AI-Assisted Interpretation

- Uses an LLM or deterministic rule-based fallback to interpret natural-language questions.
- Extracts analytical intent and relevant parameters.
- Executes predefined, parameterized SQL queries.
- Does not execute arbitrary LLM-generated SQL.

### 6. SQL Security and Guardrails

- Predefined analytical SQL queries.
- Parameterized inputs for user-provided values.
- Lexical SQL validation and DDL/DML keyword blocking.
- Unsupported questions are rejected rather than executed as arbitrary queries.

---

## 1. Setup

**Requirements:** Python 3.10 or later.

Clone the repository or navigate to the project directory:

```bash
cd rsg_ai_bi_assistant
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2. Running the Application

Start the FastAPI application:

```bash
uvicorn app.main:app --reload
```

Open the following URLs:

- **Web Dashboard:** http://127.0.0.1:8000
- **Interactive API Documentation:** http://127.0.0.1:8000/docs

The SQLite database is created automatically at `data/sales.db` during initial startup.

To re-import the source CSV:

- Click **Reload source CSV** in the dashboard.
- Alternatively, call `POST /api/reload`.

---

## 3. Optional LLM Integration

The application works without an external API key using its deterministic rule-based interpreter.

To enable LLM-assisted natural-language classification, configure the environment variables.

### Using Groq API

Create a `.env` file in the project root:

```env
LLM_API_KEY=your_groq_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

The `.env` file should never be committed to GitHub.

Start the application:

```bash
uvicorn app.main:app --reload
```

### Optional Local Ollama Integration

If supported by your configuration, local Ollama can be used:

```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=codegemma:2b
```

The application can fall back to deterministic interpretation when LLM configuration is unavailable.

---

## 4. Supported Questions and Analytics

| Analysis Type | Example Question | Execution Method |
|---|---|---|
| Total Revenue | What is the total revenue? | SQLite SUM aggregation |
| Top Product | Which product generated the highest revenue? | GROUP BY and ORDER BY |
| Monthly Trend | What is the monthly revenue trend? | Date-based aggregation |
| Top Region | Which region generated the highest sales? | Regional aggregation |
| Month Comparison | How did revenue change between two months? | Parameterized month comparison |
| Channel Breakdown | Which sales channel generated the highest revenue? | Channel aggregation |
| Category Breakdown | What is the revenue breakdown by category? | Category aggregation |
| Regional Breakdown | Show sales by all regions | Regional aggregation |
| Filtered Revenue | What is the revenue in North region? | Parameterized filtering |
| Data Quality Audit | Why were records excluded? | Audit query |

---

## 5. API Reference

### POST `/api/ask`

Accepts a natural-language question and returns a structured response.

**Request:**

```json
{
  "question": "Which sales channel generated the highest revenue?"
}
```

**Example response:**

```json
{
  "supported": true,
  "intent": "channel_breakdown",
  "answer": "Online is the leading sales channel with ₹746750.00 in revenue.",
  "data": [
    {
      "sales_channel": "Online",
      "revenue": 746750.0,
      "units_sold": 353,
      "transactions": 28
    },
    {
      "sales_channel": "Retail",
      "revenue": 692450.0,
      "units_sold": 280,
      "transactions": 20
    }
  ],
  "interpretation_method": "rules",
  "calculation": "Deterministic, read-only SQLite query"
}
```

### Other API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/summary` | GET | Returns transaction summary |
| `/api/channels` | GET | Returns sales channel distribution |
| `/api/categories` | GET | Returns category performance |
| `/api/audit` | GET | Returns excluded-record audit log |
| `/api/upload` | POST | Uploads and validates a CSV |
| `/api/health` | GET | Checks application health |
| `/api/reload` | POST | Reloads the source CSV into SQLite |

---

## 6. Data Quality and Business Rules

All 51 records from `data/sales_data.csv` are preserved in the SQLite table `sales_transactions`.

### Eligibility Policy

A transaction is eligible when:

1. Transaction status is `Completed`.
2. Quantity is greater than zero.
3. Unit price is present and non-negative.
4. Discount amount is non-negative and does not exceed the gross transaction amount.

### Excluded Transactions

| Transaction ID | Reason |
|---|---|
| TXN0033 | Returned transaction |
| TXN0034 | Zero quantity |
| TXN0051 | Missing unit price |

### Revenue Formula

Net Revenue = (Quantity × Unit Price) − Discount Amount

Only eligible transactions are included in business revenue calculations.

---

## 7. Automated Testing

The project contains 24 automated tests covering:

- CSV import and data validation.
- Total revenue calculation.
- Highest-revenue product.
- Monthly revenue trends.
- Regional analytics.
- Month comparison and abbreviations.
- Unsupported and invalid questions.
- SQL injection attempts and validation.
- Channel and category breakdowns.
- Product and regional breakdowns.
- Filtered revenue.
- Audit functionality.
- API health, reload, and upload endpoints.

Run the test suite:

```bash
pytest -v
```

**Verified result:**

```text
24 passed
```

One non-blocking deprecation warning was observed during testing.

---

## 8. Architecture and Interview Resources

- **Architecture Document:** [`docs/architecture.md`](docs/architecture.md)
- **AI Development Notes:** [`AI_DEVELOPMENT_NOTES.md`](AI_DEVELOPMENT_NOTES.md)
- **Technical Interview Preparation:** [`docs/interview_preparation_guide.md`](docs/interview_preparation_guide.md)

---

## 9. AI-Assisted Development Disclosure

AI-assisted development tools were used for architecture analysis, implementation guidance, debugging, test generation, and documentation.

The development process included:

- Natural-language intent classification.
- ETL and CSV validation logic.
- Regex-based month extraction.
- Edge-case test generation.
- Chart.js dashboard integration.
- Debugging API connectivity and question-classification issues.

Detailed information about tools, encountered problems, debugging approaches, and future improvements is documented in [`AI_DEVELOPMENT_NOTES.md`](AI_DEVELOPMENT_NOTES.md).

---

## 10. Known Limitations and Future Improvements

- Natural-language interpretation is limited to supported analytical intents.
- Complex multi-dimensional queries are not yet supported.
- The application uses SQLite and is designed as a lightweight assessment project.
- SQL validation uses lexical checks and predefined query execution; it is not a complete SQL parser or production-grade security boundary.
- Conversational multi-turn memory is not implemented.

Potential improvements:

1. Add conversational multi-turn question handling.
2. Support dynamic multi-dimensional business analytics.
3. Improve CSV schema detection and mapping.
4. Add more interactive visual drill-downs.
5. Strengthen database security with read-only connections.
6. Improve deployment, logging, and monitoring.

---

## Project Summary

The RSG Mini AI Business Intelligence Assistant demonstrates how natural-language AI interpretation can be combined with deterministic database analytics to provide accurate, explainable, and auditable business intelligence.

**Core principle: AI understands the question; SQL calculates the answer.**
