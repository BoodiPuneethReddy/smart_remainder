"""
schemas/__init__.py — Export all Pydantic schemas.
"""

from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from app.schemas.notification import NotificationResponse
from app.schemas.recommendation import RecommendationResponse, ChatRequest, ChatResponse
from app.schemas.analytics import AnalyticsSummary, WeeklyAnalytics

__all__ = [
    "UserCreate", "UserResponse", "UserLogin", "Token",
    "TaskCreate", "TaskUpdate", "TaskResponse", "TaskListResponse",
    "NotificationResponse",
    "RecommendationResponse", "ChatRequest", "ChatResponse",
    "AnalyticsSummary", "WeeklyAnalytics",
]
