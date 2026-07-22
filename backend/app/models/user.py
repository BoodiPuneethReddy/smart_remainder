"""
models/user.py — User account model.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Extended profile fields (added for auth enhancement)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    college_rel = relationship("College", foreign_keys=[college_id], lazy="joined")

    @property
    def college(self) -> str:
        if self.college_rel:
            return self.college_rel.college_name
        return "SVCE"
