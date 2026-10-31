from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .config import CSV_PATH, STATIC_DIR
from .database import initialize_database
from .ingestion import load_csv, load_csv_text
from .interpreter import interpret_question
from . import analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    summary = analytics.dataset_summary()
    if not summary or not summary.get("total_rows"):
        load_csv(CSV_PATH)
    yield

app = FastAPI(
    title="RSG AI Business Intelligence Assistant",
    description="Vectorless RAG and Schema-Grounded AI Analytics Assistant for Sales Intelligence",
    version="1.1.0",
    lifespan=lifespan
)

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RSG AI BI Assistant"}

@app.get("/api/summary")
def summary():
    return analytics.dataset_summary()

@app.get("/api/audit")
def audit():
    return analytics.audit_log()

@app.get("/api/channels")
def channels():
    return analytics.channel_breakdown()

@app.get("/api/categories")
def categories():
    return analytics.category_breakdown()

@app.post("/api/ask")
def ask(payload: AskRequest):
    parsed = interpret_question(payload.question)
    intent = parsed["intent"]
    try:
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
            return {
                "supported": False,
                "answer": (
                    "I couldn't map that question to a supported sales analysis. "
                    "Try asking about total revenue, top product, monthly trend, top region, "
                    "channel breakdown, category performance, regional breakdown, or revenue change between two months."
                ),
                "data": None,
                "interpretation_method": parsed.get("method")
            }
        return {
            "supported": True,
            "intent": intent,
            "answer": result["answer"],
            "sql": result.get("sql"),
            "data": result["data"],
            "interpretation_method": parsed.get("method"),
            "calculation": "Deterministic, read-only SQLite query"
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics query failed. Check server logs and database state.") from exc

@app.post("/api/reload")
def reload_data():
    try:
        result = load_csv(CSV_PATH)
        return {"message": "CSV reloaded successfully", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")
    try:
        content_bytes = await file.read()
        content_text = content_bytes.decode("utf-8-sig")
        result = load_csv_text(content_text)
        return {"message": f"Uploaded and imported '{file.filename}' successfully", **result}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a UTF-8 encoded CSV.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV upload: {exc}")

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
