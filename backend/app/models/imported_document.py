"""models/imported_document.py — ImportedDocument model

Stores metadata about uploaded documents.
Original files are preserved on disk at storage_path.
Tasks created from an import link back here via imported_from_id.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from app.core.database import Base


class ImportedDocument(Base):
    __tablename__ = "imported_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # File storage (original file is always preserved)
    original_filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=False)  # absolute path on disk
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)           # bytes

    # Extraction results
    extracted_text = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=True)    # assignment_notice | exam_schedule | timetable | mixed_academic | unknown_academic
    confidence_overall = Column(Float, nullable=True)    # 0–1

    # Lifecycle
    status = Column(String(30), default="pending_review", nullable=False)
    # pending_review | approved | rejected | partial

    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ImportedDocument id={self.id} type={self.document_type!r} status={self.status!r}>"
