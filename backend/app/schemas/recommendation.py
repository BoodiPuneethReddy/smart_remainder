"""schemas/recommendation.py — Chat request/response schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class StepLogSchema(BaseModel):
    agent_name: str
    status: str
    summary: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    question: str
    document_id: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    question: str
    created_at: datetime
    primary_intent: Optional[str] = None
    step_logs: List[StepLogSchema] = []


class RecommendationResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}
