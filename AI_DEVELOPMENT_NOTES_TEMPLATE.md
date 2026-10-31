# AI-Assisted Development Notes
## RSG Mini AI Business Intelligence Assistant

### 1. AI Tools and Technologies Used

- **ChatGPT:** Used for project architecture planning, implementation guidance, debugging, code improvements, and understanding technical concepts.
- **Groq API:** Integrated the `openai/gpt-oss-120b` model to interpret natural-language business questions and identify analytical intent.
- **GNU Nano:** Used to edit project configuration and source files.
- **Python and Pytest:** Used to implement the backend and verify application functionality.

### 2. How AI Assisted Development

AI assistance was used throughout the development process:

- Designed the architecture connecting the frontend, FastAPI backend, AI interpretation layer, analytics engine, and SQLite database.
- Developed CSV ingestion and validation logic to preserve valid and invalid transaction records.
- Implemented natural-language question interpretation using deterministic rules and LLM-based classification.
- Developed database-backed analytics for revenue, products, regions, monthly trends, and month comparisons.
- Integrated the Groq API for interpreting questions that were not recognized by deterministic rules.
- Improved error handling, API responses, frontend presentation, and automated tests.
- Used AI explanations to understand implementation decisions and prepare project documentation.

### 3. Problems Encountered During Development

**Problem 1 – LLM model availability**

The initially configured `llama-3.3-70b-versatile` model returned an HTTP 404 model-not-found error.

**Problem 2 – API connectivity**

The Groq API request encountered a Cloudflare HTTP 403 error.

**Problem 3 – Natural-language classification**

Some questions were not mapped to the correct analytical intent. For example, region-based revenue questions did not initially extract the region name correctly.

**Problem 4 – Incorrect intent matching**

Some product-related questions were classified under the wrong intent because of overlapping keyword patterns.

**Problem 5 – Assessment question handling**

The application needed to support the assessment's five business questions, including comparing two months when the user did not explicitly provide month names.

### 4. Debugging and Solutions

- Replaced the unavailable model with `openai/gpt-oss-120b`.
- Added a User-Agent header to the API request to address the Cloudflare connectivity issue.
- Inspected API responses and tested the LLM interpretation function independently.
- Improved deterministic matching and word-boundary handling to reduce incorrect keyword matches.
- Added validation for extracted dimensions and filter values.
- Improved the interpretation fallback so unsupported questions do not accidentally trigger unrelated analytics.
- Tested individual analytics queries and checked their returned figures against the dashboard.
- Used Pytest to identify regressions and verify the application after changes.

**Final testing result:** 24 automated tests passed, with one non-blocking deprecation warning.

### 5. Improvements I Would Make With Another Day

1. Strengthen database security by using a read-only SQLite connection for analytics.
2. Improve natural-language interpretation for more complex questions and different ways of expressing the same request.
3. Add more tests for SQL injection attempts, missing parameters, and unusual input.
4. Improve logging, monitoring, and API error reporting.
5. Add more interactive charts and advanced business analytics.
6. Improve deployment configuration and documentation.

### 6. Key Learning

This project helped me understand that an LLM should not be trusted to perform financial calculations directly. The LLM is useful for understanding user intent, while deterministic SQL queries provide accurate and verifiable business results.

I also learned how to integrate an external LLM API, debug API connectivity issues, build database-backed APIs, and test an AI-assisted application.
