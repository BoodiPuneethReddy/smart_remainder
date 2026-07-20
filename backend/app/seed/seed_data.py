"""
seed/seed_data.py — Idempotent database seeder.
Seeds one demo user, 8 fictional tasks, and 18 study sessions on startup.
Checks for existing data before inserting — safe to run multiple times.
All data is 100% fictional (no real student records, no scraped syllabi).
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.models.task import Task
from app.models.study_session import StudySession

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent / "demo_data.json"


def seed_database(db: Session) -> None:
    """Seed the database with demo data. Idempotent — skips if already seeded."""
    data = json.loads(_DATA_FILE.read_text())

    # Check if demo user already exists
    demo_email = data["demo_user"]["email"]
    existing = db.query(User).filter(User.email == demo_email).first()
    if existing:
        logger.info("Seed: demo user %s already exists — skipping seed.", demo_email)
        return

    logger.info("Seed: creating demo user and academic data...")

    # ── Create demo user ──────────────────────────────────────────────────────
    user = User(
        email=demo_email,
        full_name=data["demo_user"]["full_name"],
        hashed_password=hash_password(data["demo_user"]["password"]),
    )
    db.add(user)
    db.flush()  # get user.id without committing

    now = datetime.now(timezone.utc)

    # ── Create tasks ──────────────────────────────────────────────────────────
    for task_data in data["tasks"]:
        days_offset = task_data.pop("due_days_from_now")
        due = now + timedelta(days=days_offset)

        task = Task(
            user_id=user.id,
            due_date=due,
            **{k: v for k, v in task_data.items()},
        )
        db.add(task)

    # ── Create study sessions ─────────────────────────────────────────────────
    for session_data in data["study_sessions"]:
        days_ago = session_data.pop("days_ago")
        completed_at = now - timedelta(days=days_ago)

        session = StudySession(
            user_id=user.id,
            completed_at=completed_at,
            **session_data,
        )
        db.add(session)

    db.commit()
    logger.info(
        "Seed: created demo user '%s' with %d tasks and %d study sessions.",
        demo_email,
        len(data["tasks"]),
        len(data["study_sessions"]),
    )
