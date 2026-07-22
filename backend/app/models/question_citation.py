"""
models/question_citation.py — Stores source traceability information for generated questions.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.core.database import Base


class QuestionCitation(Base):
    __tablename__ = "question_citations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    subject = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON-encoded array of strings
    correct_answer = Column(String, nullable=False)
    
    # Document citation tracking
    document_id = Column(Integer, ForeignKey("imported_documents.id"), nullable=True)
    chunk_id = Column(String, nullable=True)
    page_range = Column(String, nullable=True)
    retrieved_context = Column(Text, nullable=True)
    generated_rubric = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
