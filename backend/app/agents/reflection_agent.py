"""
agents/reflection_agent.py — Reflection Agent (Structured Guardrail & Learning Coach)

Performs comprehensive multi-factor audits of candidate study plans:
  1. Time Budget & Overload Violations (Exceeding user available minutes or 12h ceiling).
  2. Prerequisite Dependency Violations (Detects if B is scheduled before prerequisite A).
  3. Cognitive Load & Fatigue (Detects back-to-back heavy topics with difficulty >= 4).
  4. Returns a detailed ReflectionValidationResult containing structured violations,
     recommendations, and learning_quality_issues.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from app.agents.models import StructuredPlanModel, ReflectionValidationResult, KnowledgeGraphModel

logger = logging.getLogger(__name__)

# Human capacity ceiling
MAX_DAILY_STUDY_MINUTES = 720


def review_plan(
    plan: StructuredPlanModel,
    max_budget_minutes: Optional[int] = None,
    knowledge_graph: Optional[KnowledgeGraphModel] = None,
    attempt_number: int = 1,
) -> ReflectionValidationResult:
    """
    Audits a StructuredPlanModel for duration feasibility, prerequisite order, and cognitive fatigue.
    """
    violations: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []
    learning_quality_issues: List[str] = []
    warnings: List[str] = []

    overload_risk = False
    replan_required = False
    effective_budget = max_budget_minutes or plan.available_minutes or 240
    allocated_mins = sum(item.recommended_minutes for item in plan.items)

    # 1. Audit Budget Mismatch & Overload
    if allocated_mins > effective_budget:
        overload_risk = True
        replan_required = True
        diff = allocated_mins - effective_budget
        violations.append({
            "code": "BUDGET_EXCEEDED",
            "detail": f"Allocated duration ({allocated_mins}m) exceeds available budget ({effective_budget}m) by {diff}m."
        })
        recommendations.append({
            "action": "TRIM_LOW_PRIORITY",
            "target_budget": effective_budget,
            "reason": "Cap total session allocation to user-specified budget and defer non-urgent tasks."
        })
        warnings.append(f"Excessive duration: {allocated_mins}m exceeds {effective_budget}m budget cap.")

    if allocated_mins > MAX_DAILY_STUDY_MINUTES:
        overload_risk = True
        replan_required = True
        violations.append({
            "code": "HUMAN_CEILING_EXCEEDED",
            "detail": f"Total duration ({allocated_mins}m) exceeds 12-hour maximum human study limit."
        })

    # 2. Audit Prerequisite Order Violations
    scheduled_ids = []
    for idx, item in enumerate(plan.items):
        item_id = f"item_{idx}"
        for prereq in item.prerequisite_ids:
            if prereq not in scheduled_ids:
                replan_required = True
                violations.append({
                    "code": "PREREQUISITE_ORDER_VIOLATION",
                    "task_title": item.title,
                    "missing_prerequisite": prereq,
                    "detail": f"Topic '{item.title}' scheduled before its required prerequisite '{prereq}'."
                })
                recommendations.append({
                    "action": "REORDER_PREREQUISITES",
                    "prerequisite": prereq,
                    "target_task": item.title
                })
                warnings.append(f"Prerequisite ordering flaw: '{item.title}' depends on '{prereq}'.")
        scheduled_ids.append(item.title.lower())

    # 3. Audit Cognitive Load & Study Fatigue (Back-to-back heavy topics)
    prev_difficulty = 0
    for idx, item in enumerate(plan.items):
        diff_val = getattr(item, 'difficulty', 1)
        if diff_val >= 4 and prev_difficulty >= 4:
            learning_quality_issues.append(
                f"Back-to-back intense sessions detected ('{plan.items[idx-1].title}' & '{item.title}' both difficulty {diff_val})."
            )
            recommendations.append({
                "action": "INSERT_REST_BREAK",
                "duration": 10,
                "after_task": plan.items[idx-1].title,
                "reason": "Insert rest interval to mitigate cognitive overload."
            })
        prev_difficulty = diff_val

    if not plan.items:
        warnings.append("Plan contains zero scheduled items.")

    confidence = 0.95 if not replan_required else max(0.40, 0.90 - (attempt_number * 0.15))

    result = ReflectionValidationResult(
        is_valid=not replan_required,
        replan_required=replan_required,
        attempt_number=attempt_number,
        overload_risk=overload_risk,
        confidence_score=round(confidence, 2),
        allocated_minutes=allocated_mins,
        available_minutes=effective_budget,
        violations=violations,
        recommendations=recommendations,
        learning_quality_issues=learning_quality_issues,
        warnings=warnings,
    )

    logger.info(
        "ReflectionAgent (Attempt %d): Validated plan valid=%s replan_required=%s (Allocated: %dm / %dm)",
        attempt_number, result.is_valid, result.replan_required, allocated_mins, effective_budget
    )
    return result
