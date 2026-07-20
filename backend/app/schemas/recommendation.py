"""schemas/recommendation.py — Chat request/response schemas."""

from datetime import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    question: str
    created_at: datetime


class RecommendationResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}
