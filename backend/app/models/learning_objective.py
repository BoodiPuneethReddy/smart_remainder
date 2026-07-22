from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class LearningObjective(Base):
    __tablename__ = "learning_objectives"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, index=True, nullable=False)
    topic = Column(String, index=True, nullable=False)
    objective_text = Column(String, nullable=False)
    priority_stars = Column(Integer, default=3, nullable=False)  # 1 to 5 stars
    is_mastered = Column(Boolean, default=False, nullable=False)
