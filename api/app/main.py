from fastapi import FastAPI, HTTPException, Query
from app.models.schemas import ChatRequest, ChatResponse, Customer, Citation
from app.services.ml_service import classify_intent, renewal_worklist
from starlette.concurrency import run_in_threadpool
import uuid
import httpx

app = FastAPI(title="Saathi API", version="0.1")

DUMMY_CUSTOMERS = {
    "C-204": Customer(customer_id="C-204", name="Demo Customer", product="Health", tier="Silver")
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    if customer_id not in DUMMY_CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    return DUMMY_CUSTOMERS[customer_id]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        classification = await run_in_threadpool(classify_intent, req.question)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=503, detail="Configure a trained intent provider: python -m ml.hf_models distilbert, or INTENT_PROVIDER=tfidf_lr after python -m ml.train_intent")
    return ChatResponse(
        answer="Dummy answer for now",
        intent=classification["intent"],
        citations=[Citation(source_id="DOC-01", clause_id="CL-1", version="v1")],
        session_id=req.session_id or str(uuid.uuid4()),
    )


@app.get("/worklist")
async def worklist(limit: int = Query(default=10, ge=1, le=100)):
    """Synthetic renewal-risk demo. Authorization must be added with the CRM integration."""
    try:
        rows = await renewal_worklist()
        return {"items": rows[:limit], "synthetic": True}
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Generate ML data and train Renewal Radar first")
    except (KeyError, ValueError, httpx.HTTPError):
        raise HTTPException(status_code=503, detail="Renewal risk provider is unavailable or returned invalid data")
