from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class TutorSession(Base):
    """
    LearningSession Model — State store for dynamic academic tutoring sessions.
    Stores user selections, active document binding, extracted knowledge topics,
    and progress tracking.
    """
    __tablename__ = "tutor_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", back_populates="tutor_sessions")
    
    document_id = Column(Integer, ForeignKey("imported_documents.id", ondelete="SET NULL"), nullable=True, index=True)

    subject = Column(String, index=True, nullable=False)
    topic = Column(String, index=True, nullable=False)
    
    # 6 User Configuration Selections
    teacher_personality = Column(String, default="Socratic Tutor", nullable=False)
    target_goal = Column(String, default="General Learning", nullable=False)
    learning_mode = Column(String, default="Teach Me", nullable=False)
    assessment_type = Column(String, default="Mixed", nullable=False)
    difficulty_level = Column(Integer, default=1, nullable=False)
    difficulty_name = Column(String, default="Adaptive", nullable=False)
    session_length = Column(String, default="60 min", nullable=False)

    # Deterministic Concepts & Progress Tracking
    selected_topics = Column(JSON, nullable=True)        # Extracted topics list
    current_concept = Column(String, nullable=True)       # Active concept being taught
    remaining_concepts = Column(JSON, nullable=True)     # Concepts remaining in session
    weak_topics = Column(JSON, nullable=True)            # Weak topics requiring reinforcement

    # State Machine Columns
    current_state = Column(String, default="WAITING_FOR_ANSWER", nullable=True)
    current_topic_index = Column(Integer, default=0, nullable=True)
    current_question_text = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    score = Column(Float, default=0.0, nullable=True)
    attempts = Column(Integer, default=0, nullable=True)
    status = Column(String, default="active", nullable=True)

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
