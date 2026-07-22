"""
models/learning_profile.py — Stores topic-specific learning metrics and memory status.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from app.core.database import Base


class LearningProfile(Base):
    __tablename__ = "learning_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    subject = Column(String, nullable=False, index=True)
    topic = Column(String, nullable=False, index=True)
    
    # Mastery score (0-100%)
    mastery = Column(Float, default=50.0)
    
    # Confidence score (0-100%)
    confidence = Column(Float, default=50.0)
    
    # Current memory retention percentage (0-100%)
    retention = Column(Float, default=100.0)
    
    # Assessment tracking
    avg_quiz_score = Column(Float, default=0.0)
    attempts_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    
    # Study duration tracking
    study_hours = Column(Float, default=0.0)
    
    # Spaced repetition scheduler details
    last_revision = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    revision_count = Column(Integer, default=0)
    learning_streak = Column(Integer, default=0)
    interval_days = Column(Integer, default=1)  # 1, 3, 7, 14, or 30 days

    # Socratic Journey & Preferences
    difficulty_level = Column(Integer, default=1, nullable=False)
    struggled_concepts = Column(String, nullable=True)  # JSON-encoded array of sub-topics
    preferred_explanation_style = Column(String, default="concise", nullable=False)
    prefers_diagrams = Column(Integer, default=0, nullable=False)  # 0=False, 1=True for SQLite compatibility
    learning_pace = Column(String, default="normal", nullable=False)
