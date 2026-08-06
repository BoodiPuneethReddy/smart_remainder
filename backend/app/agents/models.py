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
    definitions: List[Dict[str, str]] = Field(default_factory=list)  # [{"term": "3NF", "definition": "..."}]
    examples: List[str] = Field(default_factory=list)
    has_code: bool = False
    has_formulas: bool = False
    formulas: List[str] = Field(default_factory=list)
    code_snippets: List[str] = Field(default_factory=list)
    parents: List[str] = Field(default_factory=list)
    children: List[str] = Field(default_factory=list)


class ScoredConceptNode(BaseModel):
    rank_position: int
    similarity_score: float  # e.g., 94.5%
    node: ConceptNode


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
    urgency_score: float = 50.0
    importance_score: float = 50.0
    weakness_score: float = 50.0
    retention_score: float = 100.0
    effort_score: float = 50.0
    days_remaining: int = 7
    difficulty: int = 1
    prerequisite_ids: List[str] = Field(default_factory=list)
    decision_reason: str = "Scheduled based on highest priority score and budget availability."
    ai_explanation: str = ""


class DeferredTaskModel(BaseModel):
    task_id: Optional[int] = None
    title: str
    subject: str
    priority_score: float
    decision: str = "DEFERRED"  # DEFERRED, EXCLUDED
    reason: str


class StructuredPlanModel(BaseModel):
    user_id: int
    available_minutes: int = 240
    allocated_minutes: int = 0
    items: List[PlanItemModel] = Field(default_factory=list)
    deferred_tasks: List[DeferredTaskModel] = Field(default_factory=list)
    attempt_number: int = 1
    confidence: float = 0.95
    reasoning: List[str] = Field(default_factory=list)


# ─── Reflection Validation Models (ReflectionAgent) ───────────────────────────

class ReflectionValidationResult(BaseModel):
    is_valid: bool = True
    replan_required: bool = False
    attempt_number: int = 1
    overload_risk: bool = False
    confidence_score: float = 0.92
    allocated_minutes: int = 0
    available_minutes: int = 240
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    learning_quality_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
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

class SkippedAgentLog(BaseModel):
    agent_name: str
    skip_reason: str


class ExecutionGraph(BaseModel):
    intent: str
    active_agents: List[str] = Field(default_factory=list)
    skipped_agents: List[SkippedAgentLog] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)


class MinimalContext(BaseModel):
    user_query: str
    primary_intent: str
    subject_hint: Optional[str] = None
    pruned_history: List[Dict[str, str]] = Field(default_factory=list)
    relevant_concept_ids: List[str] = Field(default_factory=list)
    active_mastery: Optional[float] = None
    time_constraint_minutes: Optional[int] = None


class SwarmStepLog(BaseModel):
    agent_name: str
    status: str  # completed, warning, skipped, failed
    summary: str
    latency_ms: float = 0.0
    memory_read: List[str] = Field(default_factory=list)
    memory_written: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0


class SwarmExecutionResult(BaseModel):
    user_id: int
    primary_intent: str
    execution_graph: Optional[ExecutionGraph] = None
    knowledge_graph: Optional[KnowledgeGraphModel] = None
    strategy: Optional[LearningStrategyModel] = None
    plan: Optional[StructuredPlanModel] = None
    reflection: Optional[ReflectionValidationResult] = None
    analytics: Optional[AnalyticsInsightModel] = None
    step_logs: List[SwarmStepLog] = Field(default_factory=list)
    skipped_agents: List[SkippedAgentLog] = Field(default_factory=list)
    formatted_response: str = ""
    custom_nl_response: Optional[str] = None
