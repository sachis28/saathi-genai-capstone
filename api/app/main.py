from fastapi import FastAPI, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, Customer, Citation
import uuid

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
    return ChatResponse(
        answer="Dummy answer for now",
        intent="policy_question",
        citations=[Citation(source_id="DOC-01", clause_id="CL-1", version="v1")],
        session_id=req.session_id or str(uuid.uuid4()),
    )