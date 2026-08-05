"""
agents/context_agent.py — Context Minimization Agent

Filters multi-turn conversation history, planner states, mastery scores,
and document references to return a minimal context payload.
Prevents flooding LLM prompts with unnecessary data.
"""

import logging
from typing import List, Dict, Any, Optional
from app.agents.models import MinimalContext
from app.agents.session_state import ConversationSession

logger = logging.getLogger(__name__)


def build_minimal_context(
    user_query: str,
    intent: str,
    session: ConversationSession,
    subject_hint: Optional[str] = None,
    time_limit_minutes: Optional[int] = None,
) -> MinimalContext:
    """
    Selectively prunes context to include only items relevant to the current user query.
    """
    # 1. Prune multi-turn conversation history (keep last 3 relevant turns max)
    pruned_history: List[Dict[str, str]] = []
    recent_history = session.history[-3:] if session.history else []
    for turn in recent_history:
        pruned_history.append({
            "user_query": turn.user_query,
            "bot_response": turn.bot_response[:300] + "..." if len(turn.bot_response) > 300 else turn.bot_response
        })

    # 2. Extract time constraints if mentioned
    resolved_time = time_limit_minutes or session.last_time_limit

    minimal_ctx = MinimalContext(
        user_query=user_query,
        primary_intent=intent,
        subject_hint=subject_hint or session.last_subject or "DBMS",
        pruned_history=pruned_history,
        time_constraint_minutes=resolved_time,
    )

    logger.info(
        "ContextAgent: Minimal Context pruned history to %d turns for intent '%s'.",
        len(pruned_history), intent
    )

    return minimal_ctx
