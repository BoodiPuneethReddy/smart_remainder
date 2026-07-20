"""schemas/analytics.py — Analytics summary and chart data schemas."""

from typing import List, Dict, Any
from pydantic import BaseModel


class SubjectStat(BaseModel):
    subject: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    total_study_minutes: int
    avg_priority_score: float


class WeeklyDataPoint(BaseModel):
    date: str
    completed: int
    added: int
    study_minutes: int


class AnalyticsSummary(BaseModel):
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    total_study_minutes: int
    avg_priority_score: float
    subjects: List[SubjectStat]
    pending_by_type: Dict[str, int]
    streak_days: int


class WeeklyAnalytics(BaseModel):
    weekly_data: List[WeeklyDataPoint]
    total_this_week: int
    completed_this_week: int
