"""Saathi API: the FastAPI app that the web app and console talk to.

This file wires every route (URL) to the services that do the real work:
- /chat          grounded RAG answer for one customer (the main demo flow)
- /agent/chat    the same question answered by the Semantic Kernel agent using MCP tools
- /compare       a side-by-side table of tier clauses (Silver vs Gold vs Platinum)
- /drafts/...    renewal message drafts: create -> human approves -> simulated send
- /worklist      Renewal Radar risk scores, only for the signed-in agent's customers
- /audit         the tamper-evident audit log and its hash-chain check
- /metrics       live Trust Scorecard numbers (latency, block rate, citation rate)

Safety rules (prompt-injection block, off-topic guard, citation and grounding checks,
human approval, consent re-check) are all enforced here in code, not left to the LLM."""
# Standard library and FastAPI imports.
from typing import Dict, List
import logging
import uuid

from fastapi import FastAPI, HTTPException, Query, Depends
from starlette.concurrency import run_in_threadpool
import httpx

# Our own modules. Each "service" does one job; main.py only connects them together.
from app.services.ml_service import classify_intent, renewal_worklist
from app.services.worklist_access import AgentPrincipal, authenticate_agent, load_authorized_radar_frame

from app.models.schemas import (ChatRequest, ChatResponse, Comparison, Customer, Citation,
                                SearchRequest, SearchHit, DraftRequest, Draft, Turn)
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

# Print INFO-level logs to the console so we can watch requests during a demo.
logging.basicConfig(level=logging.INFO)

# The fixed reply shown when the injection detector fires. Nothing else runs for that request.
BLOCKED_MSG = "BLOCKED: this request looks like a prompt-injection attempt and was not processed."

# Create the web app and plug in the extra routes for customer summaries (routers/summary.py).
app = FastAPI(title="Saathi API", version="0.6")
app.include_router(summary_router)


# Middleware runs around EVERY request: we time it and record route, status and latency
@app.middleware("http")
# so /metrics can report p50/p95 latency and error rate per route.
async def telemetry_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    telemetry.record_request(getattr(route, "path", request.url.path), response.status_code,
                             (time.perf_counter() - start) * 1000)
    return response


# GET /metrics returns the in-memory telemetry summary (see services/telemetry.py).
@app.get("/metrics")
async def metrics():
    """Trust Scorecard numbers: latency per route, block rate, citation rate, not-found rate."""
    return telemetry.summary()

# In-memory store of renewal drafts, keyed by draft_id. It resets when the API restarts (demo only).
DRAFTS: Dict[str, Draft] = {}

# Text of the renewal message. {name}, {product} and {tier} are filled from the customer record.
RENEWAL_TEMPLATE = (
    "Dear {name}, your {product} {tier} policy is due for renewal. "
    "You can renew within the 30 day grace period after expiry, but claims for events "
    "during the grace period are not payable. Please contact your agent to renew on time."
)


# Helper: look up a customer or stop the request with a 404 error.
def get_customer_or_404(customer_id: str) -> Customer:
    customer = load_customers().get(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


# Helper: look up a draft or stop the request with a 404 error.
def get_draft_or_404(draft_id: str) -> Draft:
    draft = DRAFTS.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


# GET /health is used by Docker, CI and Azure to check the API is up.
@app.get("/health")
async def health():
    return {"status": "ok"}


# GET /customers lists every customer (demo + bulk data) for the customer picker in the UI.
@app.get("/customers", response_model=List[Customer])
async def list_customers():
    return list(load_customers().values())


# GET /customers/{id} returns one customer's CRM record.
@app.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    return get_customer_or_404(customer_id)


# POST /search runs only the retrieval step (no LLM) so you can inspect which clauses come back.
@app.post("/search", response_model=List[SearchHit])
async def search(req: SearchRequest):
    return get_retriever().search(req.query, req.k, req.product, req.tier)


# POST /chat is the main RAG flow. Order of steps:
# 1) block prompt injection, 2) redirect off-topic questions, 3) resolve follow-ups with memory,
# 4) classify intent, 5) answer from the customer record, a comparison table, or retrieval + LLM,
# 6) log telemetry and audit, 7) return the answer with its citations.
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    customer = get_customer_or_404(req.customer_id)
    # Reuse the caller's session_id so follow-ups ("and Platinum?") can see earlier turns.
    session_id = req.session_id or str(uuid.uuid4())

    # Safety: block prompt injection before retrieval or LLM
    if is_injection(req.question):
        safe_log("prompt_injection_blocked", customer_id=customer.customer_id, question=req.question)
        audit.log_event("prompt_injection_blocked", customer_id=customer.customer_id)
        telemetry.record_chat("blocked", 0)
        return ChatResponse(answer=BLOCKED_MSG, intent="prompt_injection", citations=[],
                            session_id=session_id, resolved_question=req.question)

    # Off-topic input ("dumb?", "tell me a joke") gets a polite redirect, not retrieved clauses.
    # A question is redirected only if it is not a follow-up, not on topic, and not answerable from the record.
    if (not memory.FOLLOW_UP.match(req.question) and not is_on_topic(req.question)
            and not record_answer(req.question, customer)):
        audit.log_event("off_topic_redirected", customer_id=customer.customer_id)
        telemetry.record_chat("off_topic", 0)
        return ChatResponse(answer=OFF_TOPIC_MSG, intent="out_of_scope", citations=[],
                            session_id=session_id, resolved_question=req.question)

    # Turn a follow-up like "and Platinum?" into a full question using the previous turn.
    resolved = memory.resolve_question(session_id, req.question)
    # Intent classification (ML model) runs in a thread so it does not block other requests.
    try:
        classification = await run_in_threadpool(classify_intent, resolved)
    # The model file is missing or misconfigured: tell the caller how to train/configure it.
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=503, detail="Configure a trained intent provider: python -m ml.hf_models distilbert, or INTENT_PROVIDER=tfidf_lr after python -m ml.train_intent")

    # Pick ONE of three ways to answer:
    comparison = None
    # (a) questions about the customer's own data (renewal date, consent...) come from the CRM record;
    from_record = record_answer(resolved, customer)
    if from_record:
        answer, citations = from_record, []
    # (b) "compare Silver and Gold" builds a cited table straight from clauses (no LLM writes cells);
    elif is_comparison(req.question) and (comparison := build_comparison(
            customer.product, comparison_tiers(req.question, customer.tier))):
        answer, citations = comparison_answer(comparison)
    # (c) everything else: scope the question to the customer's plan, search clauses, let the LLM answer.
    else:
        # "this policy" becomes e.g. "Health Gold policy" so retrieval finds the right clauses.
        scoped = scope_question(resolved, customer)
        # Search only this customer's product, and their tier unless the question names another tier.
        hits = get_retriever().search(rewrite_query(scoped), k=5, product=customer.product,
                                      tier=tier_filter(req.question if tiers_named(req.question) else scoped, customer))
        # generate_answer applies the safety checks: poisoned-clause filter, valid citations, grounding.
        answer, citations = generate_answer(scoped, hits)

    # Save this turn in short-term memory, then record what kind of answer it was.
    memory.add_turn(session_id, req.question, resolved, answer)
    outcome = ("record" if from_record else "comparison" if comparison
               else "not_found" if answer == NOT_FOUND else "answer")
    telemetry.record_chat(outcome, len(citations), classification["intent"])
    # safe_log redacts PII (phone, email, PAN, Aadhaar) before anything is written to the logs.
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
    )


# POST /compare returns the comparison table directly (used by the UI's compare view).
@app.post("/compare", response_model=Comparison)
async def compare(customer_id: str, tiers: str = "Silver,Gold"):
    """Cited plan comparison table, e.g. /compare?customer_id=C-204&tiers=Silver,Gold"""
    customer = get_customer_or_404(customer_id)
    # "silver, gold" -> ["Silver", "Gold"]
    wanted = [t.strip().title() for t in tiers.split(",") if t.strip()]
    result = build_comparison(customer.product, wanted)
    if result is None:
        raise HTTPException(status_code=422, detail="Comparison needs two or more Health tiers: Silver, Gold, Platinum")
    audit.log_event("comparison", customer_id=customer.customer_id, tiers=",".join(wanted))
    return result


# POST /agent/chat: the Semantic Kernel agent version of /chat (see app/agent/agent.py).
@app.post("/agent/chat")
async def agent_chat(req: ChatRequest):
    """Agentic RAG: the model picks MCP tools (max 3, allowlisted); the answer stays grounded."""
    customer = get_customer_or_404(req.customer_id)
    # The agent gets the same injection check as /chat, but answers with a 400 error instead.
    if is_injection(req.question):
        audit.log_event("injection_blocked", customer_id=customer.customer_id, route="agent")
        raise HTTPException(status_code=400, detail=BLOCKED_MSG)
    # run_agent returns the answer, citations and a "trace" of which tools were called.
    result = await run_agent(req.question, customer.customer_id, customer.agent_id or "")
    audit.log_event("agent_chat", customer_id=customer.customer_id, tools=len(result["trace"]))
    return result


# GET /sessions/{id} shows the conversation memory for one chat session.
@app.get("/sessions/{session_id}", response_model=List[Turn])
async def get_session(session_id: str):
    return memory.get_history(session_id)


# POST /drafts creates a renewal message for a customer. It always starts as PENDING_APPROVAL.
@app.post("/drafts", response_model=Draft)
async def create_draft(req: DraftRequest):
    customer = get_customer_or_404(req.customer_id)
    # Attach the grace-period clause as the citation that backs the message text.
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


# POST /drafts/{id}/approve: the human agent approves the draft. Only a pending draft can be approved.
@app.post("/drafts/{draft_id}/approve", response_model=Draft)
async def approve_draft(draft_id: str):
    draft = get_draft_or_404(draft_id)
    if draft.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=409, detail=f"Cannot approve a draft in status {draft.status}")
    draft.status = "APPROVED"
    audit.log_event("draft_approved", draft_id=draft.draft_id)
    return draft


# POST /drafts/{id}/send: a simulated send that is protected by two rules below.
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


# GET /audit returns every audit event (each one is chained to the previous one by a hash).
@app.get("/audit")
async def get_audit():
    return audit.read_events()


# GET /audit/verify recomputes the hash chain; if someone edited the log, it reports where it broke.
@app.get("/audit/verify")
async def verify_audit():
    valid, broken_at, total = audit.verify_chain()
    return {"valid": valid, "broken_at_seq": broken_at, "total_events": total}


# GET /worklist: Renewal Radar. The caller must send a bearer token (authenticate_agent),
# and only that agent's eligible customers are scored by the ML model.
@app.get("/worklist")
async def worklist(
    limit: int = Query(default=10, ge=1, le=100),
    principal: AgentPrincipal = Depends(authenticate_agent),
):
    """CRM-linked synthetic Radar scores, filtered before model inference."""
    # Reading files and filtering rows is blocking work, so it runs in a thread.
    try:
        frame = await run_in_threadpool(load_authorized_radar_frame, principal)
        if frame.empty:
            return {"items": [], "synthetic": True}
        # Score the rows with the local model or the Azure ML endpoint (ML_PROVIDER), highest risk first.
        rows = await renewal_worklist(frame)
        return {"items": rows[:limit], "synthetic": True}
    # Missing files or a broken model/endpoint become a clear 503 instead of a crash.
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Configure CRM-linked Radar input and train Renewal Radar first")
    except (OSError, KeyError, ValueError, TypeError, httpx.HTTPError):
        raise HTTPException(status_code=503, detail="Renewal risk provider is unavailable or returned invalid data")
