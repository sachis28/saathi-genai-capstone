from typing import Dict, List
import uuid

from fastapi import FastAPI, HTTPException

from app.models.schemas import (ChatRequest, ChatResponse, Customer, Citation,
                                SearchRequest, SearchHit, DraftRequest, Draft)
from app.services.retriever import get_retriever
from app.services.answer import generate_answer

app = FastAPI(title="Saathi API", version="0.3")

DUMMY_CUSTOMERS = {
    "C-204": Customer(customer_id="C-204", name="Demo Customer", product="Health", tier="Silver")
}

DRAFTS: Dict[str, Draft] = {}

RENEWAL_TEMPLATE = (
    "Dear {name}, your {product} {tier} policy is due for renewal. "
    "You can renew within the 30 day grace period after expiry, but claims for events "
    "during the grace period are not payable. Please contact your agent to renew on time."
)


def get_customer_or_404(customer_id: str) -> Customer:
    customer = DUMMY_CUSTOMERS.get(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    return get_customer_or_404(customer_id)


@app.post("/search", response_model=List[SearchHit])
async def search(req: SearchRequest):
    return get_retriever().search(req.query, req.k, req.product, req.tier)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    customer = get_customer_or_404(req.customer_id)
    hits = get_retriever().search(req.question, k=3, product=customer.product)
    answer, citations = generate_answer(req.question, hits)

    return ChatResponse(
        answer=answer,
        intent="policy_question",  # Sairaj's classifier replaces this
        citations=citations,
        session_id=req.session_id or str(uuid.uuid4()),
    )


@app.post("/drafts", response_model=Draft)
async def create_draft(req: DraftRequest):
    customer = get_customer_or_404(req.customer_id)
    hits = get_retriever().search("renewal grace period", k=1)

    draft = Draft(
        draft_id=str(uuid.uuid4()),
        customer_id=customer.customer_id,
        message=RENEWAL_TEMPLATE.format(name=customer.name, product=customer.product, tier=customer.tier),
        status="PENDING_APPROVAL",
        citations=[Citation(source_id=h.source_id, clause_id=h.clause_id, version=h.version) for h in hits],
    )
    DRAFTS[draft.draft_id] = draft
    return draft