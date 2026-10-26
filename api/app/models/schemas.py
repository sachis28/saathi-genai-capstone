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


class Customer(BaseModel):
    customer_id: str
    name: str
    product: str
    tier: str