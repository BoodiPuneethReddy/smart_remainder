"""
agents/analytics_agent.py — Analytics Agent.

Provides study analytics, workload predictions, and burnout risk signals.
  - completion rate calculation
  - burnout risk detection (overwork vs completion ratio)
  - predicted exam readiness score
"""

from __future__ import annotations

import logging
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from app.agents.models import AnalyticsInsightModel
from app.models.study_session import StudySession
from app.models.task import Task

logger = logging.getLogger(__name__)


def generate_analytics_summary(user_id: int, db: Session) -> AnalyticsInsightModel:
    """Computes workload, burnout risk level, and predicted readiness."""
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    sessions = db.query(StudySession).filter(StudySession.user_id == user_id).all()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.is_completed)
    completion_rate = round((completed_tasks / total_tasks * 100.0), 1) if total_tasks > 0 else 100.0

    total_hours = sum(s.duration_minutes for s in sessions) / 60.0 if sessions else 0.0

    # Burnout risk calculation
    if total_hours > 35.0 and completion_rate < 50.0:
        burnout = "high"
        burnout_msg = "High burnout risk detected — high study volume with lagging completion rate."
    elif total_hours > 25.0:
        burnout = "moderate"
        burnout_msg = "Moderate workload — maintain regular rest intervals."
    else:
        burnout = "low"
        burnout_msg = "Balanced workload — healthy study pace detected."

    readiness = min(100.0, round(completion_rate * 0.6 + min(40.0, total_hours * 2.0), 1))

    return AnalyticsInsightModel(
        user_id=user_id,
        completion_rate=completion_rate,
        weekly_study_hours=round(total_hours, 1),
        burnout_risk_level=burnout,
        predicted_exam_readiness=readiness,
        weakest_subject="DBMS" if not tasks else tasks[0].subject,
        insights=[burnout_msg, f"Overall completion rate is {completion_rate}%."],
    )
