"""api/routes/reminders.py — Notification/Reminder endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_ai_client_dep
from app.core.database import get_db
from app.models.user import User
from app.agents import reminder_agent
from app.services.ai_client import AIInferenceClient
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=List[NotificationResponse])
def get_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all unread notifications for the current user."""
    notifications = reminder_agent.get_unread_notifications(current_user.id, db)
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.post("/check", response_model=List[NotificationResponse])
def trigger_reminder_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """Manually trigger reminder check for the current user (for demo purposes)."""
    created = reminder_agent.check_and_create_reminders(current_user.id, db, ai_client)
    return [NotificationResponse.model_validate(n) for n in created]


@router.put("/{notification_id}/read", response_model=dict)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    success = reminder_agent.mark_notification_read(notification_id, current_user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.put("/read-all", response_model=dict)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    from app.models.notification import Notification
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"success": True}
