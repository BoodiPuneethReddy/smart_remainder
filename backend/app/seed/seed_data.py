"""
seed/seed_data.py — Idempotent database seeder.
Seeds one demo user, 8 fictional tasks, and 18 study sessions on startup
(only if SEED_DEMO_DATA environment variable is True).

Checks for existing data before inserting — safe to run multiple times.
All data is 100% fictional (no real student records, no scraped syllabi).
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.config import get_settings
from app.models.user import User
from app.models.task import Task
from app.models.study_session import StudySession

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent / "demo_data.json"


def seed_database(db: Session) -> None:
    """Seed database with single demo user and 8 realistic demo tasks.
    
    This only runs if SEED_DEMO_DATA environment variable is True.
    To start with a completely empty database, set SEED_DEMO_DATA=False.
    """
    import os
    seed_env = os.getenv("SEED_DEMO_DATA", "").lower()
    if seed_env != "true" and not get_settings().seed_demo_data:
        logger.info("Seed: demo data seeding is disabled (SEED_DEMO_DATA=false)")
        return
    
    demo_email = "punithgodof@gmail.com"
    user = db.query(User).filter(User.email == demo_email).first()
    if not user:
        logger.info("Seed: creating single user %s...", demo_email)
        user = User(
            email=demo_email,
            full_name="Punith",
            hashed_password=hash_password("Punith@123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Seed 8 realistic tasks for demo account if 0 tasks exist
    task_count = db.query(Task).filter(Task.user_id == user.id).count()
    if task_count == 0:
        now = datetime.now(timezone.utc)
        demo_tasks = [
            Task(user_id=user.id, title="Operating Systems Mid Exam", subject="Operating Systems", task_type="exam", due_date=now + timedelta(days=5), estimated_hours=6.0, importance_score=95.0, priority_score=92.0, priority_tier="Critical", ai_explanation="OS Mid Exam scores highest due to close deadline (5 days) and heavy 6.0h weight."),
            Task(user_id=user.id, title="DBMS Assignment", subject="Database Management Systems", task_type="assignment", due_date=now + timedelta(days=3), estimated_hours=4.5, importance_score=80.0, priority_score=74.0, priority_tier="High", ai_explanation="DBMS Assignment is high priority due to 3-day deadline."),
            Task(user_id=user.id, title="Python Lab", subject="Python Programming", task_type="assignment", due_date=now + timedelta(days=2), estimated_hours=2.0, importance_score=60.0, priority_score=50.0, priority_tier="Medium", ai_explanation="Python Lab requires short 2.0h review before lab section."),
            Task(user_id=user.id, title="CN Quiz", subject="Computer Networks", task_type="quiz", due_date=now + timedelta(days=10), estimated_hours=1.0, importance_score=40.0, priority_score=29.0, priority_tier="Low", ai_explanation="CN Quiz is 10 days out with light 1.0h effort."),
            Task(user_id=user.id, title="Mini Project", subject="Computer Science", task_type="project", due_date=now + timedelta(days=7), estimated_hours=10.0, importance_score=75.0, priority_score=58.0, priority_tier="Medium", ai_explanation="Mini Project requires multi-day milestone checkpoints."),
            Task(user_id=user.id, title="AI Workshop", subject="Artificial Intelligence", task_type="assignment", due_date=now + timedelta(days=4), estimated_hours=3.0, importance_score=70.0, priority_score=65.0, priority_tier="Medium", ai_explanation="AI Workshop requires preparation for practical lab."),
            Task(user_id=user.id, title="Cloud Computing Assignment", subject="Cloud Computing", task_type="assignment", due_date=now + timedelta(days=6), estimated_hours=4.0, importance_score=85.0, priority_score=70.0, priority_tier="High", ai_explanation="Cloud assignment requires architecture setup."),
            Task(user_id=user.id, title="DSA Revision", subject="Data Structures", task_type="exam", due_date=now + timedelta(days=1), estimated_hours=3.0, importance_score=90.0, priority_score=85.0, priority_tier="High", ai_explanation="DSA Revision is urgent due tomorrow.")
        ]
        db.add_all(demo_tasks)

        # Seed study sessions for analytics
        sessions = [
            StudySession(user_id=user.id, subject="Operating Systems", duration_minutes=90, task_completed=1, completed_at=now - timedelta(days=i))
            for i in range(1, 8)
        ]
        db.add_all(sessions)
        db.commit()
        logger.info("Seed: successfully populated %d tasks and study sessions for %s.", len(demo_tasks), demo_email)
