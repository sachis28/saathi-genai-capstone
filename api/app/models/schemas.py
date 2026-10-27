from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    customer_id: str
    question: str
    session_id: Optional[str] = None


class Citation(BaseModel):
    source_id: str
    clause_id: str
    version: str


class ChatResponse(BaseModel):
    answer: str
    intent: str
    citations: List[Citation] = []
    session_id: str
    resolved_question: Optional[str] = None


class Customer(BaseModel):
    customer_id: str
    name: str
    product: str
    tier: str
    consent: bool = True


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