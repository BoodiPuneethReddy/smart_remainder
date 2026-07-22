"""
models/task.py — Core Task model.
All assignment and exam types are stored here with a task_type discriminator.
This avoids complex joined-table inheritance for a hackathon demo while keeping
the data model clean and queryable.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, ForeignKey
)

from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ── Core fields ───────────────────────────────────────────────────────────
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, default="")

    # One of: "exam", "assignment", "project", "quiz", "homework", "reading"
    task_type = Column(String, nullable=False, default="assignment")

    due_date = Column(DateTime, nullable=False)
    estimated_hours = Column(Float, default=2.0)

    # ── Completion ────────────────────────────────────────────────────────────
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # ── AI-computed priority ──────────────────────────────────────────────────
    priority_score = Column(Float, default=0.0)       # 0–100
    urgency_score = Column(Float, default=0.0)        # 0–10
    importance_score = Column(Float, default=0.0)     # 0–10
    weakness_score = Column(Float, default=0.0)       # 0–10
    effort_score = Column(Float, default=0.0)         # 0–10
    ai_explanation = Column(Text, default="")

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # ── Exam-specific (nullable for non-exam tasks) ───────────────────────────
    exam_room = Column(String, nullable=True)
    exam_duration_minutes = Column(Integer, nullable=True)

    # ── Assignment-specific ───────────────────────────────────────────────────
    grade_weight = Column(Float, nullable=True)  # % of final grade

    # ── Document Import traceability (View Source) ────────────────────────────
    # Set when this task was created via the Smart Academic Import System.
    # Enables 'View Source' to open the original uploaded document.
    imported_from_id = Column(Integer, ForeignKey("imported_documents.id"), nullable=True)
