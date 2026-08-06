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
    DeferredTaskModel,
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
from app.agents.session_state import get_session, update_session

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

    # ── Step 1: Intent + Entity Extraction + Session Context Resolution ───────
    session = get_session(user_id)
    intent_res = classify(user_query)
    primary_intent = intent_res.primary_intent
    primary_intent_value = primary_intent.value

    user_time_limit = _extract_user_time_limit(user_query) or intent_res.entities.get("available_minutes")
    subject_hint = _extract_subject_hint(user_query)

    # Inherit session context if this is a follow-up or contains date shift
    is_followup = intent_res.entities.get("is_followup", False)
    date_shift = intent_res.entities.get("date_shift")

    if (is_followup or date_shift) and not subject_hint:
        subject_hint = session.last_subject
    if (is_followup or date_shift) and not user_time_limit:
        user_time_limit = session.last_time_limit or 90

    if subject_hint:
        session.last_subject = subject_hint
    if user_time_limit:
        session.last_time_limit = user_time_limit

    summary_text = f"Classified intent: '{primary_intent_value}'"
    if subject_hint:
        summary_text += f" | Subject: {subject_hint}"
    if user_time_limit:
        summary_text += f" | Time: {user_time_limit}m"
    if date_shift:
        summary_text += f" | Target: {date_shift.title()}"
    if is_followup:
        summary_text += " | Follow-up context resolved"

    step_logs.append(SwarmStepLog(
        agent_name="IntentAgent",
        status="completed",
        summary=summary_text,
    ))
    logger.info("IntentAgent: intent=%r subject=%r time=%s date_shift=%s", primary_intent_value, subject_hint, user_time_limit, date_shift)

    # ── Step 1.5: Dynamic Execution Graph Construction ─────────────────────
    from app.agents.graph_builder import build_execution_graph, visualize_runtime_graph
    from app.agents.context_agent import build_minimal_context

    has_doc = bool(document_id or session.last_imported_document_id)
    has_time = bool(user_time_limit or session.last_time_limit)

    exec_graph = build_execution_graph(
        intent=intent_res.primary_intent,
        user_query=user_query,
        has_document=has_doc,
        has_time_constraint=has_time,
    )

    # Record skipped agents explicitly in step logs
    for skipped in exec_graph.skipped_agents:
        step_logs.append(SwarmStepLog(
            agent_name=skipped.agent_name,
            status="skipped",
            summary=skipped.skip_reason,
        ))

    # ── Step 2: ContextAgent (Selective Pruning) ───────────────────────────
    learning_ctx = _get_learning_context(user_id, subject_hint, db)
    avg_mastery = learning_ctx.get("avg_mastery", 50.0)

    minimal_ctx = build_minimal_context(
        user_query=user_query,
        intent=primary_intent_value,
        session=session,
        subject_hint=subject_hint,
        time_limit_minutes=user_time_limit,
    )
    step_logs.append(SwarmStepLog(
        agent_name="ContextAgent",
        status="completed",
        summary=f"Pruned conversation history to {len(minimal_ctx.pruned_history)} turns for intent '{primary_intent_value}'",
    ))

    # ── Branch 1: Conversational / Greeting Dynamic Graph ─────────────────
    if "TutorAgent" not in exec_graph.active_agents and "PlannerAgent" not in exec_graph.active_agents and "AnalyticsAgent" not in exec_graph.active_agents:
        analytics = generate_analytics_summary(user_id, db)
        result = SwarmExecutionResult(
            user_id=user_id,
            primary_intent=primary_intent_value,
            execution_graph=exec_graph,
            analytics=analytics,
            step_logs=step_logs,
            skipped_agents=exec_graph.skipped_agents,
        )
        ctx = {"user_query": user_query, "intent": primary_intent_value, "learning_ctx": learning_ctx, "history": minimal_ctx.pruned_history}
        try:
            nl_resp = ai_client.generate("chat_answer", ctx)
            if nl_resp and len(nl_resp.strip()) > 10:
                result.custom_nl_response = nl_resp.strip()
        except Exception as exc:
            logger.warning("Greeting Gemini call notice: %s", exc)
        result.formatted_response = (
            "Hi Puneeth! Welcome back. 👋\n\n"
            "Ready to continue Database Management Systems, or would you like to study something new today?"
        )
        session.add_turn(user_query, result.formatted_response, primary_intent_value)
        return result

    # ── Branch 2: Analytics Query Dynamic Graph ────────────────────────────
    if "AnalyticsAgent" in exec_graph.active_agents and "PlannerAgent" not in exec_graph.active_agents and "TutorAgent" not in exec_graph.active_agents:
        analytics = generate_analytics_summary(user_id, db)
        step_logs.append(SwarmStepLog(
            agent_name="AnalyticsAgent",
            status="completed",
            summary=f"Completion: {analytics.completion_rate}% | Burnout: {analytics.burnout_risk_level} | Readiness: {analytics.predicted_exam_readiness}%",
        ))
        result = SwarmExecutionResult(
            user_id=user_id,
            primary_intent=primary_intent_value,
            execution_graph=exec_graph,
            analytics=analytics,
            step_logs=step_logs,
            skipped_agents=exec_graph.skipped_agents,
        )
        ctx = {"user_query": user_query, "intent": primary_intent_value, "analytics": {"completion_rate": analytics.completion_rate, "burnout_risk_level": analytics.burnout_risk_level, "predicted_exam_readiness": analytics.predicted_exam_readiness}, "history": minimal_ctx.pruned_history}
        try:
            nl_resp = ai_client.generate("chat_answer", ctx)
            if nl_resp and len(nl_resp.strip()) > 10:
                result.custom_nl_response = nl_resp.strip()
        except Exception as exc:
            logger.warning("Analytics Gemini call notice: %s", exc)
        result.formatted_response = build_final_response(result, user_query, learning_ctx)
        session.add_turn(user_query, result.formatted_response, primary_intent_value)
        return result

    # ── Branch 3: Tutor / Explanation Dynamic Graph ───────────────────────
    if "TutorAgent" in exec_graph.active_agents and "PlannerAgent" not in exec_graph.active_agents:
        from app.agents.retrieval_agent import retrieve_top_k_nodes

        graph = _find_best_matching_graph(user_id, subject_hint, db, memory)
        top_k_nodes = retrieve_top_k_nodes(user_query, graph, top_k=3) if graph else []

        top_summary = f"Top-1: '{top_k_nodes[0].node.title}' ({top_k_nodes[0].similarity_score}%)" if top_k_nodes else "None"
        step_logs.append(SwarmStepLog(
            agent_name="RetrievalAgent",
            status="completed",
            summary=f"Retrieved Top-{len(top_k_nodes)} concept nodes for query '{user_query}' [{top_summary}]",
        ))

        if graph:
            step_logs.append(SwarmStepLog(
                agent_name="DocumentAgent",
                status="completed",
                summary=f"Traversed '{graph.subject}' knowledge graph ({len(graph.concepts)} total concepts)",
            ))
        step_logs.append(SwarmStepLog(
            agent_name="TutorAgent",
            status="completed",
            summary=f"Grounded Socratic explanation using {len(top_k_nodes)} retrieved nodes",
        ))
        result = SwarmExecutionResult(
            user_id=user_id,
            primary_intent=primary_intent_value,
            execution_graph=exec_graph,
            knowledge_graph=graph,
            step_logs=step_logs,
            skipped_agents=exec_graph.skipped_agents,
        )
        ctx = {
            "user_query": user_query,
            "intent": primary_intent_value,
            "subject": subject_hint or (graph.subject if graph else "General"),
            "learning_ctx": learning_ctx,
            "history": minimal_ctx.pruned_history,
            "retrieved_nodes": [
                {
                    "rank": s.rank_position,
                    "similarity_score": f"{s.similarity_score}%",
                    "id": s.node.id,
                    "title": s.node.title,
                    "summary": s.node.summary,
                    "difficulty": s.node.difficulty,
                    "definitions": s.node.definitions,
                    "examples": s.node.examples,
                    "formulas": s.node.formulas,
                    "code_snippets": s.node.code_snippets,
                    "parents": s.node.parents,
                    "children": s.node.children,
                } for s in top_k_nodes
            ] if top_k_nodes else [],
            "knowledge_graph": {
                "subject": graph.subject,
                "concepts": [{"title": c.title, "summary": c.summary, "chapter": c.chapter} for c in graph.concepts[:5]]
            } if graph else None
        }
        try:
            nl_resp = ai_client.generate("tutor_evaluate_response" if "quiz" in user_query.lower() else "chat_answer", ctx)
            if nl_resp and len(nl_resp.strip()) > 10:
                result.custom_nl_response = nl_resp.strip()
        except Exception as exc:
            logger.warning("Tutor Gemini call notice: %s", exc)
        result.formatted_response = build_final_response(result, user_query, learning_ctx)
        session.add_turn(user_query, result.formatted_response, primary_intent_value)
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
    raw_deferred = raw_plan.get("deferred_tasks", [])

    plan_items: List[PlanItemModel] = []
    deferred_tasks: List[DeferredTaskModel] = []

    if db_tasks:
        for item in db_tasks:
            plan_items.append(PlanItemModel(
                task_id=item.get("task_id"),
                title=item.get("title", "Study Session"),
                subject=item.get("subject", graph.subject if graph else "General"),
                task_type=item.get("task_type", "study"),
                recommended_minutes=item.get("recommended_minutes", 35),
                priority_score=item.get("priority_score", 50.0),
                urgency_score=item.get("urgency_score", 50.0),
                importance_score=item.get("importance_score", 50.0),
                weakness_score=item.get("weakness_score", 50.0),
                retention_score=item.get("retention_score", 100.0),
                effort_score=item.get("effort_score", 50.0),
                days_remaining=item.get("days_remaining", 7),
                decision_reason=item.get("decision_reason", "Scheduled based on priority ranking."),
                ai_explanation=item.get("ai_explanation", ""),
            ))

    for def_item in raw_deferred:
        deferred_tasks.append(DeferredTaskModel(
            task_id=def_item.get("task_id"),
            title=def_item.get("title", "Study Task"),
            subject=def_item.get("subject", "General"),
            priority_score=def_item.get("priority_score", 40.0),
            decision="DEFERRED",
            reason=def_item.get("reason", "Deferred due to time budget cap.")
        ))

    # Supplement with knowledge graph concepts if tasks are sparse
    if graph and len(plan_items) < 3:
        graph_items = _graph_to_plan_items(graph, learning_ctx, user_time_limit)
        db_subjects = {i.subject.lower() for i in plan_items}
        for gi in graph_items:
            if gi.subject.lower() not in db_subjects or len(plan_items) == 0:
                plan_items.append(gi)

    target_avail = user_time_limit or raw_plan.get("total_recommended_minutes", 240)

    structured_plan = StructuredPlanModel(
        user_id=user_id,
        available_minutes=target_avail,
        allocated_minutes=sum(i.recommended_minutes for i in plan_items),
        items=plan_items,
        deferred_tasks=deferred_tasks,
        attempt_number=1,
        confidence=0.95,
        reasoning=[
            "Priority formula: 0.35×Urgency + 0.20×ExamWeight + 0.20×Importance + 0.10×Ebbinghaus + 0.15×Recency.",
            f"Consulted {learning_ctx['total_profiles'] if learning_ctx['has_learning_data'] else 0} active learning profile(s).",
        ],
    )
    memory.set_schedule(user_id, structured_plan)

    step_logs.append(SwarmStepLog(
        agent_name="PlannerAgent",
        status="completed",
        summary=(
            f"Attempt 1: Scheduled {len(plan_items)} sessions ({structured_plan.allocated_minutes}m / {target_avail}m) | "
            f"Deferred {len(deferred_tasks)} tasks"
        ),
        memory_read=["user_profile", "learning_profiles", "task_db"],
        memory_written=["current_schedule"]
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
                    memory_read=["task_db"],
                    memory_written=["active_reminders"]
                ))
        except Exception as exc:
            logger.warning("ReminderAgent failed: %s", exc)

    # ── Step 7: Reflection — Multi-Pass Feedback Loop (Max 3 Attempts) ─────
    reflection = None
    for attempt in range(1, 4):
        structured_plan.attempt_number = attempt
        reflection = review_plan(
            structured_plan,
            max_budget_minutes=target_avail,
            knowledge_graph=graph,
            attempt_number=attempt
        )
        memory.add_reflection(user_id, reflection)

        if not reflection.replan_required:
            step_logs.append(SwarmStepLog(
                agent_name="ReflectionAgent",
                status="completed",
                summary=f"Attempt {attempt}: APPROVED — Feasible schedule ({structured_plan.allocated_minutes}m / {target_avail}m budget).",
                memory_read=["current_schedule", "reflection_history"],
                memory_written=["verified_schedule"],
                confidence_score=reflection.confidence_score
            ))
            break
        else:
            step_logs.append(SwarmStepLog(
                agent_name="ReflectionAgent",
                status="warning",
                summary=f"Attempt {attempt}: REJECTED — {reflection.warnings[0]} Recommendations: {reflection.recommendations[0] if reflection.recommendations else 'Trim budget'}",
                memory_read=["current_schedule"],
                memory_written=["reflection_history"],
                confidence_score=reflection.confidence_score
            ))

            if attempt < 3:
                # Intelligently optimize and defer lower priority tasks
                if len(structured_plan.items) > 1:
                    deferred_item = structured_plan.items.pop()
                    structured_plan.deferred_tasks.append(DeferredTaskModel(
                        task_id=deferred_item.task_id,
                        title=deferred_item.title,
                        subject=deferred_item.subject,
                        priority_score=deferred_item.priority_score,
                        decision="DEFERRED",
                        reason=f"Deferred by Reflection attempt {attempt} to satisfy {target_avail}m budget cap."
                    ))
                if structured_plan.items:
                    plan_items = _fit_plan_to_time(structured_plan.items, target_avail)
                    structured_plan.items = plan_items
                structured_plan.allocated_minutes = sum(i.recommended_minutes for i in structured_plan.items)
            else:
                step_logs.append(SwarmStepLog(
                    agent_name="ReflectionAgent",
                    status="failed",
                    summary=f"Attempt 3: UNSATISFIABLE CONSTRAINTS — Unable to fit tasks into {target_avail}m after 3 attempts.",
                    memory_read=["current_schedule", "reflection_history"],
                    memory_written=["failed_schedule_notice"],
                    confidence_score=0.30
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
        memory_read=["task_db", "user_profile"],
        memory_written=["analytics_summary"],
        confidence_score=0.96
    ))

    # ── Step 9: Call Gemini AI Client via Grounded Prompt Builder ─────────
    from app.services.prompt_builders import build_grounded_mentor_prompt
    import time

    start_perf = time.perf_counter()
    history_turns = [
        {"user_query": turn.user_query, "bot_response": turn.bot_response, "intent": turn.intent}
        for turn in session.history
    ]

    context_payload = {
        "user_query": user_query,
        "intent": primary_intent_value,
        "subject": subject_hint or (graph.subject if graph else "General"),
        "learning_ctx": learning_ctx,
        "history": history_turns,
        "knowledge_graph": {
            "subject": graph.subject,
            "concepts": [{"title": c.title, "summary": c.summary, "chapter": c.chapter} for c in graph.concepts[:5]]
        } if graph else None,
        "plan": {
            "available_minutes": structured_plan.available_minutes,
            "allocated_minutes": structured_plan.allocated_minutes,
            "items": [{"title": i.title, "subject": i.subject, "recommended_minutes": i.recommended_minutes, "priority_score": i.priority_score, "days_remaining": i.days_remaining} for i in structured_plan.items],
            "deferred_tasks": [{"title": d.title, "reason": d.reason} for d in structured_plan.deferred_tasks]
        } if structured_plan else None,
        "reflection": {
            "is_valid": reflection.is_valid if reflection else True,
            "violations": reflection.violations if reflection else [],
            "recommendations": reflection.recommendations if reflection else []
        } if reflection else None,
        "analytics": {
            "completion_rate": analytics.completion_rate,
            "burnout_risk_level": analytics.burnout_risk_level,
            "predicted_exam_readiness": analytics.predicted_exam_readiness
        } if analytics else None
    }

    grounded_prompt = build_grounded_mentor_prompt(context_payload)

    # Grounding telemetry report with explicit citations
    used_defs = []
    used_exs = []
    used_sqls = []
    used_forms = []
    used_nodes = []
    if graph and graph.concepts:
        for c in graph.concepts[:5]:
            used_nodes.append(c.id)
            if c.definitions:
                used_defs.extend([d.get("definition") for d in c.definitions if d.get("definition")])
            if c.examples:
                used_exs.extend(c.examples)
            if c.code_snippets:
                used_sqls.extend(c.code_snippets)
            if c.formulas:
                used_forms.extend(c.formulas)

    grounding_report = {
        "knowledge_nodes_used": used_nodes,
        "used_definitions": used_defs[:3],
        "used_examples": used_exs[:3],
        "used_sql_examples": used_sqls[:3],
        "used_formulas": used_forms[:3],
        "planner_fields_used": ["available_minutes", "allocated_minutes", "items", "deferred_tasks"] if structured_plan else [],
        "analytics_used": ["completion_rate", "burnout_risk_level", "predicted_exam_readiness"] if (analytics and primary_intent_value != "greeting") else [],
        "memory_used": ["last_subject", "last_intent", "current_topic", "mastery_level", "pruned_history"]
    }

    # Dynamic confidence formula = average confidence of EXECUTED agents strictly
    executed_confidences = [step.confidence_score for step in step_logs if step.status in ("completed", "warning") and step.confidence_score > 0]
    dynamic_confidence = round(sum(executed_confidences) / len(executed_confidences), 2) if executed_confidences else 0.85

    result = SwarmExecutionResult(
        user_id=user_id,
        primary_intent=primary_intent_value,
        execution_graph=exec_graph,
        knowledge_graph=graph,
        strategy=strategy,
        plan=structured_plan,
        reflection=reflection,
        analytics=analytics,
        step_logs=step_logs,
        skipped_agents=exec_graph.skipped_agents,
    )

    if primary_intent_value == "greeting":
        result.formatted_response = (
            "Hi Puneeth! Welcome back. 👋\n\n"
            "Ready to continue Database Management Systems, or would you like to study something new today?"
        )
    else:
        try:
            custom_response = ai_client.generate("chat_answer", {"raw_prompt": grounded_prompt, **context_payload})
            if custom_response and len(custom_response.strip()) > 10:
                result.custom_nl_response = custom_response.strip()
        except Exception as exc:
            logger.warning("Orchestrator: Gemini NL generation notice: %s", exc)
        result.formatted_response = build_final_response(result, user_query, learning_ctx)

    session.add_turn(user_query, result.formatted_response, primary_intent_value)

    # Update stateful academic session memory
    update_session(
        user_id,
        last_subject=subject_hint or (graph.subject if graph else "General"),
        current_topic=user_query,
        current_schedule=structured_plan.model_dump() if structured_plan else None,
        last_explanation=result.formatted_response,
        last_retrieved_nodes=[{"id": c.id, "title": c.title} for c in (graph.concepts[:5] if graph else [])]
    )

    total_latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)

    # ── Step 10: Database Persistence of Swarm Telemetry & Grounding Metadata ──
    try:
        from app.models.telemetry_log import SwarmTelemetryLog
        db_log = SwarmTelemetryLog(
            user_id=user_id,
            query=user_query,
            intent=primary_intent_value,
            subject=subject_hint or (graph.subject if graph else "General"),
            active_agents=exec_graph.active_agents,
            skipped_agents=[s.agent_name for s in exec_graph.skipped_agents],
            total_latency_ms=total_latency_ms,
            dynamic_confidence=dynamic_confidence,
            memory_before={
                "last_intent": session.last_intent,
                "last_subject": session.last_subject,
                "current_topic": session.current_topic,
                "mastery_level": session.mastery_level
            },
            memory_after={
                "last_intent": primary_intent_value,
                "last_subject": subject_hint or (graph.subject if graph else "General"),
                "current_topic": user_query,
                "mastery_level": session.mastery_level
            },
            step_logs=[s.model_dump() for s in step_logs],
            reflection_audit=reflection.model_dump() if reflection else None,
            planner_output=structured_plan.model_dump() if structured_plan else None,
            grounding_report=grounding_report,
            retrieved_nodes=[{"id": c.id, "title": c.title} for c in (graph.concepts[:5] if graph else [])],
            exact_prompt=grounded_prompt if primary_intent_value != "greeting" else None,
            raw_gemini_output=result.custom_nl_response,
            final_response=result.formatted_response
        )
        db.add(db_log)
        db.commit()
        logger.info("Orchestrator: SwarmTelemetryLog persisted ID=%s user_id=%d", db_log.id, user_id)
    except Exception as db_exc:
        db.rollback()
        logger.warning("Orchestrator: Telemetry persistence notice: %s", db_exc)

    logger.info("Orchestrator done: user=%d steps=%d confidence=%.2f latency=%.2fms", user_id, len(step_logs), dynamic_confidence, total_latency_ms)
    return result
