from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .config import CSV_PATH, STATIC_DIR
from .database import initialize_database
from .ingestion import load_csv
from .interpreter import interpret_question
from . import analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    # Seed only when the database is empty; use /api/reload to explicitly re-import.
    summary=analytics.dataset_summary()
    if not summary or not summary.get("total_rows"):
        load_csv(CSV_PATH)
    yield

app = FastAPI(title="RSG AI Business Intelligence Assistant", version="1.0.0", lifespan=lifespan)

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)

@app.get("/api/health")
def health():
    return {"status":"ok", "service":"RSG AI BI Assistant"}

@app.get("/api/summary")
def summary():
    return analytics.dataset_summary()

@app.post("/api/ask")
def ask(payload: AskRequest):
    parsed=interpret_question(payload.question)
    intent=parsed["intent"]
    try:
        if intent == "total_revenue": result=analytics.total_revenue()
        elif intent == "top_product": result=analytics.top_product()
        elif intent == "monthly_trend": result=analytics.monthly_trend()
        elif intent == "top_region": result=analytics.top_region()
        elif intent == "compare_months": result=analytics.compare_months(parsed["month_a"], parsed["month_b"])
        else:
            return {"supported":False, "answer":"I couldn't map that question to a supported sales analysis. Try asking about total revenue, top product, monthly trend, top region, or revenue change between two months.", "data":None, "interpretation_method":parsed.get("method")}
        return {"supported":True, "intent":intent, "answer":result["answer"], "data":result["data"], "interpretation_method":parsed.get("method"), "calculation":"Deterministic, read-only SQLite query"}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics query failed. Check server logs and database state.") from exc

@app.post("/api/reload")
def reload_data():
    try:
        result=load_csv(CSV_PATH)
        return {"message":"CSV reloaded successfully", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
