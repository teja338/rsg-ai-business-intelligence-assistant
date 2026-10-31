# Technical Interview Preparation Guide
### AI-Assisted Development Challenge: Mini AI BI Assistant

This guide prepares you for technical and architectural interview questions based on the challenge requirements and key evaluation topics:
**Agentic AI, Generative AI, RAG, Vectorless RAG, and Agentic Frameworks (LangChain, Google ADK, Dify).**

---

## 1. Generative AI vs. Agentic AI

### Core Differences

| Dimension | Generative AI (GenAI) | Agentic AI |
| :--- | :--- | :--- |
| **Operational Model** | Single-turn, prompt-and-response (stateless, reactive). | Iterative, goal-driven execution loop (stateful, proactive). |
| **Environment Interaction** | Cannot interact with external tools or databases directly. | Uses tools, APIs, code execution, databases, and web browsers. |
| **Error Handling** | If output is wrong, user must re-prompt manually. | Self-reflection: Inspects tool outputs, detects errors, and re-plans. |
| **Determinism** | Probabilistic token generation; prone to arithmetic hallucinations. | Delegates computation to deterministic tools (e.g. SQLite, calculator). |

### The 4 Agentic AI Patterns (Andrew Ng's Framework)
1. **Tool Use:** The LLM identifies when external computation/data is needed, chooses an appropriate tool, formats arguments, and uses the output. *(In our app: The assistant maps the user question to an allowlisted database query tool).*
2. **Planning:** Decomposing complex user goals into intermediate tasks (e.g., plan steps, identify sub-queries, execute in sequence).
3. **Reflection:** Critiquing intermediate results (e.g. validating query syntax or verifying row counts before presenting to the user).
4. **Multi-Agent Collaboration:** Dividing work among specialized agents (e.g., Query Planner Agent, Data Validation Agent, Report Presenter Agent).

---

## 2. RAG vs. Vectorless RAG

### What is Vector RAG?
Traditional RAG chunks text documents, computes semantic vector embeddings (via models like `text-embedding-ada-002` or `all-MiniLM-L6-v2`), indexes them in a Vector Database (Chroma, Pinecone, FAISS), and retrieves top-$k$ nearest chunks using cosine similarity.
- **Where it excels:** Unstructured narrative text (documentation, policies, knowledge bases, customer support manuals).
- **Where it fails:** Structured quantitative queries. Asking *"What is the total revenue?"* in a Vector RAG system retrieves 5 arbitrary invoice chunks; the LLM then hallucinates an incomplete sum.

### What is Vectorless RAG?
Vectorless RAG retrieves information from **structured, relational, or graph data stores** without relying on semantic vector similarity. Retrieval is performed using:
- SQL / relational database queries (`SELECT SUM(revenue) FROM sales_transactions WHERE is_eligible=1`)
- Graph queries (Cypher / SPARQL)
- Metadata filtering & structured APIs

### Why Vectorless RAG is Essential for Business Intelligence
1. **Mathematical Correctness:** Financial metrics require exact summation, not probabilistic text prediction.
2. **Complete Coverage:** Vector search retrieves top-$k$ (e.g., 5 rows out of 50,000). A SQL `SUM()` computes over 100% of eligible rows.
3. **Data Freshness & Auditing:** Real-time updates without re-embedding text chunks. Transparent audit trails on excluded rows.
4. **Latency & Cost Efficiency:** Parameterized SQL executes in milliseconds without embedding API costs or vector index maintenance.

---

## 3. Agentic Frameworks: LangChain, Google ADK, Dify

### 1. LangChain / LangGraph
- **Overview:** The most popular open-source framework for building LLM applications and stateful agents.
- **Key Concepts:**
  - `LangChain Expression Language (LCEL)`: Declarative composition of chains.
  - `create_sql_agent`: Prebuilt agent with database reflection and query tools.
  - `LangGraph`: Graph-based agent orchestration with circular loops, persistent memory, and human-in-the-loop checkpoints.
- **Mapping to our Project:** Our `interpret_question` + `analytics` pipeline can be represented in LangGraph as:
  `User Question` $\rightarrow$ `Router Node` $\rightarrow$ `SQL Execution Tool Node` $\rightarrow$ `Formatter Node`.

### 2. Google ADK (Agent Development Kit / Google Generative AI SDK)
- **Overview:** Google's enterprise-grade framework for building autonomous agents natively integrated with Gemini models.
- **Key Concepts:**
  - Function Calling (`tools=[...]`): Gemini natively outputs structured function calls with type validation.
  - Schema Enforcement: Leverages OpenAPI / JSON Schema to guarantee output types.
  - Grounding: Built-in grounding with Google Search or Vertex AI Search for enterprise data stores.
- **Mapping to our Project:** In Google ADK, our predefined queries (`total_revenue`, `compare_months`) would be declared as Python functions decorated with `@tool`, passed directly to `model.generate_content(tools=[...])`.

### 3. Dify (dify.ai)
- **Overview:** An open-source, visual LLMOps platform combining visual workflow orchestration, RAG pipelines, and agent capabilities.
- **Key Concepts:**
  - Visual Orchestration: Drag-and-drop workflow canvas with nodes (LLM, Code, Knowledge Retrieval, HTTP Request).
  - Hybrid RAG: Supports both Vector RAG (for text knowledge) and Tool-based / Vectorless retrieval (via custom API plugins).
  - Observability: Built-in logging, token tracking, user feedback collection, and prompt iteration.
- **Mapping to our Project:** In Dify, we would create a **Custom Tool Provider** connecting to our FastAPI `/api/ask` and `/api/summary` endpoints, orchestrating the conversational UI in Dify's visual canvas.

---

## 4. Key Architectural Decisions & Interview Defenses

### Q1: "Why not let the LLM generate raw SQL directly (Text-to-SQL)?"
**Answer:**
> *"Allowing an LLM to generate raw SQL in an enterprise BI context introduces significant reliability and security risks:
> 1. **Security Vulnerabilities:** Prompt injection can induce destructive SQL (`DROP`, `DELETE`, `UPDATE`) or bypass permission barriers.
> 2. **Non-Deterministic Calculations:** Different prompts might generate inconsistent SQL queries (e.g. one forgetting to filter out `Returned` items or negative quantities).
> 3. **Hallucinated Schemas:** LLMs frequently invent non-existent column names or join conditions.
>
> Instead, we adopted a **Vectorless RAG / Intent Classification** pattern. The AI handles what it is best at — understanding user intent and extracting parameters (e.g. months) — while our tested, deterministic SQL queries guarantee exact, secure arithmetic."*

### Q2: "How did you handle invalid rows in the CSV without data loss?"
**Answer:**
> *"Silently discarding bad data during ETL is an anti-pattern because it conceals upstream data quality issues and prevents reconciliation. 
> In our database schema, we preserve all 51 rows from `sales_data.csv`. We added an `is_eligible` boolean flag and a `validation_note` field:
> - 48 rows are eligible completed transactions.
> - 3 rows are retained with clear audit notes: `TXN0033` (Status: Returned), `TXN0034` (Quantity: 0), and `TXN0051` (Missing Unit Price).
>
> All revenue analytics filter on `is_eligible = 1`, and the frontend metrics card explicitly informs business users of total vs. eligible transactions."*

### Q3: "What prevents SQL injection in your application?"
**Answer:**
> *"We employ multiple layers of defense:
> 1. **Intent Allowlist:** User input is never concatenated or formatted into SQL strings.
> 2. **Keyword Blocklist & Sanitization:** Destructive SQL keywords (`DROP`, `DELETE`, `UPDATE`, `;`, `--`) are intercepted upfront and rejected.
> 3. **Parameterized Queries:** All database calls utilize SQLite parameterized placeholders (`?`).
> 4. **Query Safety Validator (`validate_sql_query`):** A standalone AST-style validator verifies that only single-statement read-only `SELECT`/`WITH` queries targeting approved tables can run."*

### Q4: "How would you scale this application to 10 million transactions?"
**Answer:**
> *"For a production enterprise deployment:
> 1. **Database:** Migrate from SQLite to a columnar analytical data warehouse like **DuckDB**, **ClickHouse**, or **PostgreSQL with TimescaleDB/Citus**. Columnar storage provides 100x faster aggregation over millions of rows.
> 2. **Pre-Aggregated Materialized Views:** Precompute daily and monthly revenue rollups, so monthly trend queries read 12 rows instead of scanning 10 million.
> 3. **Caching Layer:** Place Redis in front of common queries (e.g. total revenue, top product) with a time-to-live (TTL) invalidation on CSV reloads.
> 4. **Dynamic Schema Tooling:** Use LangGraph or Google ADK with structured Tool Calling, querying database metadata catalogs dynamically."*
