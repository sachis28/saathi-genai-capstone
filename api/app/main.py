from typing import Dict, List
import uuid

from fastapi import FastAPI, HTTPException

from app.models.schemas import (ChatRequest, ChatResponse, Customer, Citation,
                                SearchRequest, SearchHit, DraftRequest, Draft, Turn)
from app.services.retriever import get_retriever
from app.services.answer import generate_answer
from app.services import memory

from app.services.safety import is_injection, safe_log
import logging

logging.basicConfig(level=logging.INFO)

BLOCKED_MSG = "BLOCKED: this request looks like a prompt-injection attempt and was not processed."


app = FastAPI(title="Saathi API", version="0.4")

DUMMY_CUSTOMERS = {
    "C-204": Customer(customer_id="C-204", name="Demo Customer", product="Health", tier="Silver", consent=True),
    "C-205": Customer(customer_id="C-205", name="No Consent Customer", product="Health", tier="Gold", consent=False),
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


def get_draft_or_404(draft_id: str) -> Draft:
    draft = DRAFTS.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


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
    session_id = req.session_id or str(uuid.uuid4())

    # Safety: block prompt injection before retrieval or LLM
    if is_injection(req.question):
        safe_log("prompt_injection_blocked", customer_id=customer.customer_id, question=req.question)
        return ChatResponse(answer=BLOCKED_MSG, intent="prompt_injection", citations=[],
                            session_id=session_id, resolved_question=req.question)

    resolved = memory.resolve_question(session_id, req.question)
    hits = get_retriever().search(resolved, k=3, product=customer.product)
    answer, citations = generate_answer(resolved, hits)

    memory.add_turn(session_id, req.question, resolved, answer)
    safe_log("chat", customer_id=customer.customer_id, question=req.question, citations=len(citations))

    return ChatResponse(
        answer=answer,
        intent="policy_question",  # Sairaj's classifier replaces this
        citations=citations,
        session_id=session_id,
        resolved_question=resolved,
    )

@app.get("/sessions/{session_id}", response_model=List[Turn])
async def get_session(session_id: str):
    return memory.get_history(session_id)


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


@app.post("/drafts/{draft_id}/approve", response_model=Draft)
async def approve_draft(draft_id: str):
    draft = get_draft_or_404(draft_id)
    if draft.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=409, detail=f"Cannot approve a draft in status {draft.status}")
    draft.status = "APPROVED"
    return draft


@app.post("/drafts/{draft_id}/send", response_model=Draft)
async def send_draft(draft_id: str):
    draft = get_draft_or_404(draft_id)

    # Rule 1: never send without human approval
    if draft.status != "APPROVED":
        raise HTTPException(status_code=409, detail="BLOCKED: draft must be approved by the agent before sending")

    # Rule 2: re-check consent at send time, not only at draft time
    customer = get_customer_or_404(draft.customer_id)
    if not customer.consent:
        draft.status = "BLOCKED_NO_CONSENT"
        raise HTTPException(status_code=403, detail="BLOCKED: customer has not given consent")

    draft.status = "SIMULATED_SENT"  # nothing real is ever sent
    return draft