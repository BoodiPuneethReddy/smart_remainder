"""
agents/models.py — Strongly typed Pydantic models for multi-agent communication.
All agents exchange typed data models — never raw un-typed string blobs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# ─── Knowledge Graph Models (DocumentAgent) ───────────────────────────────────

class ConceptNode(BaseModel):
    id: str
    title: str
    chapter: str
    summary: str
    difficulty: int = Field(default=1, ge=1, le=6)
    prerequisites: List[str] = Field(default_factory=list)
    has_code: bool = False
    has_formulas: bool = False
    formulas: List[str] = Field(default_factory=list)
    code_snippets: List[str] = Field(default_factory=list)


class KnowledgeGraphModel(BaseModel):
    document_id: Optional[int] = None
    subject: str = "General Studies"
    doc_type: str = "Academic Notes"  # DBMS, DSA, OS, Math, Research Paper, Resume, etc.
    total_chapters: int = 1
    concepts: List[ConceptNode] = Field(default_factory=list)
    prerequisite_edges: List[Dict[str, str]] = Field(default_factory=list)  # {"from": "id1", "to": "id2"}
    detected_features: List[str] = Field(default_factory=list)  # ["code", "formulas", "sql", "diagrams"]


# ─── Study Strategy Models (StudyStrategyAgent) ───────────────────────────────

class LearningStrategyModel(BaseModel):
    strategy_name: str = "concept-first"  # concept-first, problem-first, exam-focused, interview-focused, revision-heavy
    target_goal: str = "Mastery"
    recommended_focus_order: List[str] = Field(default_factory=list)
    estimated_total_hours: float = 10.0
    rationale: str = "Selected based on topic complexity and prerequisite dependency depth."


# ─── Planner & Allocation Models (PlannerAgent) ───────────────────────────────

class PlanItemModel(BaseModel):
    task_id: Optional[int] = None
    title: str
    subject: str
    task_type: str = "study"
    recommended_minutes: int = 45
    priority_score: float = 50.0
    days_remaining: int = 7
    ai_explanation: str = ""


class StructuredPlanModel(BaseModel):
    user_id: int
    available_minutes: int = 240
    allocated_minutes: int = 0
    items: List[PlanItemModel] = Field(default_factory=list)
    confidence: float = 0.95
    reasoning: List[str] = Field(default_factory=list)


# ─── Reflection Validation Models (ReflectionAgent) ───────────────────────────

class ReflectionValidationResult(BaseModel):
    is_valid: bool = True
    replan_required: bool = False
    overload_risk: bool = False
    confidence_score: float = 0.92
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Learning Profile Models (LearningAgent) ──────────────────────────────────

class LearningProfileModel(BaseModel):
    user_id: int
    subject: str
    topic: str
    mastery_score: float = 50.0
    retention_score: float = 100.0
    confidence_score: float = 50.0
    interval_days: int = 1
    next_revision_due: Optional[datetime] = None


# ─── Analytics & Workload Models (AnalyticsAgent) ─────────────────────────────

class AnalyticsInsightModel(BaseModel):
    user_id: int
    completion_rate: float = 75.0
    weekly_study_hours: float = 12.5
    burnout_risk_level: str = "low"  # low, moderate, high
    predicted_exam_readiness: float = 82.0
    weakest_subject: str = "General"
    insights: List[str] = Field(default_factory=list)


# ─── Swarm Step Log & Execution Result ────────────────────────────────────────

class SwarmStepLog(BaseModel):
    agent_name: str
    status: str = "completed"  # pending, running, completed, warning
    summary: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SwarmExecutionResult(BaseModel):
    user_id: int
    primary_intent: str
    knowledge_graph: Optional[KnowledgeGraphModel] = None
    strategy: Optional[LearningStrategyModel] = None
    plan: Optional[StructuredPlanModel] = None
    reflection: Optional[ReflectionValidationResult] = None
    analytics: Optional[AnalyticsInsightModel] = None
    step_logs: List[SwarmStepLog] = Field(default_factory=list)
    formatted_response: str = ""
