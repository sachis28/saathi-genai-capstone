from pydantic import BaseModel, StrictBool, Field
from typing import Dict, List, Optional, Literal
from datetime import date


class ChatRequest(BaseModel):
    customer_id: str
    question: str
    session_id: Optional[str] = None


class Citation(BaseModel):
    source_id: str
    clause_id: str
    version: str


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


class RetrievedClause(BaseModel):
    """One search hit as the retriever ranked it; used=True if the answer cites it."""
    source_id: str
    clause_id: str
    version: str
    text: str
    score: float
    used: bool = False


class ChatResponse(BaseModel):
    answer: str
    intent: str
    citations: List[Citation] = []
    session_id: str
    resolved_question: Optional[str] = None
    comparison: Optional[Comparison] = None
    # Trace details for the UI. Uncalibrated scores, shown for explanation only.
    intent_confidence: Optional[float] = None
    intent_model: Optional[str] = None
    intent_scores: Dict[str, float] = {}
    retriever: Optional[str] = None
    retrieved: List[RetrievedClause] = []


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


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    product: Optional[str] = None
    tier: Optional[str] = None


class SearchHit(BaseModel):
    source_id: str
    clause_id: str
    version: str
    product: str
    tier: str
    text: str
    score: float


class DraftRequest(BaseModel):
    customer_id: str


class Draft(BaseModel):
    draft_id: str
    customer_id: str
    message: str
    status: str
    citations: List[Citation] = []


class Turn(BaseModel):
    question: str
    resolved_question: str
    answer: str