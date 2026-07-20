"""
services/scheduler.py — APScheduler setup for periodic reminder checks.

Polls all active users' tasks every REMINDER_POLL_INTERVAL seconds.
Only creates notifications for tasks meeting urgency thresholds.
Started via FastAPI lifespan; stopped cleanly on shutdown.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User
from app.agents.reminder_agent import check_and_create_reminders
from app.services.ai_client import get_ai_client

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")
_ai_client = None  # initialized at startup


def _poll_reminders() -> None:
    """Called by APScheduler every N seconds. Creates notifications for urgent tasks."""
    global _ai_client
    if _ai_client is None:
        _ai_client = get_ai_client()

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            created = check_and_create_reminders(user.id, db, _ai_client)
            if created:
                logger.info(
                    "Scheduler: created %d reminder(s) for user %d", len(created), user.id
                )
    except Exception as exc:
        logger.error("Scheduler: poll_reminders failed: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler. Called on app startup."""
    global _ai_client
    _ai_client = get_ai_client()

    settings = get_settings()
    interval = settings.reminder_poll_interval

    _scheduler.add_job(
        _poll_reminders,
        trigger=IntervalTrigger(seconds=interval),
        id="reminder_poll",
        replace_existing=True,
        max_instances=1,  # never run two polls concurrently
    )
    _scheduler.start()
    logger.info("Scheduler: started reminder polling every %ds", interval)


def stop_scheduler() -> None:
    """Gracefully stop the scheduler. Called on app shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler: stopped")
