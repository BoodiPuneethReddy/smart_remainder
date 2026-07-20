"""
agents/planner_agent.py — Planner Agent

Responsibilities:
1. Query all incomplete tasks for a user
2. Compute priority scores using scoring.py (pure math, no AI)
3. Persist updated scores to the database
4. Build daily and weekly study plans
5. Call ai_client.generate("explain_priority", context) for NL explanations

The AI is used ONLY for natural-language generation. All decisions are deterministic.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.study_session import StudySession
from app.services.scoring import (
    compute_priority,
    generate_explanation_template,
)
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)


def _get_sessions_for_user(user_id: int, db: Session) -> list[dict]:
    """Retrieve all study sessions as plain dicts for scoring."""
    sessions = db.query(StudySession).filter(StudySession.user_id == user_id).all()
    return [{"subject": s.subject, "task_completed": s.task_completed} for s in sessions]


def score_all_tasks(user_id: int, db: Session, ai_client: AIInferenceClient) -> list[Task]:
    """
    Compute and persist priority scores for all incomplete tasks.
    Returns tasks sorted descending by priority_score.
    """
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.is_completed == False)
        .all()
    )
    sessions = _get_sessions_for_user(user_id, db)

    for task in tasks:
        result = compute_priority(
            task_type=task.task_type,
            subject=task.subject,
            due_date=task.due_date,
            estimated_hours=task.estimated_hours,
            sessions=sessions,
        )

        # Persist scores
        task.priority_score = result["priority_score"]
        task.urgency_score = result["urgency_score"]
        task.importance_score = result["importance_score"]
        task.weakness_score = result["weakness_score"]
        task.effort_score = result["effort_score"]

        # Generate NL explanation via AI client
        # Build template explanation as fallback context
        template_explanation = generate_explanation_template(
            subject=task.subject,
            task_type=task.task_type,
            top_factors=result["top_factors"],
            days_remaining=result["days_remaining"],
            estimated_hours=task.estimated_hours,
        )

        try:
            ai_explanation = ai_client.generate(
                "explain_priority",
                {
                    "subject": task.subject,
                    "task_type": task.task_type,
                    "days_remaining": result["days_remaining"],
                    "estimated_hours": task.estimated_hours,
                    "top_factors": result["top_factors"],
                    "priority_score": result["priority_score"],
                    "urgency_score": result["urgency_score"],
                    "importance_score": result["importance_score"],
                    "weakness_score": result["weakness_score"],
                    "effort_score": result["effort_score"],
                    "template_suggestion": template_explanation,
                },
            )
            task.ai_explanation = ai_explanation or template_explanation
        except Exception as exc:
            logger.warning("Planner: AI explanation failed for task %d: %s", task.id, exc)
            task.ai_explanation = template_explanation

    db.commit()

    return sorted(tasks, key=lambda t: t.priority_score, reverse=True)


def build_daily_plan(user_id: int, db: Session, ai_client: AIInferenceClient) -> dict:
    """
    Build today's study plan — top tasks with time allocation.
    Returns structured dict suitable for the dashboard hero row.
    """
    tasks = score_all_tasks(user_id, db, ai_client)
    today = datetime.now(timezone.utc).date()

    plan_items = []
    total_minutes_available = 240  # 4 hours of study time daily
    minutes_allocated = 0

    for task in tasks[:5]:  # Top 5 only
        # Compute daily time allocation: spread remaining hours over remaining days
        due = task.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days_left = max(1, (due - datetime.now(timezone.utc)).days)
        daily_hours = min(task.estimated_hours, task.estimated_hours / days_left)
        daily_minutes = int(daily_hours * 60)
        daily_minutes = max(30, min(daily_minutes, 120))  # 30–120 min per task

        if minutes_allocated + daily_minutes > total_minutes_available:
            daily_minutes = total_minutes_available - minutes_allocated
            if daily_minutes < 15:
                break

        plan_items.append({
            "task_id": task.id,
            "title": task.title,
            "subject": task.subject,
            "task_type": task.task_type,
            "due_date": task.due_date.isoformat(),
            "priority_score": task.priority_score,
            "urgency_score": task.urgency_score,
            "importance_score": task.importance_score,
            "weakness_score": task.weakness_score,
            "effort_score": task.effort_score,
            "ai_explanation": task.ai_explanation,
            "recommended_minutes": daily_minutes,
        })
        minutes_allocated += daily_minutes

    return {
        "date": today.isoformat(),
        "total_recommended_minutes": minutes_allocated,
        "tasks": plan_items,
    }


def build_weekly_plan(user_id: int, db: Session, ai_client: AIInferenceClient) -> dict:
    """
    Build a 7-day study schedule distributing tasks across the week.
    """
    tasks = score_all_tasks(user_id, db, ai_client)
    now = datetime.now(timezone.utc)
    days_plan = {}

    for i in range(7):
        day = (now + timedelta(days=i)).date()
        days_plan[day.isoformat()] = []

    # Assign each task to its most relevant day(s)
    for task in tasks:
        due = task.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days_until_due = max(0, (due.date() - now.date()).days)

        # Study in the 2 days before due date (or today if due today/tomorrow)
        study_days = [max(0, days_until_due - 1), max(0, days_until_due - 2)]
        for day_offset in study_days:
            if day_offset < 7:
                day_key = (now + timedelta(days=day_offset)).date().isoformat()
                if day_key in days_plan:
                    days_plan[day_key].append({
                        "task_id": task.id,
                        "title": task.title,
                        "subject": task.subject,
                        "task_type": task.task_type,
                        "priority_score": task.priority_score,
                        "recommended_minutes": 60,
                    })

    return {
        "week_start": now.date().isoformat(),
        "days": days_plan,
    }
