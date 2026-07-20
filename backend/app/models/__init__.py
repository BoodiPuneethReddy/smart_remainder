"""
models/__init__.py — Import all models so SQLAlchemy can create all tables
from a single Base.metadata.create_all() call in database.py.
"""

from app.models.user import User
from app.models.task import Task
from app.models.study_session import StudySession
from app.models.notification import Notification
from app.models.recommendation import Recommendation

__all__ = ["User", "Task", "StudySession", "Notification", "Recommendation"]
