"""
agents/graph_builder.py — Dynamic Execution Graph Builder

Dynamically constructs directed execution graphs (DAGs) at runtime
based on user intent, required context, and active session goals.
Defines explicit contracts for every agent node.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.agents.models import ExecutionGraph, SkippedAgentLog
from app.agents.intent_classifier import Intent

logger = logging.getLogger(__name__)


class AgentContract(BaseModel):
    agent_name: str
    required_inputs: List[str]
    produced_outputs: List[str]
    side_effects: List[str]
    shared_memory_read: List[str]
    shared_memory_written: List[str]


AGENT_CONTRACTS: Dict[str, AgentContract] = {
    "IntentAgent": AgentContract(
        agent_name="IntentAgent",
        required_inputs=["user_query"],
        produced_outputs=["primary_intent", "entities"],
        side_effects=["Session intent update"],
        shared_memory_read=[],
        shared_memory_written=["last_intent"],
    ),
    "ContextAgent": AgentContract(
        agent_name="ContextAgent",
        required_inputs=["user_query", "primary_intent"],
        produced_outputs=["minimal_context"],
        side_effects=["Context pruning"],
        shared_memory_read=["conversation_history", "last_subject"],
        shared_memory_written=["pruned_history"],
    ),
    "RetrievalAgent": AgentContract(
        agent_name="RetrievalAgent",
        required_inputs=["subject_hint", "user_query"],
        produced_outputs=["top_k_concept_nodes"],
        side_effects=["Semantic search"],
        shared_memory_read=["active_knowledge_graph"],
        shared_memory_written=["retrieved_nodes"],
    ),
    "DocumentAgent": AgentContract(
        agent_name="DocumentAgent",
        required_inputs=["document_id"],
        produced_outputs=["knowledge_graph"],
        side_effects=["DB graph fetch"],
        shared_memory_read=["last_imported_document_id"],
        shared_memory_written=["knowledge_graph_pointers"],
    ),
    "StrategyAgent": AgentContract(
        agent_name="StrategyAgent",
        required_inputs=["knowledge_graph", "avg_mastery"],
        produced_outputs=["learning_strategy"],
        side_effects=[],
        shared_memory_read=["learning_profile"],
        shared_memory_written=["active_strategy"],
    ),
    "PlannerAgent": AgentContract(
        agent_name="PlannerAgent",
        required_inputs=["user_tasks", "available_minutes"],
        produced_outputs=["structured_plan"],
        side_effects=["Time budgeting"],
        shared_memory_read=["user_profile", "active_strategy"],
        shared_memory_written=["last_schedule"],
    ),
    "ReflectionAgent": AgentContract(
        agent_name="ReflectionAgent",
        required_inputs=["structured_plan"],
        produced_outputs=["reflection_audit"],
        side_effects=["Re-plan trigger if overloaded"],
        shared_memory_read=["last_schedule"],
        shared_memory_written=["reflection_audit"],
    ),
    "ReminderAgent": AgentContract(
        agent_name="ReminderAgent",
        required_inputs=["user_tasks"],
        produced_outputs=["active_reminders"],
        side_effects=["Schedule DB alerts"],
        shared_memory_read=["user_tasks"],
        shared_memory_written=["last_reminders"],
    ),
    "AnalyticsAgent": AgentContract(
        agent_name="AnalyticsAgent",
        required_inputs=["user_id"],
        produced_outputs=["analytics_summary"],
        side_effects=["Performance calculation"],
        shared_memory_read=["task_history"],
        shared_memory_written=["analytics_summary"],
    ),
    "TutorAgent": AgentContract(
        agent_name="TutorAgent",
        required_inputs=["minimal_context", "knowledge_graph"],
        produced_outputs=["grounded_tutor_payload"],
        side_effects=["Pedagogical synthesis"],
        shared_memory_read=["retrieved_nodes", "pruned_history"],
        shared_memory_written=["tutor_payload"],
    ),
}


def build_execution_graph(
    intent: Intent,
    user_query: str,
    has_document: bool = False,
    has_time_constraint: bool = False,
) -> ExecutionGraph:
    """
    Construct a dynamic execution graph at runtime.
    Determines active agents, execution sequence, and skipped agents with explicit reasons.
    """
    active_agents: List[str] = ["IntentAgent", "ContextAgent"]
    skipped_agents: List[SkippedAgentLog] = []

    intent_val = intent.value if isinstance(intent, Intent) else str(intent)

    # 1. Greeting / Casual / Small Talk
    if intent in (Intent.GREETING, Intent.GOODBYE, Intent.GRATITUDE, Intent.SMALL_TALK, Intent.CASUAL):
        for agent in [
            "RetrievalAgent", "DocumentAgent", "StrategyAgent",
            "PlannerAgent", "ReflectionAgent", "ReminderAgent",
            "AnalyticsAgent", "TutorAgent"
        ]:
            skipped_agents.append(SkippedAgentLog(
                agent_name=agent,
                skip_reason=f"Query intent '{intent_val}' is conversational; skipping heavy reasoning and scheduling steps."
            ))

    # 2. Learning Analytics Query
    elif intent == Intent.LEARNING_ANALYTICS:
        active_agents.append("AnalyticsAgent")
        for agent in [
            "RetrievalAgent", "DocumentAgent", "StrategyAgent",
            "PlannerAgent", "ReflectionAgent", "ReminderAgent", "TutorAgent"
        ]:
            skipped_agents.append(SkippedAgentLog(
                agent_name=agent,
                skip_reason="Analytics query specifically requests performance metrics; tutoring/planning skipped."
            ))

    # 3. Tutor / Explanation / Quiz
    elif intent in (Intent.TUTOR, Intent.INFORMATION_QUERY):
        active_agents.extend(["RetrievalAgent", "DocumentAgent", "TutorAgent"])
        for agent in ["StrategyAgent", "PlannerAgent", "ReflectionAgent", "ReminderAgent", "AnalyticsAgent"]:
            skipped_agents.append(SkippedAgentLog(
                agent_name=agent,
                skip_reason=f"Intent '{intent_val}' focuses on conceptual explanation; scheduling and reflection skipped."
            ))

    # 4. Study Planning / Schedule Constraint
    elif intent in (Intent.STUDY_PLANNING, Intent.SCHEDULE_CONSTRAINT, Intent.PRIORITY_CALCULATION):
        if has_document:
            active_agents.extend(["RetrievalAgent", "DocumentAgent"])
        else:
            skipped_agents.extend([
                SkippedAgentLog(agent_name="RetrievalAgent", skip_reason="No document selected for study planning."),
                SkippedAgentLog(agent_name="DocumentAgent", skip_reason="No active document context in session.")
            ])

        active_agents.extend([
            "StrategyAgent",
            "PlannerAgent",
            "ReflectionAgent",
            "ReminderAgent",
            "AnalyticsAgent"
        ])
        skipped_agents.append(SkippedAgentLog(
            agent_name="TutorAgent",
            skip_reason="Study planning prioritizes task schedule allocation over topic explanations."
        ))

    # 5. Default / Fallback
    else:
        active_agents.extend(["StrategyAgent", "TutorAgent"])
        for agent in ["RetrievalAgent", "DocumentAgent", "PlannerAgent", "ReflectionAgent", "ReminderAgent", "AnalyticsAgent"]:
            skipped_agents.append(SkippedAgentLog(
                agent_name=agent,
                skip_reason="General query; invoking default strategy and tutor agents."
            ))

    return ExecutionGraph(
        intent=intent_val,
        active_agents=active_agents,
        skipped_agents=skipped_agents,
        execution_order=active_agents,
    )


def visualize_runtime_graph(active_agents: List[str]) -> str:
    """Generate a clean ASCII tree representation of the active runtime execution graph."""
    if not active_agents:
        return "User\n └── (No agents executed)"
    lines = ["User"]
    indent = " "
    for i, agent in enumerate(active_agents):
        prefix = "└── " if i == len(active_agents) - 1 else "├── "
        lines.append(f"{indent}{prefix}{agent}")
        indent += "  "
    lines.append(f"{indent}└── Gemini (Grounded LLM)")
    return "\n".join(lines)
