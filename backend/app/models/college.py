"""models/college.py — College directory model"""

from sqlalchemy import Column, Integer, String, Boolean, Index
from app.core.database import Base


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    college_name = Column(String(500), nullable=False, index=True)
    university = Column(String(500), nullable=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    college_type = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_colleges_name_state", "college_name", "state"),
    )

    def __repr__(self) -> str:
        return f"<College id={self.id} name={self.college_name!r} state={self.state!r}>"


class CollegeAlias(Base):
    __tablename__ = "college_aliases"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, nullable=False, index=True)
    alias = Column(String(200), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<CollegeAlias college_id={self.college_id} alias={self.alias!r}>"
