from typing import List
import uuid

from fastapi import FastAPI, HTTPException

from app.models.schemas import (ChatRequest, ChatResponse, Customer, Citation,
                                SearchRequest, SearchHit)
from app.services.retriever import get_retriever

app = FastAPI(title="Saathi API", version="0.2")

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


@app.post("/search", response_model=List[SearchHit])
async def search(req: SearchRequest):
    return get_retriever().search(req.query, req.k, req.product, req.tier)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    customer = DUMMY_CUSTOMERS.get(req.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Filter by product only, so "compare Silver and Gold" still works
    hits = get_retriever().search(req.question, k=3, product=customer.product)

    if not hits:
        answer = "I could not find this in the policy documents."
    else:
        answer = f"Top match: {hits[0].text}"  # LLM answer replaces this on Day 36

    return ChatResponse(
        answer=answer,
        intent="policy_question",  # Sairaj's classifier replaces this
        citations=[Citation(source_id=h.source_id, clause_id=h.clause_id, version=h.version) for h in hits],
        session_id=req.session_id or str(uuid.uuid4()),
    )