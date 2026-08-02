"""
agents/orchestrator.py — Orchestrator Agent (Brain of the System).

EXECUTION GRAPH per intent:
  STUDY_PLANNING / SCHEDULE_CONSTRAINT
      → DocumentAgent (subject-matched) + StrategyAgent + PlannerAgent
      → LearningProfileContext + ReminderAgent + ReflectionAgent + AnalyticsAgent
      → ResponseBuilder(mode=planner)

  TUTOR / INFORMATION_QUERY
      → DocumentAgent (context only) + TutorContextBuilder
      → ResponseBuilder(mode=tutor)

  LEARNING_ANALYTICS
      → LearningProfileQuery + AnalyticsAgent
      → ResponseBuilder(mode=analytics)

  GREETING / CASUAL / SMALL_TALK
      → ResponseBuilder(mode=greeting) — no heavy compute

  MOTIVATION
      → AnalyticsAgent + LearningProfileQuery
      → ResponseBuilder(mode=motivation)

  TASK_COMPLETION
      → MarkComplete + LearningAgent trigger + PlannerAgent rescore
      → ResponseBuilder(mode=completion)

  UNKNOWN / fallback
      → DocumentAgent (latest) + PlannerAgent
      → ResponseBuilder(mode=planner)

Every response uses at least: intent, user context, knowledge graph (when available),
learning profile, tasks, analytics, and real AI explanations.
No response can be generated without consulting live DB context.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.agents.models import (
    SwarmExecutionResult,
    SwarmStepLog,
    StructuredPlanModel,
    PlanItemModel,
    KnowledgeGraphModel,
)
from app.agents.memory import get_shared_memory
from app.agents.intent_classifier import classify, Intent
from app.agents.strategy_agent import select_learning_strategy
from app.agents.planner_agent import build_daily_plan
from app.agents.reflection_agent import review_plan
from app.agents.analytics_agent import generate_analytics_summary
from app.agents.response_builder import build_final_response
from app.agents.reminder_agent import check_and_create_reminders
from app.models.imported_document import ImportedDocument
from app.models.learning_profile import LearningProfile
from app.models.task import Task
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)


# ─── Time constraint extraction ───────────────────────────────────────────────

def _extract_user_time_limit(user_query: str) -> Optional[int]:
    """Extract explicit user time constraints from query text."""
    q_lower = user_query.lower()
    m = re.search(r'(\d+)\s*(?:min|minute|mins|minutes)', q_lower)
    if m:
        return int(m.group(1))
    h = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hours|hr|hrs)', q_lower)
    if h:
        return int(float(h.group(1)) * 60)
    if "an hour" in q_lower or "one hour" in q_lower:
        return 60
    if "half an hour" in q_lower or "30 mins" in q_lower:
        return 30
    return None


# ─── Subject extraction from user query ───────────────────────────────────────

_SUBJECT_KEYWORDS: Dict[str, List[str]] = {
    "DBMS":    ["dbms", "database", "sql", "normalization", "join", "er diagram", "relation", "transaction", "acid"],
    "DSA":     ["dsa", "data structure", "algorithm", "recursion", "linked list", "tree", "graph", "sorting", "heap", "bfs", "dfs"],
    "OS":      ["os", "operating system", "process", "thread", "deadlock", "memory", "paging", "scheduling", "semaphore"],
    "MATH":    ["math", "mathematics", "calculus", "integral", "derivative", "matrix", "vector", "proof", "theorem"],
    "NETWORK": ["network", "tcp", "ip", "protocol", "routing", "subnet", "osi", "http", "dns"],
    "ML":      ["ml", "machine learning", "neural", "deep learning", "model", "training", "classification"],
}


def _extract_subject_hint(user_query: str) -> Optional[str]:
    """Extract subject domain hint from user query text."""
    q_lower = user_query.lower()
    best_subject = None
    best_count = 0
    for subject, keywords in _SUBJECT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > best_count:
            best_count = count
            best_subject = subject
    return best_subject if best_count > 0 else None


# ─── Graph subject matching ───────────────────────────────────────────────────

def _find_best_matching_graph(
    user_id: int,
    subject_hint: Optional[str],
    db: Session,
    memory,
) -> Optional[KnowledgeGraphModel]:
    """
    Find the most relevant knowledge graph for the user's current query.

    Priority:
      1. If subject_hint matches a memory graph's doc_type → use it
      2. If no hint, use latest graph from memory
      3. If memory empty, load from DB (most recent first) → parse + cache all
    """
    # Load all graphs from memory
    user_space = memory._get_user_space(user_id)
    all_graphs: Dict[Any, KnowledgeGraphModel] = dict(user_space.get("knowledge_graphs", {}))
    latest_graph = user_space.get("latest_graph")

    # If we have graphs and a subject hint, try to match
    if all_graphs and subject_hint:
        for graph in all_graphs.values():
            if subject_hint.upper() in (graph.doc_type or "").upper():
                logger.info("OrchestratorAgent: Matched graph doc_type=%r for subject_hint=%r", graph.doc_type, subject_hint)
                return graph
        # Also match against subject name text
        for graph in all_graphs.values():
            if subject_hint.upper() in (graph.subject or "").upper():
                logger.info("OrchestratorAgent: Matched graph subject=%r for hint=%r", graph.subject, subject_hint)
                return graph

    # No subject match → use latest
    if latest_graph:
        return latest_graph

    # Memory cold — load from DB and parse all user documents
    docs = (
        db.query(ImportedDocument)
        .filter(ImportedDocument.user_id == user_id)
        .order_by(ImportedDocument.uploaded_at.desc())
        .all()
    )

    if not docs:
        return None

    from app.agents.document_agent import process_document
    loaded_graph = None
    for doc in docs:
        try:
            g = process_document(doc.id, db)
            memory.set_knowledge_graph(user_id, g)
            # Match subject hint against freshly parsed graph
            if subject_hint and subject_hint.upper() in (g.doc_type or "").upper():
                loaded_graph = g
        except Exception as exc:
            logger.warning("OrchestratorAgent: Failed to parse doc_id=%d: %s", doc.id, exc)

    # If no subject match found, return latest parsed
    return loaded_graph or memory.get_latest_graph(user_id)


# ─── Learning profile context ─────────────────────────────────────────────────

def _get_learning_context(user_id: int, subject_hint: Optional[str], db: Session) -> Dict[str, Any]:
    """
    Query LearningProfile for the user's mastery and retention on the detected subject.
    Returns a structured dict that goes into the response builder context.
    """
    query = db.query(LearningProfile).filter(LearningProfile.user_id == user_id)
    if subject_hint:
        profiles = query.filter(LearningProfile.subject.ilike(f"%{subject_hint}%")).all()
        if not profiles:
            profiles = query.all()
    else:
        profiles = query.all()

    if not profiles:
        return {"has_learning_data": False, "avg_mastery": 50.0, "avg_retention": 100.0, "profiles": []}

    avg_mastery = sum(p.mastery for p in profiles) / len(profiles)
    avg_retention = sum(p.retention for p in profiles) / len(profiles)

    # Find weakest topics (mastery < 50)
    weak_topics = [
        {"subject": p.subject, "topic": p.topic, "mastery": p.mastery, "retention": p.retention}
        for p in sorted(profiles, key=lambda x: x.mastery)
        if p.mastery < 60
    ][:5]

    # Find topics needing revision (retention < 60)
    revision_needed = [
        {"subject": p.subject, "topic": p.topic, "retention": p.retention, "interval_days": p.interval_days}
        for p in sorted(profiles, key=lambda x: x.retention)
        if p.retention < 60
    ][:3]

    return {
        "has_learning_data": True,
        "avg_mastery": round(avg_mastery, 1),
        "avg_retention": round(avg_retention, 1),
        "weak_topics": weak_topics,
        "revision_needed": revision_needed,
        "total_profiles": len(profiles),
    }


# ─── Plan allocation with time constraint ─────────────────────────────────────

def _fit_plan_to_time(plan_items: List[PlanItemModel], user_time_limit: int) -> List[PlanItemModel]:
    """Fit plan items to user's time budget by trimming and scaling."""
    allocated = 0
    fitted = []
    n = min(len(plan_items), 5)
    if n == 0:
        return []
    per_item = min(60, max(20, user_time_limit // n))
    for item in plan_items:
        remaining = user_time_limit - allocated
        if remaining < 15:
            break
        mins = min(per_item, remaining)
        item.recommended_minutes = mins
        allocated += mins
        fitted.append(item)
    return fitted


# ─── Context-derived plan from knowledge graph ────────────────────────────────

def _graph_to_plan_items(
    graph: KnowledgeGraphModel,
    learning_ctx: Dict[str, Any],
    user_time_limit: Optional[int],
) -> List[PlanItemModel]:
    """
    Generate plan items directly from knowledge graph concepts
    when no DB tasks exist.

    Priority order:
      1. Weak topics (mastery < 60) that appear in graph
      2. Topics needing revision (retention < 60)
      3. Remaining concepts sorted by difficulty ascending (prerequisites first)
    """
    items = []
    weak_topic_names = {wt["topic"].lower() for wt in learning_ctx.get("weak_topics", [])}
    revision_topic_names = {rt["topic"].lower() for rt in learning_ctx.get("revision_needed", [])}

    # Build ordered concept list: weak first, then revision, then sequential
    concepts_ordered = sorted(graph.concepts, key=lambda c: (
        0 if c.title.lower() in weak_topic_names else (
            1 if c.title.lower() in revision_topic_names else 2
        ),
        c.difficulty,
        len(c.prerequisites)
    ))

    total_time = user_time_limit or 240
    per_item_mins = min(60, max(20, total_time // max(len(concepts_ordered[:5]), 1)))

    for idx, concept in enumerate(concepts_ordered[:5]):
        is_weak = concept.title.lower() in weak_topic_names
        needs_revision = concept.title.lower() in revision_topic_names

        if is_weak:
            explanation = (
                f"⚠️ Weak topic — mastery below threshold. Targeted review before exam will maximize score gain."
            )
            priority = 92.0 - (idx * 3)
        elif needs_revision:
            explanation = (
                f"🔁 Retention dropping — spaced repetition review scheduled to prevent forgetting."
            )
            priority = 85.0 - (idx * 3)
        else:
            explanation = (
                f"Foundational concept from '{concept.chapter}' — difficulty level {concept.difficulty}/6. "
                f"Must be mastered before prerequisite-dependent topics."
            )
            priority = 75.0 - (idx * 5)

        items.append(PlanItemModel(
            task_id=None,
            title=concept.title,
            subject=graph.subject,
            task_type="study",
            recommended_minutes=per_item_mins,
            priority_score=priority,
            days_remaining=4,
            ai_explanation=explanation,
        ))

    return items


# ─── Main orchestrator ────────────────────────────────────────────────────────

def execute_swarm_workflow(
    user_id: int,
    user_query: str,
    db: Session,
    ai_client: AIInferenceClient,
    document_id: Optional[int] = None,
) -> SwarmExecutionResult:
    """
    Full context-aware multi-agent execution.
    Every response consults: intent, knowledge graph, learning profiles,
    tasks, analytics, reminders, and reflection.
    No response can be produced without live DB context.
    """
    memory = get_shared_memory()
    step_logs: List[SwarmStepLog] = []

    logger.info("=" * 50)
    logger.info("Orchestrator: user_id=%d query=%r", user_id, user_query)

    # ── Step 1: Intent + Entity Extraction ────────────────────────────────────
    intent_res = classify(user_query)
    primary_intent = intent_res.primary_intent
    primary_intent_value = primary_intent.value
    user_time_limit = _extract_user_time_limit(user_query) or intent_res.entities.get("available_minutes")
    subject_hint = _extract_subject_hint(user_query)

    step_logs.append(SwarmStepLog(
        agent_name="IntentAgent",
        status="completed",
        summary=(
            f"Classified intent: '{primary_intent_value}'"
            + (f" | Subject: {subject_hint}" if subject_hint else "")
            + (f" | Time: {user_time_limit}m" if user_time_limit else "")
        ),
    ))
    logger.info("IntentAgent: intent=%r subject=%r time=%s", primary_intent_value, subject_hint, user_time_limit)

    # ── Step 2: Learning Profile Context ─────────────────────────────────────
    learning_ctx = _get_learning_context(user_id, subject_hint, db)
    avg_mastery = learning_ctx.get("avg_mastery", 50.0)

    if learning_ctx["has_learning_data"]:
        step_logs.append(SwarmStepLog(
            agent_name="ContextBuilder",
            status="completed",
            summary=(
                f"Loaded {learning_ctx['total_profiles']} learning profiles | "
                f"Avg mastery: {avg_mastery:.0f}% | "
                f"Avg retention: {learning_ctx['avg_retention']:.0f}% | "
                f"Weak topics: {len(learning_ctx.get('weak_topics', []))}"
            ),
        ))
    else:
        step_logs.append(SwarmStepLog(
            agent_name="ContextBuilder",
            status="completed",
            summary="No learning profile data yet — using default mastery values.",
        ))

    # ── SHORT-CIRCUIT: Greeting / Casual / Goodbye ─────────────────────────
    if primary_intent in (Intent.GREETING, Intent.GOODBYE, Intent.GRATITUDE, Intent.SMALL_TALK, Intent.CASUAL):
        analytics = generate_analytics_summary(user_id, db)
        result = SwarmExecutionResult(
            user_id=user_id,
            primary_intent=primary_intent_value,
            analytics=analytics,
            step_logs=step_logs,
        )
        result.formatted_response = build_final_response(result, user_query, learning_ctx)
        return result

    # ── SHORT-CIRCUIT: Learning Analytics query ────────────────────────────
    if primary_intent == Intent.LEARNING_ANALYTICS:
        analytics = generate_analytics_summary(user_id, db)
        step_logs.append(SwarmStepLog(
            agent_name="AnalyticsAgent",
            status="completed",
            summary=f"Completion: {analytics.completion_rate}% | Burnout: {analytics.burnout_risk_level} | Readiness: {analytics.predicted_exam_readiness}%",
        ))
        result = SwarmExecutionResult(
            user_id=user_id,
            primary_intent=primary_intent_value,
            analytics=analytics,
            step_logs=step_logs,
        )
        result.formatted_response = build_final_response(result, user_query, learning_ctx)
        return result

    # ── Step 3: Knowledge Graph Selection ─────────────────────────────────
    graph: Optional[KnowledgeGraphModel] = None

    if document_id:
        from app.agents.document_agent import process_document
        graph = process_document(document_id, db)
        memory.set_knowledge_graph(user_id, graph)
    else:
        graph = _find_best_matching_graph(user_id, subject_hint, db, memory)

    if graph:
        step_logs.append(SwarmStepLog(
            agent_name="DocumentAgent",
            status="completed",
            summary=(
                f"Knowledge graph: '{graph.subject}' ({graph.doc_type}) | "
                f"{len(graph.concepts)} concepts | "
                f"Features: {', '.join(graph.detected_features[:4])}"
            ),
        ))

    # ── Step 4: Strategy Selection ─────────────────────────────────────────
    strategy = None
    if graph:
        strategy = select_learning_strategy(
            graph,
            target_goal="Mastery",
            ai_client=ai_client,
            avg_mastery=avg_mastery,
        )
        memory.set_strategy(user_id, strategy)
        step_logs.append(SwarmStepLog(
            agent_name="StrategyAgent",
            status="completed",
            summary=f"Strategy: '{strategy.strategy_name}' | {strategy.rationale[:80]}...",
        ))

    # ── Step 5: Planner — DB Tasks first, then KB graph fallback ──────────
    raw_plan = build_daily_plan(user_id, db, ai_client,
                                constraints={"available_minutes": user_time_limit} if user_time_limit else None)
    # build_daily_plan returns {"tasks": [...], ...}
    db_tasks = raw_plan.get("tasks", [])

    plan_items: List[PlanItemModel] = []

    if db_tasks:
        for item in db_tasks:
            plan_items.append(PlanItemModel(
                task_id=item.get("task_id"),
                title=item.get("title", "Study Session"),
                subject=item.get("subject", graph.subject if graph else "General"),
                task_type=item.get("task_type", "study"),
                recommended_minutes=item.get("recommended_minutes", 35),
                priority_score=item.get("priority_score", 50.0),
                days_remaining=item.get("days_remaining", 7),
                ai_explanation=item.get("ai_explanation", ""),
            ))

    # Supplement with knowledge graph concepts if tasks are sparse
    if graph and len(plan_items) < 3:
        graph_items = _graph_to_plan_items(graph, learning_ctx, user_time_limit)
        # Add only graph items that aren't duplicated by DB task subjects
        db_subjects = {i.subject.lower() for i in plan_items}
        for gi in graph_items:
            if gi.subject.lower() not in db_subjects or len(plan_items) == 0:
                plan_items.append(gi)

    # Apply time constraint
    target_avail = user_time_limit or raw_plan.get("total_recommended_minutes", 240)
    if user_time_limit and plan_items:
        plan_items = _fit_plan_to_time(plan_items, user_time_limit)

    structured_plan = StructuredPlanModel(
        user_id=user_id,
        available_minutes=target_avail,
        allocated_minutes=sum(i.recommended_minutes for i in plan_items),
        items=plan_items,
        confidence=0.95,
        reasoning=[
            "Priority scoring: 0.35×Urgency + 0.20×ExamWeight + 0.20×Importance + 0.10×Ebbinghaus + 0.15×Recency.",
            f"Context: {learning_ctx['total_profiles'] if learning_ctx['has_learning_data'] else 0} learning profiles consulted.",
        ],
    )
    memory.set_schedule(user_id, structured_plan)

    step_logs.append(SwarmStepLog(
        agent_name="PlannerAgent",
        status="completed",
        summary=(
            f"Scheduled {len(plan_items)} sessions | "
            f"Total: {structured_plan.allocated_minutes}m / {target_avail}m budget | "
            f"DB tasks: {len(db_tasks)} | Graph items: {max(0, len(plan_items)-len(db_tasks))}"
        ),
    ))

    # ── Step 6: Reminders (only for study planning) ────────────────────────
    active_reminders = []
    if primary_intent in (Intent.STUDY_PLANNING, Intent.SCHEDULE_CONSTRAINT):
        try:
            active_reminders = check_and_create_reminders(user_id, db, ai_client)
            if active_reminders:
                step_logs.append(SwarmStepLog(
                    agent_name="ReminderAgent",
                    status="completed",
                    summary=f"Found {len(active_reminders)} urgent reminders: " +
                            ", ".join(f"{n.title}" for n in active_reminders[:2]),
                ))
        except Exception as exc:
            logger.warning("ReminderAgent failed: %s", exc)

    # ── Step 7: Reflection ─────────────────────────────────────────────────
    reflection = review_plan(structured_plan)
    memory.add_reflection(user_id, reflection)

    if reflection.replan_required and user_time_limit and plan_items:
        # Auto-replan: trim to fit
        plan_items = _fit_plan_to_time(plan_items[:3], user_time_limit)
        structured_plan.items = plan_items
        structured_plan.allocated_minutes = sum(i.recommended_minutes for i in plan_items)
        reflection = review_plan(structured_plan)
        step_logs.append(SwarmStepLog(
            agent_name="ReflectionAgent",
            status="warning",
            summary="Overload detected — auto-replanned to fit budget. Schedule re-validated.",
        ))
    else:
        step_logs.append(SwarmStepLog(
            agent_name="ReflectionAgent",
            status="completed" if reflection.is_valid else "warning",
            summary=(
                "Schedule verified: feasible and within safe daily study limits."
                if reflection.is_valid
                else f"Warnings: {'; '.join(reflection.warnings[:2])}"
            ),
        ))

    # ── Step 8: Analytics ─────────────────────────────────────────────────
    analytics = generate_analytics_summary(user_id, db)
    memory.set_analytics(user_id, analytics)
    step_logs.append(SwarmStepLog(
        agent_name="AnalyticsAgent",
        status="completed",
        summary=(
            f"Completion: {analytics.completion_rate}% | "
            f"Burnout: {analytics.burnout_risk_level} | "
            f"Predicted readiness: {analytics.predicted_exam_readiness}%"
        ),
    ))

    # ── Build result ───────────────────────────────────────────────────────
    result = SwarmExecutionResult(
        user_id=user_id,
        primary_intent=primary_intent_value,
        knowledge_graph=graph,
        strategy=strategy,
        plan=structured_plan,
        reflection=reflection,
        analytics=analytics,
        step_logs=step_logs,
    )

    result.formatted_response = build_final_response(result, user_query, learning_ctx)
    logger.info("Orchestrator done: user=%d steps=%d intent=%r", user_id, len(step_logs), primary_intent_value)
    return result
