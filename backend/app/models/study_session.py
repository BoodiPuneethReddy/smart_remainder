"""
models/study_session.py — Records completed study sessions per subject.
Used by the Planner Agent to compute historical completion rates (weakness scores).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from app.core.database import Base


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=60)
    # Was the associated task completed in this session?
    task_completed = Column(Integer, default=1)  # 1 = completed, 0 = incomplete
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
