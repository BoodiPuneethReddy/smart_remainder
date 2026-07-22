from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class TutorSession(Base):
    __tablename__ = "tutor_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, index=True, nullable=False)
    topic = Column(String, index=True, nullable=False)
    difficulty_level = Column(Integer, default=1, nullable=False)  # 1-6 levels
    assessment_type = Column(String, default="mixed", nullable=False)  # mcq, short_answer, etc.
    target_goal = Column(String, default="General Learning", nullable=False)
    teacher_personality = Column(String, default="Socratic Tutor", nullable=False)
    learning_mode = Column(String, default="Mixed", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    messages = relationship("TutorMessage", back_populates="session", cascade="all, delete-orphan")


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    evaluation_confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("TutorSession", back_populates="messages")
    chunks = relationship("TutorMessageChunk", back_populates="message", cascade="all, delete-orphan")


class TutorMessageChunk(Base):
    __tablename__ = "tutor_message_chunks"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("tutor_messages.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(Integer, nullable=False)
    document_name = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    paragraph_number = Column(Integer, default=1, nullable=True)
    lecture_name = Column(String, nullable=True)

    message = relationship("TutorMessage", back_populates="chunks")
