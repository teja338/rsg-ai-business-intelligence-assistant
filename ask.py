#!/usr/bin/env python3
"""
CLI tool to query the Sales Database using natural language.
Translates question -> intent -> SQL query and prints the SQL command + results directly in the terminal.

Usage:
    python ask.py "What is the total revenue?"
    python ask.py "Which product generated the highest revenue?"
    python ask.py (runs in interactive mode)
"""
import sys
from pathlib import Path
from app.database import initialize_database
from app.ingestion import load_csv
from app.config import CSV_PATH
from app.interpreter import interpret_question
from app import analytics

def run_query(question: str):
    initialize_database()
    summary = analytics.dataset_summary()
    if not summary or not summary.get("total_rows"):
        load_csv(CSV_PATH)

    parsed = interpret_question(question)
    intent = parsed.get("intent")
    
    print("\n" + "=" * 70)
    print(f"QUESTION:  {question}")
    print(f"INTENT:    {intent} (via {parsed.get('method')})")
    print("=" * 70)

    if intent == "total_revenue":
        result = analytics.total_revenue()
    elif intent == "top_product":
        result = analytics.top_product()
    elif intent == "monthly_trend":
        result = analytics.monthly_trend()
    elif intent == "top_region":
        result = analytics.top_region()
    elif intent == "compare_months":
        result = analytics.compare_months(parsed["month_a"], parsed["month_b"])
    elif intent == "channel_breakdown":
        result = analytics.channel_breakdown()
    elif intent == "category_breakdown":
        result = analytics.category_breakdown()
    elif intent == "product_breakdown":
        result = analytics.product_breakdown()
    elif intent == "region_breakdown":
        result = analytics.region_breakdown()
    elif intent == "filtered_revenue":
        result = analytics.filtered_revenue(parsed["dimension"], parsed["value"])
    elif intent == "audit_log":
        result = analytics.audit_log()
    else:
        print("\n[!] UNSUPPORTED QUESTION:")
        print("    Could not map to a supported sales query.")
        print("    Try asking about total revenue, top product, monthly trend, top region, or month comparison.\n")
        return

    print("\n[+] EXECUTED SQL QUERY:")
    print(f"    {result.get('sql', 'N/A')}")
    print("\n[+] ANSWER:")
    print(f"    {result.get('answer')}")
    print("\n[+] SUPPORTING DATA:")
    data = result.get("data")
    if isinstance(data, list):
        for item in data:
            print(f"    • {item}")
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f"    • {k}: {v}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_query(query)
    else:
        print("\n=======================================================")
        print(" RSG AI BI Assistant - Interactive Terminal CLI Mode")
        print(" Type any question below or type 'exit' to quit.")
        print("=======================================================\n")
        # Run default question to demonstrate
        run_query("What is the total revenue?")
        while True:
            try:
                q = input("Enter your question: ").strip()
                if not q or q.lower() in ("exit", "quit", "q"):
                    print("Goodbye!")
                    break
                run_query(q)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break
