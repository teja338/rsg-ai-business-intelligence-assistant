import json
import re
import urllib.request
import urllib.error
from datetime import datetime
from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

SUPPORTED = {"total_revenue", "top_product", "monthly_trend", "top_region", "compare_months"}

# Supports full names and common 3-letter abbreviations
MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

DISALLOWED_SQL_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "ATTACH", "DETACH", "REPLACE", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
}

def validate_sql_query(sql: str) -> tuple[bool, str]:
    """
    Validates a SQL query for read-only safety (guardrail against destructive SQL).
    Returns (is_valid, reason).
    """
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        return False, "Multi-statement queries are forbidden."
    tokens = re.findall(r"\b[A-Za-z_]+\b", cleaned)
    if not tokens:
        return False, "Query is empty or invalid."
    if tokens[0].upper() not in {"SELECT", "WITH"}:
        return False, f"Only SELECT/read-only queries are permitted (got {tokens[0].upper()})."
    upper_tokens = {t.upper() for t in tokens}
    blocked = upper_tokens.intersection(DISALLOWED_SQL_KEYWORDS)
    if blocked:
        return False, f"Destructive or modifying operations forbidden: {', '.join(sorted(blocked))}."
    return True, "Query passed read-only validation."

def _month_from_text(text: str) -> list[str]:
    found = []
    # Match month names/abbreviations
    for name, number in MONTHS.items():
        # Avoid false positive on English modal verb "may" followed by common verbs
        if name == "may" and re.search(r"\bmay\s+(be|have|generate|cause|include|occur|show)\b", text, re.I):
            continue
        for match in re.finditer(rf"\b{name}\b", text, re.I):
            # Check adjacent 12 chars for explicit 4-digit year
            year_match = re.search(r"\b20\d{2}\b", text[match.end():match.end()+12])
            if not year_match:
                # Also check before the month name (e.g. 2026 January)
                year_match = re.search(r"\b20\d{2}\b", text[max(0, match.start()-12):match.start()])
            year = year_match.group(0) if year_match else "2026"
            found.append((match.start(), f"{year}-{number:02d}"))

    # Match numeric formats like 2026-01 or 2026/01
    numeric = re.findall(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", text)
    found.extend((text.find(f"{y}-{m}"), f"{y}-{int(m):02d}") for y, m in numeric)
    
    # Sort in order of appearance and deduplicate preserving order
    sorted_months = [m for _, m in sorted(found)]
    deduped = []
    for m in sorted_months:
        if not deduped or deduped[-1] != m:
            deduped.append(m)
    return deduped

def _matches_phrase_or_word(text: str, candidates: tuple[str, ...]) -> bool:
    for c in candidates:
        if " " in c or "-" in c:
            if c in text:
                return True
        else:
            if re.search(rf"\b{re.escape(c)}\b", text, re.I):
                return True
    return False

def deterministic_interpret(question: str) -> dict | None:
    q = question.lower().strip()

    # Reject obvious SQL injections or DDL/DML tampering attempts immediately
    if re.search(r"\b(drop|delete|update|insert|alter|truncate|create|grant|revoke|attach|exec)\b", q, re.I) or ";" in q or "--" in q:
        return None

    months = _month_from_text(q)

    # 1. Compare months intent
    # Handles: "How did revenue change between two months?", "Compare January and February 2026", "change between Jan and Feb"
    is_comparison = _matches_phrase_or_word(q, ("compare", "change", "difference", "between", "versus", "vs"))
    has_month_word = _matches_phrase_or_word(q, ("month", "months"))
    if is_comparison and (len(months) >= 2 or has_month_word):
        month_a = months[0] if len(months) >= 1 else "2026-01"
        month_b = months[1] if len(months) >= 2 else "2026-02"
        return {"intent": "compare_months", "month_a": month_a, "month_b": month_b, "method": "rules"}

    # 2. Monthly trend intent
    # Handles: "What is the monthly revenue trend?", "revenue by month", "monthly sales", "trend over months", "month-by-month"
    if _matches_phrase_or_word(q, ("monthly", "month-wise", "month wise", "trend", "each month", "by month", "per month", "month by month", "over months")):
        return {"intent": "monthly_trend", "method": "rules"}

    # 3. Top region intent
    # Handles: "Which region generated the highest sales?", "best region by revenue", "top region"
    if _matches_phrase_or_word(q, ("region", "state", "territory", "zone", "area")) and _matches_phrase_or_word(q, ("highest", "top", "best", "most", "sales", "revenue", "max")):
        return {"intent": "top_region", "method": "rules"}

    # 4. Top product intent
    # Handles: "Which product generated the highest revenue?", "best selling product", "top item"
    if _matches_phrase_or_word(q, ("product", "item")) and _matches_phrase_or_word(q, ("highest", "top", "best", "most", "generated", "revenue", "sales", "max")):
        return {"intent": "top_product", "method": "rules"}

    # 5. Total revenue intent
    # Handles: "What is the total revenue?", "overall revenue", "gross revenue", "net revenue", "total sales", "overall sales", "sum of revenue", "total turnover", "revenue", "sales"
    if _matches_phrase_or_word(q, ("total revenue", "overall revenue", "gross revenue", "net revenue", "total sales", "overall sales", "sum of revenue", "total turnover", "revenue", "sales")):
        return {"intent": "total_revenue", "method": "rules"}

    return None

def _llm_interpret(question: str) -> dict | None:
    if not LLM_API_KEY:
        return None
    prompt = ("Classify the business question into exactly one supported intent. Return JSON only with keys "
              "intent, month_a, month_b. Allowed intents: total_revenue, top_product, monthly_trend, top_region, "
              "compare_months, unsupported. Months must be YYYY-MM. Never generate SQL. If comparing months, extract "
              "two months. Question: " + question)
    payload = {"model": LLM_MODEL, "temperature": 0, "messages": [
        {"role": "system", "content": "You are a strict intent classifier. Output one JSON object and no markdown."},
        {"role": "user", "content": prompt}
    ]}
    request = urllib.request.Request(
        LLM_BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode())
        content = body["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            return None
        result = json.loads(match.group(0))
        intent = result.get("intent")
        if intent not in SUPPORTED:
            return None
        parsed = {"intent": intent, "method": "llm"}
        if intent == "compare_months":
            for key in ("month_a", "month_b"):
                value = result.get(key)
                if not isinstance(value, str) or not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", value):
                    return None
                parsed[key] = value
        return parsed
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None

def interpret_question(question: str) -> dict:
    # Prefer AI classification when configured; deterministic rules are the safe fallback.
    return _llm_interpret(question) or deterministic_interpret(question) or {"intent": "unsupported", "method": "rules"}
