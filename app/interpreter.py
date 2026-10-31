
import json
import re
import urllib.request
import urllib.error

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


SUPPORTED = {
    "total_revenue",
    "top_product",
    "monthly_trend",
    "top_region",
    "compare_months",
    "channel_breakdown",
    "category_breakdown",
    "product_breakdown",
    "region_breakdown",
    "filtered_revenue",
    "audit_log"
}

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
    "ATTACH", "DETACH", "REPLACE", "CREATE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE"
}

KNOWN_REGIONS = ("north", "south", "east", "west")
KNOWN_CATEGORIES = ("accessories", "electronics", "furniture")
KNOWN_CHANNELS = ("online", "retail")


def validate_sql_query(sql: str) -> tuple[bool, str]:
    """
    Validates SQL for read-only safety.
    Returns (is_valid, reason).
    """
    cleaned = sql.strip().rstrip(";")

    if ";" in cleaned:
        return False, "Multi-statement queries are forbidden."

    tokens = re.findall(r"\b[A-Za-z_]+\b", cleaned)

    if not tokens:
        return False, "Query is empty or invalid."

    if tokens[0].upper() not in {"SELECT", "WITH"}:
        return False, (
            f"Only SELECT/read-only queries are permitted "
            f"(got {tokens[0].upper()})."
        )

    upper_tokens = {token.upper() for token in tokens}
    blocked = upper_tokens.intersection(DISALLOWED_SQL_KEYWORDS)

    if blocked:
        return False, (
            "Destructive or modifying operations forbidden: "
            + ", ".join(sorted(blocked)) + "."
        )

    return True, "Query passed read-only validation."


def _month_from_text(text: str) -> list[str]:
    found = []

    for name, number in MONTHS.items():

        if name == "may" and re.search(
            r"\bmay\s+(be|have|generate|cause|include|occur|show)\b",
            text,
            re.I
        ):
            continue

        for match in re.finditer(rf"\b{name}\b", text, re.I):

            year_match = re.search(
                r"\b20\d{2}\b",
                text[match.end():match.end() + 12]
            )

            if not year_match:
                year_match = re.search(
                    r"\b20\d{2}\b",
                    text[max(0, match.start() - 12):match.start()]
                )

            year = year_match.group(0) if year_match else "2026"

            found.append(
                (match.start(), f"{year}-{number:02d}")
            )

    numeric = re.findall(
        r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b",
        text
    )

    found.extend(
        (text.find(f"{year}-{month}"), f"{year}-{int(month):02d}")
        for year, month in numeric
    )

    sorted_months = [month for _, month in sorted(found)]

    deduped = []

    for month in sorted_months:
        if not deduped or deduped[-1] != month:
            deduped.append(month)

    return deduped


def _matches_phrase_or_word(
    text: str,
    candidates: tuple[str, ...]
) -> bool:

    for candidate in candidates:

        if " " in candidate or "-" in candidate:
            if candidate in text:
                return True

        else:
            if re.search(
                rf"\b{re.escape(candidate)}\b",
                text,
                re.I
            ):
                return True

    return False


def deterministic_interpret(question: str) -> dict | None:

    q = question.lower().strip()

    # Reject obvious SQL injection and DDL/DML attempts
    if (
        re.search(
            r"\b(drop|delete|update|insert|alter|truncate|create|grant|revoke|attach|exec)\b",
            q,
            re.I
        )
        or ";" in q
        or "--" in q
    ):
        return None

    # 1. Audit log
    if _matches_phrase_or_word(
        q,
        (
            "excluded rows",
            "excluded records",
            "excluded transactions",
            "invalid records",
            "invalid rows",
            "audit log",
            "data quality",
            "why were records excluded",
            "rejected rows"
        )
    ):
        return {
            "intent": "audit_log",
            "method": "rules"
        }

    months = _month_from_text(q)

    # 2. Compare months
    is_comparison = _matches_phrase_or_word(
        q,
        ("compare", "change", "difference", "between", "versus", "vs")
    )

    has_month_word = _matches_phrase_or_word(
        q,
        ("month", "months")
    )

    if is_comparison and (len(months) >= 2 or has_month_word):

        month_a = months[0] if len(months) >= 1 else "2026-01"
        month_b = months[1] if len(months) >= 2 else "2026-02"

        return {
            "intent": "compare_months",
            "month_a": month_a,
            "month_b": month_b,
            "method": "rules"
        }

    # 3. Monthly trend
    if _matches_phrase_or_word(
        q,
        (
            "monthly",
            "month-wise",
            "month wise",
            "trend",
            "each month",
            "by month",
            "per month",
            "month by month",
            "over months"
        )
    ):
        return {
            "intent": "monthly_trend",
            "method": "rules"
        }

    # 4. Channel breakdown
    if _matches_phrase_or_word(
        q,
        (
            "channel",
            "sales channel",
            "online vs retail",
            "retail vs online",
            "online or retail"
        )
    ):
        return {
            "intent": "channel_breakdown",
            "method": "rules"
        }

    # 5. Category breakdown
    if _matches_phrase_or_word(
        q,
        (
            "category breakdown",
            "sales by category",
            "revenue by category",
            "breakdown by category",
            "which category",
            "top category",
            "best category"
        )
    ):
        return {
            "intent": "category_breakdown",
            "method": "rules"
        }

    # 6. Product breakdown
    if _matches_phrase_or_word(
        q,
        (
            "all products",
            "product breakdown",
            "sales by product",
            "revenue by product",
            "breakdown by product",
            "every product",
            "products breakdown"
        )
    ):
        return {
            "intent": "product_breakdown",
            "method": "rules"
        }

    # 7. Region breakdown
    if _matches_phrase_or_word(
        q,
        (
            "all regions",
            "regional breakdown",
            "region breakdown",
            "sales by region",
            "revenue by region",
            "breakdown by region",
            "every region"
        )
    ):
        return {
            "intent": "region_breakdown",
            "method": "rules"
        }

    # 8. Top region
    if (
        _matches_phrase_or_word(
            q,
            ("region", "state", "territory", "zone", "area")
        )
        and _matches_phrase_or_word(
            q,
            (
                "highest",
                "top",
                "best",
                "most",
                "max",
                "leading",
                "leader"
            )
        )
    ):
        return {
            "intent": "top_region",
            "method": "rules"
        }

    # 9. Top product
    if (
        _matches_phrase_or_word(q, ("product", "item"))
        and _matches_phrase_or_word(
            q,
            (
                "highest",
                "top",
                "best",
                "most",
                "max",
                "leading",
                "leader",
                "best selling",
                "top selling"
            )
        )
    ):
        return {
            "intent": "top_product",
            "method": "rules"
        }

    # 10. Filtered revenue
    is_revenue_query = _matches_phrase_or_word(
        q,
        (
            "revenue",
            "sales",
            "how much",
            "total",
            "turnover",
            "performance"
        )
    )

    if is_revenue_query:

        for region in KNOWN_REGIONS:
            if re.search(rf"\b{region}\b", q):
                return {
                    "intent": "filtered_revenue",
                    "dimension": "region",
                    "value": region.title(),
                    "method": "rules"
                }

        for category in KNOWN_CATEGORIES:
            if re.search(rf"\b{category}\b", q):
                return {
                    "intent": "filtered_revenue",
                    "dimension": "category",
                    "value": category.title(),
                    "method": "rules"
                }

        for channel in KNOWN_CHANNELS:
            if re.search(rf"\b{channel}\b", q):
                return {
                    "intent": "filtered_revenue",
                    "dimension": "sales_channel",
                    "value": channel.title(),
                    "method": "rules"
                }

    # 11. Total revenue
    if _matches_phrase_or_word(
        q,
        (
            "total revenue",
            "overall revenue",
            "gross revenue",
            "net revenue",
            "total sales",
            "overall sales",
            "sum of revenue",
            "total turnover",
            "revenue",
            "sales"
        )
    ):
        return {
            "intent": "total_revenue",
            "method": "rules"
        }

    return None


def _llm_interpret(question: str) -> dict | None:

    if not LLM_API_KEY:
        return None

    allowed = ", ".join(sorted(SUPPORTED)) + ", unsupported"

    prompt = (
        f"Classify the business question into exactly one supported intent: {allowed}. "
        "Return JSON only with keys: intent, month_a, month_b, dimension, value. "
        "For filtered_revenue, extract the exact region, category, or "
        "sales_channel value from the question. "
        "Allowed dimensions: region, category, sales_channel. "
        "Months must be YYYY-MM. Never generate SQL. Question: "
        + question
    )

    payload = {
        "model": LLM_MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict intent classifier for business intelligence. "
                    "Output one JSON object and no markdown."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    request = urllib.request.Request(
        LLM_BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "RSG-AI-BI-Assistant/1.0"
        },
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

        parsed = {
            "intent": intent,
            "method": "llm"
        }

        # Validate comparison months
        if intent == "compare_months":

            for key in ("month_a", "month_b"):

                value = result.get(key)

                if (
                    not isinstance(value, str)
                    or not re.fullmatch(
                        r"20\d{2}-(0[1-9]|1[0-2])",
                        value
                    )
                ):
                    return None

                parsed[key] = value

        # Validate filtered revenue parameters
        if intent == "filtered_revenue":

            dimension = result.get("dimension")
            value = result.get("value")

            if dimension not in {
                "region",
                "category",
                "sales_channel"
            }:
                return None

            if not isinstance(value, str) or not value.strip():
                return None

            parsed["dimension"] = dimension
            parsed["value"] = value.strip()

        return parsed

    except (
        urllib.error.URLError,
        TimeoutError,
        KeyError,
        ValueError,
        TypeError,
        json.JSONDecodeError
    ):
        return None


def interpret_question(question: str) -> dict:

    # First, prefer deterministic rules for clear supported patterns.
    rule_result = deterministic_interpret(question)

    if rule_result is not None:
        return rule_result

    # Use LLM for questions not recognized by deterministic rules.
    llm_result = _llm_interpret(question)

    if llm_result is not None:
        return llm_result

    return {
        "intent": "unsupported",
        "method": "rules"
    }

