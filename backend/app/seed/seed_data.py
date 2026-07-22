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
    """Seed the database with the single account punithgodof@gmail.com. Idempotent — skips if user exists."""
    demo_email = "punithgodof@gmail.com"
    existing = db.query(User).filter(User.email == demo_email).first()
    if existing:
        logger.info("Seed: user %s already exists — skipping seed.", demo_email)
        return

    logger.info("Seed: creating single user %s...", demo_email)

    user = User(
        email=demo_email,
        full_name="Punith",
        hashed_password=hash_password("Punith@123"),
    )
    db.add(user)
    db.commit()
    logger.info("Seed: created single user '%s' with zero tasks and zero study sessions.", demo_email)
