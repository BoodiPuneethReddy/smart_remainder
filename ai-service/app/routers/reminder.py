from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter(prefix="/reminder", tags=["reminder"])

class ReminderRequest(BaseModel):
    subject: str
    task_type: str
    days_remaining: float
    priority_score: float
    estimated_hours: float

class ReminderResponse(BaseModel):
    urgency_tier: str
    message: str
    recommended_action: str

@router.post("", response_model=ReminderResponse)
def compute_reminder(request: ReminderRequest):
    if request.days_remaining <= 1:
        tier = "critical"
        msg = f"🚨 **Urgent: {request.subject} {request.task_type} due TODAY!** Priority score: {request.priority_score:.0f}/100."
        action = "Start immediately with 25-minute Pomodoro blocks."
    elif request.days_remaining <= 3:
        tier = "high"
        msg = f"⚠️ **{request.subject} {request.task_type} due in {int(request.days_remaining)} days.** Priority {request.priority_score:.0f}/100."
        action = f"Plan {request.estimated_hours / 2:.1f}h of study today."
    else:
        tier = "medium"
        msg = f"📅 **Heads up: {request.subject} {request.task_type} in {int(request.days_remaining)} days.**"
        action = "Schedule a short review block."

    return ReminderResponse(
        urgency_tier=tier,
        message=msg,
        recommended_action=action
    )
