from typing import Dict, List
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException, Query, Depends
from starlette.concurrency import run_in_threadpool
import httpx

from app.services.ml_service import classify_intent, renewal_worklist
from app.services.worklist_access import AgentPrincipal, authenticate_agent, load_authorized_radar_frame

from app.models.schemas import (ChatRequest, ChatResponse, Comparison, Customer, Citation,
                                SearchRequest, SearchHit, DraftRequest, Draft, Turn, RetrievedClause)
from app.routers.summary import router as summary_router
from app.services.retriever import get_retriever
from app.services.query_rewrite import rewrite_query
from app.services.customer_context import scope_question, record_answer, tier_filter
from app.services.compare import tiers_named, is_comparison, comparison_tiers, build_comparison, comparison_answer
from app.services.topic_guard import is_on_topic, OFF_TOPIC_MSG
from app.services.answer import generate_answer, NOT_FOUND
from app.services.customers import load_customers
from app.services import memory
from app.services import audit
from app.services import telemetry
import time
from fastapi import Request
from app.services.safety import is_injection, safe_log
from app.agent.agent import run_agent

logging.basicConfig(level=logging.INFO)

BLOCKED_MSG = "BLOCKED: this request looks like a prompt-injection attempt and was not processed."

app = FastAPI(title="Saathi API", version="0.6")
app.include_router(summary_router)


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    telemetry.record_request(getattr(route, "path", request.url.path), response.status_code,
                             (time.perf_counter() - start) * 1000)
    return response


@app.get("/metrics")
async def metrics():
    """Trust Scorecard numbers: latency per route, block rate, citation rate, not-found rate."""
    return telemetry.summary()

DRAFTS: Dict[str, Draft] = {}

RENEWAL_TEMPLATE = (
    "Dear {name}, your {product} {tier} policy is due for renewal. "
    "You can renew within the 30 day grace period after expiry, but claims for events "
    "during the grace period are not payable. Please contact your agent to renew on time."
)


def get_customer_or_404(customer_id: str) -> Customer:
    customer = load_customers().get(customer_id)
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


@app.get("/customers", response_model=List[Customer])
async def list_customers():
    return list(load_customers().values())


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
        audit.log_event("prompt_injection_blocked", customer_id=customer.customer_id)
        telemetry.record_chat("blocked", 0)
        return ChatResponse(answer=BLOCKED_MSG, intent="prompt_injection", citations=[],
                            session_id=session_id, resolved_question=req.question)

    # Off-topic input ("dumb?", "tell me a joke") gets a polite redirect, not retrieved clauses.
    if (not memory.FOLLOW_UP.match(req.question) and not is_on_topic(req.question)
            and not record_answer(req.question, customer)):
        audit.log_event("off_topic_redirected", customer_id=customer.customer_id)
        telemetry.record_chat("off_topic", 0)
        return ChatResponse(answer=OFF_TOPIC_MSG, intent="out_of_scope", citations=[],
                            session_id=session_id, resolved_question=req.question)

    resolved = memory.resolve_question(session_id, req.question)
    try:
        classification = await run_in_threadpool(classify_intent, resolved)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=503, detail="Configure a trained intent provider: python -m ml.hf_models distilbert, or INTENT_PROVIDER=tfidf_lr after python -m ml.train_intent")

    comparison = None
    retrieved = []
    from_record = record_answer(resolved, customer)
    if from_record:
        answer, citations = from_record, []
    elif is_comparison(req.question) and (comparison := build_comparison(
            customer.product, comparison_tiers(req.question, customer.tier))):
        answer, citations = comparison_answer(comparison)
    else:
        scoped = scope_question(resolved, customer)
        hits = get_retriever().search(rewrite_query(scoped), k=5, product=customer.product,
                                      tier=tier_filter(req.question if tiers_named(req.question) else scoped, customer))
        answer, citations = generate_answer(scoped, hits)
        cited = {(c.source_id, c.clause_id) for c in citations}
        retrieved = [RetrievedClause(source_id=h.source_id, clause_id=h.clause_id, version=h.version, text=h.text,
                                     score=h.score, used=(h.source_id, h.clause_id) in cited) for h in hits]

    memory.add_turn(session_id, req.question, resolved, answer)
    outcome = ("record" if from_record else "comparison" if comparison
               else "not_found" if answer == NOT_FOUND else "answer")
    telemetry.record_chat(outcome, len(citations), classification["intent"])
    safe_log("chat", customer_id=customer.customer_id, question=req.question, citations=len(citations))
    audit.log_event("chat", customer_id=customer.customer_id, intent=classification["intent"],
                    citations=len(citations))

    return ChatResponse(
        answer=answer,
        intent=classification["intent"],
        citations=citations,
        session_id=session_id,
        resolved_question=resolved,
        comparison=comparison,
        intent_confidence=classification.get("confidence"),
        intent_model=classification.get("model"),
        intent_scores=classification.get("scores") or {},
        retriever=os.getenv("RETRIEVER", "local") if retrieved else None,
        retrieved=retrieved,
    )


@app.post("/compare", response_model=Comparison)
async def compare(customer_id: str, tiers: str = "Silver,Gold"):
    """Cited plan comparison table, e.g. /compare?customer_id=C-204&tiers=Silver,Gold"""
    customer = get_customer_or_404(customer_id)
    wanted = [t.strip().title() for t in tiers.split(",") if t.strip()]
    result = build_comparison(customer.product, wanted)
    if result is None:
        raise HTTPException(status_code=422, detail="Comparison needs two or more Health tiers: Silver, Gold, Platinum")
    audit.log_event("comparison", customer_id=customer.customer_id, tiers=",".join(wanted))
    return result


@app.post("/agent/chat")
async def agent_chat(req: ChatRequest):
    """Agentic RAG: the model picks MCP tools (max 3, allowlisted); the answer stays grounded."""
    customer = get_customer_or_404(req.customer_id)
    if is_injection(req.question):
        audit.log_event("injection_blocked", customer_id=customer.customer_id, route="agent")
        raise HTTPException(status_code=400, detail=BLOCKED_MSG)
    result = await run_agent(req.question, customer.customer_id, customer.agent_id or "")
    audit.log_event("agent_chat", customer_id=customer.customer_id, tools=len(result["trace"]))
    return result


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
    audit.log_event("draft_created", draft_id=draft.draft_id, customer_id=draft.customer_id)
    return draft


@app.post("/drafts/{draft_id}/approve", response_model=Draft)
async def approve_draft(draft_id: str):
    draft = get_draft_or_404(draft_id)
    if draft.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=409, detail=f"Cannot approve a draft in status {draft.status}")
    draft.status = "APPROVED"
    audit.log_event("draft_approved", draft_id=draft.draft_id)
    return draft


@app.post("/drafts/{draft_id}/send", response_model=Draft)
async def send_draft(draft_id: str):
    draft = get_draft_or_404(draft_id)

    # Rule 1: never send without human approval
    if draft.status != "APPROVED":
        audit.log_event("send_blocked_not_approved", draft_id=draft.draft_id)
        raise HTTPException(status_code=409, detail="BLOCKED: draft must be approved by the agent before sending")

    # Rule 2: re-check consent at send time, not only at draft time
    customer = get_customer_or_404(draft.customer_id)
    if not customer.consent:
        draft.status = "BLOCKED_NO_CONSENT"
        audit.log_event("send_blocked_no_consent", draft_id=draft.draft_id, customer_id=draft.customer_id)
        raise HTTPException(status_code=403, detail="BLOCKED: customer has not given consent")

    draft.status = "SIMULATED_SENT"  # nothing real is ever sent
    audit.log_event("draft_sent_simulated", draft_id=draft.draft_id, customer_id=draft.customer_id)
    return draft


@app.get("/audit")
async def get_audit():
    return audit.read_events()


@app.get("/audit/verify")
async def verify_audit():
    valid, broken_at, total = audit.verify_chain()
    return {"valid": valid, "broken_at_seq": broken_at, "total_events": total}


@app.get("/worklist")
async def worklist(
    limit: int = Query(default=10, ge=1, le=100),
    principal: AgentPrincipal = Depends(authenticate_agent),
):
    """CRM-linked synthetic Radar scores, filtered before model inference."""
    try:
        frame = await run_in_threadpool(load_authorized_radar_frame, principal)
        if frame.empty:
            return {"items": [], "synthetic": True}
        rows = await renewal_worklist(frame)
        return {"items": rows[:limit], "synthetic": True}
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Configure CRM-linked Radar input and train Renewal Radar first")
    except (OSError, KeyError, ValueError, TypeError, httpx.HTTPError):
        raise HTTPException(status_code=503, detail="Renewal risk provider is unavailable or returned invalid data")
