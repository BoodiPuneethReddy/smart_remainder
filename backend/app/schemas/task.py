"""schemas/task.py — Pydantic schemas for Task CRUD and responses."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


VALID_TASK_TYPES = {"exam", "assignment", "project", "quiz", "homework", "reading"}


class TaskCreate(BaseModel):
    title: str
    subject: str
    description: Optional[str] = ""
    task_type: str = "assignment"
    due_date: datetime
    estimated_hours: float = 2.0
    exam_room: Optional[str] = None
    exam_duration_minutes: Optional[int] = None
    grade_weight: Optional[float] = None

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: str) -> str:
        if v not in VALID_TASK_TYPES:
            raise ValueError(f"task_type must be one of: {VALID_TASK_TYPES}")
        return v

    @field_validator("estimated_hours")
    @classmethod
    def validate_hours(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("estimated_hours must be positive")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    is_completed: Optional[bool] = None
    exam_room: Optional[str] = None
    exam_duration_minutes: Optional[int] = None
    grade_weight: Optional[float] = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    subject: str
    description: str
    task_type: str
    due_date: datetime
    estimated_hours: float
    is_completed: bool
    completed_at: Optional[datetime] = None
    priority_score: float
    urgency_score: float
    importance_score: float
    weakness_score: float
    effort_score: float
    ai_explanation: str
    created_at: datetime
    exam_room: Optional[str] = None
    exam_duration_minutes: Optional[int] = None
    grade_weight: Optional[float] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
