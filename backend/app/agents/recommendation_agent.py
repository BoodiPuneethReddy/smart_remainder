"""
agents/recommendation_agent.py — Pure Compatibility Facade for Orchestrator Agent.

All orchestration logic, decision making, and workflow coordination have been removed.
This facade immediately delegates 100% of user queries to the OrchestratorAgent swarm.
"""

from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.services.ai_client import AIInferenceClient
from app.agents.orchestrator import execute_swarm_workflow
from app.agents.session_state import update_session

logger = logging.getLogger(__name__)


def answer_query(
    user_id: int,
    question: str,
    db: Session,
    ai_client: AIInferenceClient,
    document_id: Optional[int] = None,
) -> Recommendation:
    """
    Facade entry point — immediately delegates execution to OrchestratorAgent.
    No legacy conditional routing, no canned fallbacks, no manual chatbot rules.
    """
    logger.info("RecommendationAgent Facade: delegating user=%d query to OrchestratorAgent", user_id)

    # Delegate 100% of execution to OrchestratorAgent swarm
    swarm_result = execute_swarm_workflow(
        user_id=user_id,
        user_query=question,
        db=db,
        ai_client=ai_client,
        document_id=document_id,
    )

    answer = swarm_result.formatted_response or "Your dynamic AI study workspace is ready."

    update_session(user_id, last_intent=swarm_result.primary_intent)

    # Persist Q&A
    rec = Recommendation(user_id=user_id, question=question, answer=answer)
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return rec


def get_chat_history(user_id: int, db: Session, limit: int = 20) -> list[Recommendation]:
    """Return the N most recent Q&A pairs for the user."""
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
