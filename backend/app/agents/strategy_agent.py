"""
agents/strategy_agent.py — Study Strategy Agent.

Analyzes the document knowledge graph and selects the optimal adaptive learning strategy:
  - concept-first: deep prerequisite chain, heavy theory
  - problem-first: code, SQL, numerical formulas detected
  - exam-focused: high-stakes academic syllabus / test format
  - interview-focused: career resume or technical placement focus
  - revision-heavy: low mastery or retention decay detected
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.models import KnowledgeGraphModel, LearningStrategyModel
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)


def select_learning_strategy(
    graph: KnowledgeGraphModel,
    target_goal: str = "Mastery",
    ai_client: Optional[AIInferenceClient] = None,
) -> LearningStrategyModel:
    """
    Selects adaptive study strategy based on knowledge graph features.
    
    Deterministic strategy assignment with optional LLM rationale generation.
    """
    doc_type = (graph.doc_type or "").upper()
    features = graph.detected_features or []
    
    if "sql" in features or "DBMS" in doc_type:
        strategy_name = "problem-first"
        rationale = "DBMS document detected. Prioritizing SQL queries, normalization practice, and ER schema visualizers."
    elif "code" in features or "DSA" in doc_type:
        strategy_name = "problem-first"
        rationale = "Algorithmic code detected. Focusing on time/space complexity analysis and code step-through practice."
    elif "RESUME" in doc_type or "PLACEMENT" in target_goal.upper():
        strategy_name = "interview-focused"
        rationale = "Placement or resume profile detected. Structuring mock technical interview questions and skill gap analysis."
    elif "GATE" in target_goal.upper() or "EXAM" in target_goal.upper():
        strategy_name = "exam-focused"
        rationale = "High-stakes exam goal detected. Ordering high-priority competitive questions and revision intervals."
    else:
        strategy_name = "concept-first"
        rationale = "Foundational academic document. Building prerequisite chain before advancing to complex sub-topics."

    focus_order = [c.title for c in sorted(graph.concepts, key=lambda x: (x.difficulty, len(x.prerequisites)))]
    estimated_hours = sum(max(0.5, c.difficulty * 0.75) for c in graph.concepts) or 8.0

    strategy_model = LearningStrategyModel(
        strategy_name=strategy_name,
        target_goal=target_goal,
        recommended_focus_order=focus_order[:10],
        estimated_total_hours=round(estimated_hours, 1),
        rationale=rationale,
    )

    logger.info("StudyStrategyAgent: Selected strategy %r for subject %r", strategy_name, graph.subject)
    return strategy_model
