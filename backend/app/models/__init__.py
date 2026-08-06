"""
models/__init__.py — Import all models so SQLAlchemy can create all tables
from a single Base.metadata.create_all() call in database.py.
"""

from app.models.user import User
from app.models.task import Task
from app.models.study_session import StudySession
from app.models.notification import Notification
from app.models.recommendation import Recommendation
from app.models.college import College, CollegeAlias
from app.models.otp_code import OTPCode
from app.models.imported_document import ImportedDocument
from app.models.learning_profile import LearningProfile
from app.models.question_citation import QuestionCitation
from app.models.tutor_session import TutorSession, TutorMessage, TutorMessageChunk
from app.models.learning_objective import LearningObjective
from app.models.tutor_bookmark import TutorBookmark
from app.models.mistake_journal import MistakeJournal
from app.models.study_note import StudyNote
from app.models.telemetry_log import SwarmTelemetryLog

__all__ = [
    "User", "Task", "StudySession", "Notification", "Recommendation",
    "College", "CollegeAlias", "OTPCode", "ImportedDocument",
    "LearningProfile", "QuestionCitation", "TutorSession", 
    "TutorMessage", "TutorMessageChunk", "LearningObjective", "TutorBookmark",
    "MistakeJournal", "StudyNote", "SwarmTelemetryLog",
]
