# AI-Assisted Development Notes

This document fulfills Deliverable 5 of the technical assessment, documenting the AI tools used, the engineering workflow, problems encountered, debugging steps, and future improvements.

---

## 1. AI Tools Used

- **Antigravity (Google DeepMind Agentic Assistant)** powered by **Gemini 3.8 Flash / Pro**: Used for project scaffolding, architecture trade-off evaluation, code authoring, and test generation.
- **Claude 3.7 Sonnet / ChatGPT**: Used for reviewing Vectorless RAG concepts, evaluating prompt guardrails, and validating SQL safety strategies.
- **Local Ollama (`codegemma:2b` / `llama3`) & Groq OpenAI-compatible endpoints**: Used to test optional LLM-assisted zero-shot intent classification alongside the deterministic fallback.

---

## 2. How AI Was Used During Development

1. **Architecture & Safety Trade-off Analysis:**
   - Consulted AI to evaluate **unconstrained Text-to-SQL vs. Vectorless RAG (Intent Classification + Parameterized Predefined SQL)**.
   - Text-to-SQL poses severe risks: SQL injection, non-deterministic aggregation logic, hallucinated column names, and accidental data mutation.
   - Vectorless RAG / Intent Classification was chosen: The AI extracts the user's intent and parameters, while all database execution runs through deterministic, allowlisted, parameterized SQLite queries.

2. **Data Pipeline & Cleansing Design:**
   - Used AI to inspect the 51 rows in `data/sales_data.csv` and identify data quality issues:
     - `TXN0033`: Status is `Returned` (must be excluded from net revenue).
     - `TXN0034`: Quantity is `0` (invalid transaction).
     - `TXN0051`: Missing `Unit_price` (incomplete record).
   - Designed the database schema to keep all 51 records (for full auditability) while flagging the 3 invalid rows with `is_eligible = 0` and an explicit `validation_note`.

3. **Natural Language Understanding & Parameter Extraction:**
   - Used AI to craft regex and fuzzy month extractors for standard calendar names (`January`–`December`), 3-letter abbreviations (`Jan`–`Dec`), ISO formats (`2026-01`), and edge cases (e.g., disambiguating the calendar month "May" from the modal verb "may").
   - Added support for the assessment's verbatim question: *"How did revenue change between two months?"*.

4. **Automated Testing & Security Guardrails:**
   - Generated a 15-test automated test suite covering:
     - Data ingestion and data quality counters (51 total, 48 eligible, 3 excluded).
     - All 5 assessment questions with verified mathematical accuracy.
     - Phrasing variations and synonyms (e.g., "Show revenue by month").
     - SQL injection attempts (e.g., `DROP TABLE sales_transactions; --`).
     - Query safety validation functions (`validate_sql_query`).
     - REST API health check and data reload endpoints.

5. **Frontend Dashboard:**
   - Crafted a clean, responsive single-page application using modern HTML5, CSS custom properties, and Chart.js for data visualization.

---

## 3. Problems Encountered

1. **Subtle Intent Collision on Assessment Question 5:**
   - When the user asked the exact question from the problem statement: *"How did revenue change between two months?"*, no specific month names were present.
   - The original keyword matcher checked for `len(months) >= 2`. Since this was false, it fell through to the general revenue rule and wrongly returned `total_revenue`.
2. **SQL Injection False Positive on Naive Keyword Matching:**
   - When testing malicious input like `DROP TABLE sales_transactions; --`, the naive substring check `if "sales" in q:` matched because `sales_transactions` contains the substring `sales`. As a result, the injection attempt was incorrectly routed to `total_revenue` instead of being rejected as unsupported.
3. **Pytest Module Import Failure (`ModuleNotFoundError: No module named 'app'`):**
   - Running `pytest -q` directly from the project root failed during test collection because the repository root directory was not automatically added to `sys.path`.
4. **Month Abbreviation Neglect:**
   - Real business users frequently query *"Jan and Feb"* rather than typing out *"January and February"*. The initial dictionary only had full month names, resulting in empty month parameter extraction.
5. **Data Deletion vs. Data Retention Ambiguity:**
   - In raw business data, should invalid rows be deleted during ETL or retained? Deleting rows destroys data lineage and prevents quality auditing.

---

## 4. How I Debugged and Resolved Them

1. **Resolving Question 5 Intent Ambiguity:**
   - Updated `deterministic_interpret()` to recognize comparison keywords (`compare`, `change`, `difference`, `between`) paired with `month` or `months`.
   - If specific months are supplied (e.g. `January and February 2026`), it extracts them. If the user asks generally *"between two months"*, it defaults to comparing the first two recorded consecutive months (`2026-01` and `2026-02`) with an informative response.
2. **Hardening Against Injection and Word Collisions:**
   - Implemented `_matches_phrase_or_word()` utilizing regex word boundaries (`\b`) so that `sales` only matches the standalone word `\bsales\b` and never `sales_transactions` or `wholesalers`.
   - Added an upfront security check that immediately returns `None` (unsupported) if any destructive SQL token (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `;`, `--`) is detected.
   - Authored an independent `validate_sql_query()` guardrail function to demonstrate read-only AST-style validation.
3. **Fixing Pytest Path Resolution:**
   - Added a `pytest.ini` file in the project root defining:
     ```ini
     [pytest]
     pythonpath = .
     testpaths = tests
     ```
   - Running `pytest -v` or `pytest -q` now executes cleanly without requiring manual environment variables.
4. **Supporting Short Month Abbreviations & Disambiguation:**
   - Expanded `MONTHS` dictionary with 3-letter abbreviations (`jan`, `feb`, `mar`, etc.).
   - Added a regex guard for the month `"may"` to ignore occurrences followed by verbs (e.g. `"may be"`, `"may have"`, `"may cause"`).
5. **Transparent Data Audit Model:**
   - Implemented `is_eligible` (1 or 0) and `validation_note` in SQLite. When loading `sales_data.csv`, the ingestion function populates:
     - `TXN0033`: `"non-completed transaction excluded from revenue"` (Status = Returned)
     - `TXN0034`: `"quantity must be greater than zero"` (Quantity = 0)
     - `TXN0051`: `"missing or invalid unit price"` (Unit_price = NULL)
   - The UI top metric cards explicitly display: **51 Loaded**, **48 Eligible**, and **3 Excluded**, providing full transparency to business stakeholders.

---

## 5. What I Would Improve With Another Day of Work

1. **Multi-Turn Conversational Memory & Clarifications:**
   - Implement session-based chat history so users can ask contextual follow-ups (e.g., *"What about in the North region?"* or *"Compare that with the following month"*).
2. **Dynamic Multi-Dimensional Analytics (Slice & Dice):**
   - Allow combining dimensions dynamically: *"Which product sold the most in South region through Online channel in March?"* using safe query builders or dynamic parameter binding.
3. **Interactive Visual Drill-Down in UI:**
   - Enable users to click on any bar in the Monthly Trend chart or any product row to expand and view the underlying transaction line items.
4. **Drag-and-Drop CSV Ingestion with Schema Mapping:**
   - Allow users to upload arbitrary sales CSV files from the web interface, using LLM-assisted schema mapping to map arbitrary headers (e.g., `Amt`, `Cost`, `Qty`, `Item`) to the standardized database schema.
5. **Enterprise Production Readiness:**
   - Implement user authentication (JWT/OAuth2), role-based access control (RBAC), database connection pooling (PostgreSQL/DuckDB), structured query logging, and export to Excel/PDF.
