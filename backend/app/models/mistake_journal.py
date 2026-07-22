from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from app.core.database import Base


class MistakeJournal(Base):
    __tablename__ = "mistake_journal"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, index=True, nullable=False)
    topic = Column(String, index=True, nullable=False)
    question_text = Column(Text, nullable=False)
    student_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    mistakes_count = Column(Integer, default=1, nullable=False)
    last_attempt = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    revision_due = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
