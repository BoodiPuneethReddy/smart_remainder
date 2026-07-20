"""api/routes/chat.py — Recommendation Agent chat endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_ai_client_dep
from app.core.database import get_db
from app.models.user import User
from app.agents import recommendation_agent
from app.services.ai_client import AIInferenceClient
from app.schemas.recommendation import ChatRequest, ChatResponse, RecommendationResponse
from typing import List
from datetime import timezone

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """Submit a study question and receive an AI-generated, data-grounded answer."""
    rec = recommendation_agent.answer_query(current_user.id, request.question, db, ai_client)
    return ChatResponse(
        answer=rec.answer,
        question=rec.question,
        created_at=rec.created_at,
    )


@router.get("/history", response_model=List[RecommendationResponse])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the 20 most recent Q&A pairs."""
    recs = recommendation_agent.get_chat_history(current_user.id, db)
    return [RecommendationResponse.model_validate(r) for r in recs]
