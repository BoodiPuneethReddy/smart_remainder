"""api/routes/analytics.py — Analytics data for dashboard charts."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.task import Task
from app.models.study_session import StudySession
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary, SubjectStat, WeeklyAnalytics, WeeklyDataPoint

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id
    all_tasks = db.query(Task).filter(Task.user_id == uid).all()
    all_sessions = db.query(StudySession).filter(StudySession.user_id == uid).all()

    total = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.is_completed)
    completion_rate = round((completed / total * 100) if total else 0, 1)

    total_study_minutes = sum(s.duration_minutes for s in all_sessions)
    avg_priority = round(
        sum(t.priority_score for t in all_tasks if not t.is_completed) /
        max(1, sum(1 for t in all_tasks if not t.is_completed)), 1
    )

    # Per-subject stats
    subject_tasks: Dict[str, list] = defaultdict(list)
    for t in all_tasks:
        subject_tasks[t.subject].append(t)

    subject_sessions: Dict[str, list] = defaultdict(list)
    for s in all_sessions:
        subject_sessions[s.subject].append(s)

    subjects = []
    for subj, tasks in subject_tasks.items():
        s_completed = sum(1 for t in tasks if t.is_completed)
        s_total = len(tasks)
        s_rate = round((s_completed / s_total * 100) if s_total else 0, 1)
        s_minutes = sum(s.duration_minutes for s in subject_sessions.get(subj, []))
        s_avg_priority = round(
            sum(t.priority_score for t in tasks) / max(1, len(tasks)), 1
        )
        subjects.append(SubjectStat(
            subject=subj,
            total_tasks=s_total,
            completed_tasks=s_completed,
            completion_rate=s_rate,
            total_study_minutes=s_minutes,
            avg_priority_score=s_avg_priority,
        ))
    subjects.sort(key=lambda s: s.avg_priority_score, reverse=True)

    # Pending by type
    pending_by_type: Dict[str, int] = defaultdict(int)
    for t in all_tasks:
        if not t.is_completed:
            pending_by_type[t.task_type] += 1

    # Streak: count consecutive days with at least one completed task
    today = datetime.now(timezone.utc).date()
    streak = 0
    for i in range(30):
        day = today - timedelta(days=i)
        day_sessions = [
            s for s in all_sessions
            if s.completed_at.date() == day and s.task_completed == 1
        ]
        if day_sessions:
            streak += 1
        else:
            break

    return AnalyticsSummary(
        total_tasks=total,
        completed_tasks=completed,
        completion_rate=completion_rate,
        total_study_minutes=total_study_minutes,
        avg_priority_score=avg_priority,
        subjects=subjects,
        pending_by_type=dict(pending_by_type),
        streak_days=streak,
    )


@router.get("/weekly", response_model=WeeklyAnalytics)
def get_weekly(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    all_tasks = db.query(Task).filter(Task.user_id == uid).all()
    all_sessions = db.query(StudySession).filter(
        StudySession.user_id == uid,
        StudySession.completed_at >= week_ago,
    ).all()

    weekly_data = []
    total_this_week = 0
    completed_this_week = 0

    for i in range(7):
        day = (now - timedelta(days=6 - i)).date()
        day_sessions = [s for s in all_sessions if s.completed_at.date() == day]
        day_completed = sum(1 for s in day_sessions if s.task_completed == 1)
        day_added = sum(1 for t in all_tasks if t.created_at.date() == day)
        day_minutes = sum(s.duration_minutes for s in day_sessions)

        weekly_data.append(WeeklyDataPoint(
            date=day.isoformat(),
            completed=day_completed,
            added=day_added,
            study_minutes=day_minutes,
        ))
        completed_this_week += day_completed
        total_this_week += day_added

    return WeeklyAnalytics(
        weekly_data=weekly_data,
        total_this_week=total_this_week,
        completed_this_week=completed_this_week,
    )


@router.get("/telemetry/latest")
def get_latest_telemetry(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.telemetry_log import SwarmTelemetryLog
    log_item = db.query(SwarmTelemetryLog).filter(
        SwarmTelemetryLog.user_id == current_user.id
    ).order_by(SwarmTelemetryLog.created_at.desc()).first()

    if not log_item:
        return {"status": "empty", "message": "No telemetry logs recorded yet."}

    return {
        "id": log_item.id,
        "query": log_item.query,
        "intent": log_item.intent,
        "subject": log_item.subject,
        "active_agents": log_item.active_agents,
        "skipped_agents": log_item.skipped_agents,
        "total_latency_ms": log_item.total_latency_ms,
        "dynamic_confidence": log_item.dynamic_confidence,
        "memory_before": log_item.memory_before,
        "memory_after": log_item.memory_after,
        "step_logs": log_item.step_logs,
        "reflection_audit": log_item.reflection_audit,
        "planner_output": log_item.planner_output,
        "grounding_report": log_item.grounding_report,
        "retrieved_nodes": log_item.retrieved_nodes,
        "exact_prompt": log_item.exact_prompt,
        "raw_gemini_output": log_item.raw_gemini_output,
        "final_response": log_item.final_response,
        "created_at": log_item.created_at.isoformat()
    }


@router.get("/knowledge-graph")
def get_knowledge_graph():
    from app.agents.retrieval_agent import _create_dbms_normalization_graph
    kg = _create_dbms_normalization_graph()
    return {
        "subject": kg.subject,
        "concepts": [c.model_dump() for c in kg.concepts],
        "prerequisite_edges": kg.prerequisite_edges
    }
