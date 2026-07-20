"""
agents/recommendation_agent.py — Recommendation Agent

Responsibilities:
1. Retrieve stored task and session data for the user (deterministic, pure Python)
2. Compute context: top tasks, completion rates, weakest subjects
3. Call ai_client.generate("chat_answer", context) to produce the NL answer
4. Persist the Q&A to the Recommendations table

The retrieval and analysis logic is local — only the final wording goes through ai_client.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.study_session import StudySession
from app.models.recommendation import Recommendation
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)


def _compute_completion_rate(user_id: int, db: Session) -> float:
    """Overall task completion rate for the user, 0–100."""
    total = db.query(Task).filter(Task.user_id == user_id).count()
    if total == 0:
        return 0.0
    completed = db.query(Task).filter(
        Task.user_id == user_id, Task.is_completed == True
    ).count()
    return round((completed / total) * 100, 1)


def _get_weakest_subject(user_id: int, db: Session) -> tuple[str, float]:
    """Return (subject, completion_rate%) for the subject with lowest completion rate."""
    sessions = db.query(StudySession).filter(StudySession.user_id == user_id).all()

    subject_stats: dict[str, dict] = {}
    for s in sessions:
        if s.subject not in subject_stats:
            subject_stats[s.subject] = {"total": 0, "completed": 0}
        subject_stats[s.subject]["total"] += 1
        subject_stats[s.subject]["completed"] += s.task_completed

    if not subject_stats:
        return ("", 0.0)

    weakest = min(
        subject_stats,
        key=lambda s: subject_stats[s]["completed"] / max(subject_stats[s]["total"], 1),
    )
    stats = subject_stats[weakest]
    rate = round((stats["completed"] / max(stats["total"], 1)) * 100, 1)
    return (weakest, rate)


def answer_query(
    user_id: int,
    question: str,
    db: Session,
    ai_client: AIInferenceClient,
) -> Recommendation:
    """
    Process a student's question and return an AI-generated answer
    grounded in their actual academic data.
    """
    # ── Deterministic data retrieval ──────────────────────────────────────────
    pending_tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.is_completed == False)
        .order_by(Task.priority_score.desc())
        .all()
    )

    completion_rate = _compute_completion_rate(user_id, db)
    weakest_subject, weakest_rate = _get_weakest_subject(user_id, db)

    # Build task context dicts
    task_contexts = []
    for t in pending_tasks[:8]:
        due = t.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days_left = (due - datetime.now(timezone.utc)).total_seconds() / 86400
        task_contexts.append({
            "id": t.id,
            "title": t.title,
            "subject": t.subject,
            "task_type": t.task_type,
            "due_date": t.due_date.isoformat(),
            "estimated_hours": t.estimated_hours,
            "priority_score": t.priority_score,
            "urgency_score": t.urgency_score,
            "importance_score": t.importance_score,
            "weakness_score": t.weakness_score,
            "effort_score": t.effort_score,
            "days_remaining": round(days_left, 1),
            "ai_explanation": t.ai_explanation,
        })

    # ── AI call for NL answer ──────────────────────────────────────────────────
    context = {
        "question": question,
        "tasks": task_contexts,
        "completion_rate": completion_rate,
        "weakest_subject": weakest_subject,
        "weakest_rate": weakest_rate,
        "pending_count": len(pending_tasks),
    }

    try:
        answer = ai_client.generate("chat_answer", context)
    except Exception as exc:
        logger.warning("RecommendationAgent: AI call failed: %s", exc)
        top = task_contexts[0] if task_contexts else {}
        answer = (
            f"Based on your current tasks, I recommend focusing on "
            f"**{top.get('subject', 'your highest priority subject')}** first "
            f"(priority score: {top.get('priority_score', 0):.0f}/100)."
        )

    # ── Persist Q&A ───────────────────────────────────────────────────────────
    rec = Recommendation(
        user_id=user_id,
        question=question,
        answer=answer,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    logger.info("RecommendationAgent: answered question for user %d", user_id)
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
