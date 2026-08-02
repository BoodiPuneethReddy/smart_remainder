"""api/routes/chat.py — Orchestrator-powered chat endpoint with full pipeline transparency."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_current_user, get_ai_client_dep
from app.core.database import get_db
from app.models.user import User
from app.agents import recommendation_agent
from app.services.ai_client import AIInferenceClient
from app.schemas.recommendation import ChatRequest, ChatResponse, RecommendationResponse, StepLogSchema
from datetime import timezone

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """
    Submit a study question and receive a full context-aware response.
    Returns: answer, primary_intent, and agent step_logs for pipeline visualization.
    """
    rec, step_logs, primary_intent = recommendation_agent.answer_query(
        user_id=current_user.id,
        question=request.question,
        db=db,
        ai_client=ai_client,
        document_id=request.document_id,
    )
    return ChatResponse(
        answer=rec.answer,
        question=rec.question,
        created_at=rec.created_at,
        primary_intent=primary_intent,
        step_logs=[StepLogSchema(**log) for log in step_logs],
    )


@router.get("/history", response_model=List[RecommendationResponse])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the 20 most recent Q&A pairs."""
    recs = recommendation_agent.get_chat_history(current_user.id, db)
    return [RecommendationResponse.model_validate(r) for r in recs]
