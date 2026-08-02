"""
agents/recommendation_agent.py — Pure Compatibility Facade for Orchestrator Agent.

Delegates 100% of execution to OrchestratorAgent swarm.
Returns answer + step_logs for full pipeline transparency.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, List
from datetime import datetime, timezone
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
) -> Tuple[Recommendation, List[dict], str]:
    """
    Facade entry point — delegates 100% to OrchestratorAgent swarm.
    Returns: (Recommendation record, step_logs as dicts, primary_intent)
    """
    logger.info("RecommendationAgent: user=%d query=%r", user_id, question)

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
    rec = Recommendation(
        user_id=user_id,
        question=question,
        answer=answer,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Convert step_logs to plain dicts for serialization
    step_logs_dicts = [
        {
            "agent_name": log.agent_name,
            "status": log.status,
            "summary": log.summary,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in swarm_result.step_logs
    ]

    return rec, step_logs_dicts, swarm_result.primary_intent


def get_chat_history(user_id: int, db: Session, limit: int = 20) -> list[Recommendation]:
    """Return the N most recent Q&A pairs for the user."""
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
