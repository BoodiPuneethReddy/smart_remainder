"""
agents/orchestrator.py — Orchestrator Agent (Brain of the System).

Decomposes user goals, selects domain agents, coordinates swarm execution,
stores state in SharedMemoryStore, invokes ReflectionAgent validation,
and returns a SwarmExecutionResult.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.agents.models import (
    SwarmExecutionResult,
    SwarmStepLog,
    StructuredPlanModel,
    PlanItemModel,
)
from app.agents.memory import get_shared_memory
from app.agents.intent_classifier import classify, Intent
from app.agents.strategy_agent import select_learning_strategy
from app.agents.planner_agent import build_daily_plan
from app.agents.reflection_agent import review_plan
from app.agents.analytics_agent import generate_analytics_summary
from app.agents.response_builder import build_final_response
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)


def execute_swarm_workflow(
    user_id: int,
    user_query: str,
    db: Session,
    ai_client: AIInferenceClient,
    document_id: Optional[int] = None,
) -> SwarmExecutionResult:
    """
    Executes collaborative multi-agent workflow:
      Gateway -> Intent -> Shared Memory -> DocumentAgent -> StrategyAgent -> PlannerAgent
      -> LearningAgent -> AnalyticsAgent -> ReflectionAgent -> ResponseBuilder
    """
    memory = get_shared_memory()
    step_logs: list[SwarmStepLog] = []

    # Step 1: Intent Classification
    intent_res = classify(user_query)
    primary_intent = intent_res.primary_intent.value
    step_logs.append(
        SwarmStepLog(
            agent_name="OrchestratorAgent",
            status="completed",
            summary=f"Detected intent '{primary_intent}' with confidence {intent_res.confidence:.2f}.",
        )
    )

    # Step 2: Knowledge Graph Retrieval / Processing (DocumentAgent)
    graph = None
    if document_id:
        from app.agents.document_agent import process_document
        graph = process_document(document_id, db)
        memory.set_knowledge_graph(user_id, graph)
        step_logs.append(
            SwarmStepLog(
                agent_name="DocumentAgent",
                status="completed",
                summary=f"Parsed Knowledge Graph for '{graph.subject}' ({len(graph.concepts)} concepts).",
            )
        )
    else:
        graph = memory.get_latest_graph(user_id)

    # Step 3: Strategy Selection (StudyStrategyAgent)
    strategy = None
    if graph:
        strategy = select_learning_strategy(graph, target_goal="Mastery", ai_client=ai_client)
        memory.set_strategy(user_id, strategy)
        step_logs.append(
            SwarmStepLog(
                agent_name="StrategyAgent",
                status="completed",
                summary=f"Selected '{strategy.strategy_name}' strategy ({strategy.rationale}).",
            )
        )

    # Step 4: Schedule Generation (PlannerAgent)
    raw_plan_dict = build_daily_plan(user_id, db, ai_client)
    plan_items = [
        PlanItemModel(
            task_id=item.get("task_id"),
            title=item.get("title", "Study Session"),
            subject=item.get("subject", "General"),
            task_type=item.get("task_type", "study"),
            recommended_minutes=item.get("recommended_minutes", 45),
            priority_score=item.get("priority_score", 50.0),
            days_remaining=item.get("days_remaining", 7),
            ai_explanation=item.get("ai_explanation", ""),
        )
        for item in raw_plan_dict.get("items", [])
    ]

    structured_plan = StructuredPlanModel(
        user_id=user_id,
        available_minutes=raw_plan_dict.get("available_minutes", 240),
        allocated_minutes=raw_plan_dict.get("total_minutes_allocated", 0),
        items=plan_items,
        confidence=0.95,
        reasoning=["Prioritized using 5-factor deterministic priority scoring."],
    )
    memory.set_schedule(user_id, structured_plan)
    step_logs.append(
        SwarmStepLog(
            agent_name="PlannerAgent",
            status="completed",
            summary=f"Generated daily study roadmap with {len(plan_items)} task allocation sessions.",
        )
    )

    # Step 5: Plan Validation & Guardrails (ReflectionAgent)
    reflection = review_plan(structured_plan)
    memory.add_reflection(user_id, reflection)
    step_logs.append(
        SwarmStepLog(
            agent_name="ReflectionAgent",
            status="completed" if reflection.is_valid else "warning",
            summary="Schedule verified as feasible." if reflection.is_valid else "Guardrail issued: Replanning recommended.",
        )
    )

    # Step 6: Analytics & Workload (AnalyticsAgent)
    analytics = generate_analytics_summary(user_id, db)
    memory.set_analytics(user_id, analytics)
    step_logs.append(
        SwarmStepLog(
            agent_name="AnalyticsAgent",
            status="completed",
            summary=f"Workload analyzed: Completion rate {analytics.completion_rate}%, Burnout risk {analytics.burnout_risk_level}.",
        )
    )

    result = SwarmExecutionResult(
        user_id=user_id,
        primary_intent=primary_intent,
        knowledge_graph=graph,
        strategy=strategy,
        plan=structured_plan,
        reflection=reflection,
        analytics=analytics,
        step_logs=step_logs,
    )

    result.formatted_response = build_final_response(result)
    logger.info("OrchestratorAgent: Workflow completed for user=%d intent=%s steps=%d", user_id, primary_intent, len(step_logs))
    return result
