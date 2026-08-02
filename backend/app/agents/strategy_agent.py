"""
agents/strategy_agent.py — Study Strategy Agent.

Analyzes the document knowledge graph and selects the optimal adaptive learning strategy.
Strategy is always based on the DETECTED doc_type and features from the actual document.

Strategy mapping:
  DBMS              → problem-first (SQL queries, normalization practice)
  DSA               → problem-first (code step-through, complexity analysis)
  OS                → concept-first then practice (simulation, numericals)
  MATH              → concept-first (proofs, derivations, then practice)
  ML/AI             → concept-first (theory, then experiments)
  NETWORK           → concept-first (protocols, layered approach)
  SE                → concept-first (design patterns, process)
  ACADEMIC/General  → concept-first (build prerequisite chain first)
  
  + Goal overrides:
    EXAM / GATE / EXAM_FOCUSED → exam-focused
    INTERVIEW / PLACEMENT      → interview-focused
    Low mastery (<40)          → revision-heavy
"""

from __future__ import annotations

import logging
from typing import Optional, List

from app.agents.models import KnowledgeGraphModel, LearningStrategyModel
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)


# ─── Strategy rules ordered by specificity ────────────────────────────────────

_DOC_TYPE_STRATEGY: dict[str, tuple[str, str]] = {
    "DBMS":    ("problem-first",   "DBMS document detected. Prioritizing SQL queries, normalization exercises, ER schema practice, and transaction management. Concepts must precede SQL syntax."),
    "DSA":     ("problem-first",   "Algorithmic document detected. Focusing on dry runs, time/space complexity analysis, and iterative code step-through before advanced patterns."),
    "OS":      ("concept-first",   "Operating Systems material detected. Building conceptual foundation (processes, memory, scheduling) before numerical problems and simulations."),
    "MATH":    ("concept-first",   "Mathematics document detected. Following: Definitions → Theorems → Proofs → Derivations → Practice problems."),
    "ML":      ("concept-first",   "Machine Learning material detected. Theory and intuition first, then implementation, then experiments and hyperparameter tuning."),
    "NETWORK": ("concept-first",   "Computer Networks material detected. Following OSI/TCP-IP layer order, building bottom-up understanding before application-layer protocols."),
    "SE":      ("concept-first",   "Software Engineering material detected. Design principles before patterns, process models before methodologies."),
}


def select_learning_strategy(
    graph: KnowledgeGraphModel,
    target_goal: str = "Mastery",
    ai_client: Optional[AIInferenceClient] = None,
    avg_mastery: float = 50.0,
) -> LearningStrategyModel:
    """
    Selects adaptive study strategy based on:
      1. Document's detected doc_type (from real keyword analysis)
      2. Detected content features (sql, code, formulas)
      3. Target goal (exam/placement overrides)
      4. User mastery score (low mastery → revision-heavy)

    All deterministic — no AI call needed.
    """
    doc_type = (graph.doc_type or "ACADEMIC").upper()
    features = [f.lower() for f in (graph.detected_features or [])]
    goal_upper = target_goal.upper()

    # --- Goal overrides (highest priority) ---
    if any(kw in goal_upper for kw in ["GATE", "EXAM_FOCUSED", "COMPETITIVE"]):
        strategy_name = "exam-focused"
        rationale = f"High-stakes competitive exam goal detected ({target_goal}). Ordering topics by exam frequency weight, focusing on MCQ patterns and previous year question coverage."

    elif any(kw in goal_upper for kw in ["INTERVIEW", "PLACEMENT", "CAREER"]):
        strategy_name = "interview-focused"
        rationale = "Placement/interview preparation mode. Structuring mock technical interview questions, STAR method explanations, and concept-to-application bridging."

    # --- Low mastery → revision-heavy ---
    elif avg_mastery < 40.0:
        strategy_name = "revision-heavy"
        rationale = f"Average mastery ({avg_mastery:.0f}%) is below threshold. Prioritizing spaced repetition over new material. Reviewing weak concepts before advancing."

    # --- Feature-based detection (SQL/code detected in content) ---
    elif "sql" in features:
        strategy_name = "problem-first"
        rationale = "SQL syntax detected in document. Starting with query writing practice, then normalization exercises, then schema design."

    elif "code" in features and doc_type in ("DSA", "SE", "ML", "ACADEMIC"):
        strategy_name = "problem-first"
        rationale = "Code blocks detected. Focusing on implementation first with dry runs and complexity analysis before theoretical advanced topics."

    elif "formulas" in features and doc_type in ("MATH", "NETWORK", "OS", "ACADEMIC"):
        strategy_name = "concept-first"
        rationale = "Mathematical formulas detected. Ensuring conceptual understanding before formula application — definitions and proofs before numerical practice."

    # --- Document type routing ---
    elif doc_type in _DOC_TYPE_STRATEGY:
        strategy_name, rationale = _DOC_TYPE_STRATEGY[doc_type]

    else:
        strategy_name = "concept-first"
        rationale = f"General academic document detected ({doc_type}). Building prerequisite chain before advancing to complex sub-topics."

    # Build focus order: sort concepts by (difficulty ASC, num prerequisites ASC)
    # This ensures foundational concepts come first
    focus_order: List[str] = [
        c.title for c in sorted(
            graph.concepts,
            key=lambda x: (x.difficulty, len(x.prerequisites))
        )
    ]

    estimated_hours = sum(max(0.5, c.difficulty * 0.75) for c in graph.concepts) or 8.0

    strategy = LearningStrategyModel(
        strategy_name=strategy_name,
        target_goal=target_goal,
        recommended_focus_order=focus_order[:10],
        estimated_total_hours=round(estimated_hours, 1),
        rationale=rationale,
    )

    logger.info(
        "StrategyAgent: user_mastery=%.1f doc_type=%r features=%r → strategy=%r",
        avg_mastery, doc_type, features, strategy_name
    )
    return strategy
