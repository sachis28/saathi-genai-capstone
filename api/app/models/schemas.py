"""Pydantic models: the shapes of the JSON going in and out of the API.

FastAPI uses these to validate requests, build responses and generate the /docs page."""
from pydantic import BaseModel, StrictBool, Field
from typing import Dict, List, Optional, Literal
from datetime import date


# Body of POST /chat and /agent/chat.
class ChatRequest(BaseModel):
    customer_id: str
    question: str
    session_id: Optional[str] = None


# One citation: which document (source_id), which clause, and which version.
class Citation(BaseModel):
    source_id: str
    clause_id: str
    version: str


# Comparison table: Comparison -> rows (one per aspect) -> cells (one per tier).
class ComparisonCell(BaseModel):
    text: str
    source_id: str
    clause_id: str
    version: str


class ComparisonRow(BaseModel):
    aspect: str
    cells: Dict[str, Optional[ComparisonCell]]


class Comparison(BaseModel):
    product: str
    tiers: List[str]
    rows: List[ComparisonRow]


# What /chat returns.
class ChatResponse(BaseModel):
    answer: str
    intent: str
    citations: List[Citation] = []
    session_id: str
    resolved_question: Optional[str] = None
    comparison: Optional[Comparison] = None


# One customer's CRM record. Status fields are filled in by services/customers.py.
class Customer(BaseModel):
    customer_id: str
    name: str
    product: str
    tier: str
    consent: StrictBool = True
    agent_id: Optional[str] = None
    renewal_date: Optional[date] = None
    annual_premium_inr: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    cancelled: StrictBool = False
    policy_status: Optional[Literal["ACTIVE", "IN_GRACE", "LAPSED", "CANCELLED"]] = None
    renewal_eligible: StrictBool = False
    eligibility_reason: Optional[str] = None


# Body of POST /search.
class SearchRequest(BaseModel):
    query: str
    k: int = 5
    product: Optional[str] = None
    tier: Optional[str] = None


# One retrieved clause with its relevance score.
class SearchHit(BaseModel):
    source_id: str
    clause_id: str
    version: str
    product: str
    tier: str
    text: str
    score: float


# Body of POST /drafts.
class DraftRequest(BaseModel):
    customer_id: str


# A renewal message draft. status goes PENDING_APPROVAL -> APPROVED -> SIMULATED_SENT.
class Draft(BaseModel):
    draft_id: str
    customer_id: str
    message: str
    status: str
    citations: List[Citation] = []


# One remembered chat turn.
class Turn(BaseModel):
    question: str
    resolved_question: str
    answer: str