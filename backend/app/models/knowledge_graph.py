"""
models/knowledge_graph.py — Grounded KnowledgeGraph & ConceptNode entities

Persists extracted multi-level knowledge hierarchies for uploaded documents.
Never recomputed on every request — indexed once and stored in SQLite.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class KnowledgeGraph(Base):
    """
    KnowledgeGraph Model — Container for extracted document knowledge hierarchy.
    """
    __tablename__ = "knowledge_graphs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("imported_documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    subject = Column(String(255), nullable=False, index=True)
    doc_type = Column(String(100), default="ACADEMIC", nullable=False)
    total_nodes = Column(Integer, default=0, nullable=False)
    features = Column(JSON, nullable=True)  # ["concepts", "code", "formulas", "sql", "diagrams"]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    nodes = relationship("ConceptNode", back_populates="graph", cascade="all, delete-orphan")


class ConceptNode(Base):
    """
    ConceptNode Model — Individual concept / topic node within a KnowledgeGraph.
    Contains rich ground-truth assets: definitions, examples, SQL/code, formulas,
    prerequisites, difficulty, and exam weight.
    """
    __tablename__ = "concept_nodes"

    id = Column(Integer, primary_key=True, index=True)
    graph_id = Column(Integer, ForeignKey("knowledge_graphs.id", ondelete="CASCADE"), nullable=False, index=True)

    node_key = Column(String(100), nullable=False, index=True)  # e.g., "node_1"
    title = Column(String(500), nullable=False, index=True)
    chapter = Column(String(200), default="Chapter 1", nullable=False)
    summary = Column(Text, nullable=False)

    definitions = Column(JSON, nullable=True)     # list of dicts or strings
    examples = Column(JSON, nullable=True)        # list of strings
    code_snippets = Column(JSON, nullable=True)   # list of code/SQL strings
    formulas = Column(JSON, nullable=True)        # list of formula strings

    difficulty = Column(Integer, default=3, nullable=False)        # 1 (Beginner) to 5 (Advanced)
    importance = Column(Float, default=0.75, nullable=False)        # 0.0 to 1.0 (Exam Weight)
    est_minutes = Column(Integer, default=15, nullable=False)      # Estimated learning minutes

    prerequisites = Column(JSON, nullable=True)  # list of prerequisite titles or keys
    children = Column(JSON, nullable=True)       # list of child concept keys

    exam_tips = Column(JSON, nullable=True)        # high yield exam hints
    common_mistakes = Column(JSON, nullable=True)  # student misconception warnings

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    graph = relationship("KnowledgeGraph", back_populates="nodes")
