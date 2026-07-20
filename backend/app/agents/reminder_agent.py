"""
agents/reminder_agent.py — Reminder Agent

Responsibilities:
1. Find urgent tasks (due ≤ 48h or high priority score) — pure Python logic
2. Avoid duplicate notifications (check if one already exists for this task today)
3. Call ai_client.generate("reminder_message", context) for notification wording
4. Persist Notification records to the database

APScheduler calls check_and_create_reminders() on a configurable interval.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.notification import Notification
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)

# Urgency tiers — determines notification severity and wording
_TIER_CRITICAL = "critical"  # due today (≤ 0 days)
_TIER_HIGH = "high"          # due in ≤ 2 days
_TIER_MEDIUM = "medium"      # due in ≤ 4 days or priority ≥ 70


def _days_remaining(due_date: datetime) -> float:
    now = datetime.now(timezone.utc)
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    return (due_date - now).total_seconds() / 86400


def _get_urgency_tier(days: float, priority_score: float) -> str | None:
    """Return urgency tier string, or None if not urgent enough to notify."""
    if days <= 0:
        return _TIER_CRITICAL
    if days <= 2:
        return _TIER_HIGH
    if days <= 4 or priority_score >= 70:
        return _TIER_MEDIUM
    return None


def _already_notified_today(user_id: int, task_id: int, db: Session) -> bool:
    """Return True if a notification for this task was already created today."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.task_id == task_id,
            Notification.created_at >= today_start,
        )
        .first()
    )
    return existing is not None


def check_and_create_reminders(
    user_id: int,
    db: Session,
    ai_client: AIInferenceClient,
) -> list[Notification]:
    """
    Scan all incomplete tasks and create notifications for urgent ones.
    Returns a list of newly created notifications.
    """
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.is_completed == False)
        .all()
    )

    created = []
    for task in tasks:
        days = _days_remaining(task.due_date)
        tier = _get_urgency_tier(days, task.priority_score)

        if not tier:
            continue

        if _already_notified_today(user_id, task.id, db):
            continue

        # Build context for AI wording
        context = {
            "subject": task.subject,
            "task_type": task.task_type,
            "title": task.title,
            "days_remaining": round(days, 1),
            "estimated_hours": task.estimated_hours,
            "priority_score": task.priority_score,
            "urgency_tier": tier,
        }

        try:
            message = ai_client.generate("reminder_message", context)
        except Exception as exc:
            logger.warning("ReminderAgent: AI message failed for task %d: %s", task.id, exc)
            message = f"Reminder: {task.subject} {task.task_type} is due in {max(0, int(days))} day(s). Priority: {task.priority_score:.0f}/100."

        # Notification title based on tier
        tier_titles = {
            _TIER_CRITICAL: f"🚨 Due Today: {task.subject}",
            _TIER_HIGH: f"⚠️ Due Soon: {task.subject}",
            _TIER_MEDIUM: f"📅 Upcoming: {task.subject}",
        }

        notification = Notification(
            user_id=user_id,
            task_id=task.id,
            urgency_tier=tier,
            title=tier_titles[tier],
            message=message,
        )
        db.add(notification)
        created.append(notification)
        logger.info(
            "ReminderAgent: created %s notification for task %d ('%s')",
            tier, task.id, task.title,
        )

    if created:
        db.commit()
        for n in created:
            db.refresh(n)

    return created


def get_unread_notifications(user_id: int, db: Session) -> list[Notification]:
    """Return all unread notifications for a user, newest first."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_notification_read(notification_id: int, user_id: int, db: Session) -> bool:
    """Mark a notification as read. Returns True if found and updated."""
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not n:
        return False
    n.is_read = True
    db.commit()
    return True
