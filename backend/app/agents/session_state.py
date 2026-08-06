"""
agents/session_state.py — Stateful Conversation Memory & Session Store.

Holds persistent academic state across multi-turn sessions:
  - Current subject, topic, chapter, document
  - Current goal, strategy, weak concept, and schedule
  - Mastery level (Beginner, Intermediate, Advanced)
  - Full turn history for multi-turn reasoning ("Why?", "Make it 30 mins", "Quiz me", "Make it harder")
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


@dataclass
class ConversationTurn:
    user_query: str
    bot_response: str
    intent: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConversationSession:
    """
    Holds persistent multi-turn conversation state for a single user session.
    """
    last_intent: Optional[str] = None
    last_query: Optional[str] = None
    last_subject: Optional[str] = None
    last_time_limit: Optional[int] = None        # minutes
    last_schedule: Optional[dict] = None         # Most recent build_daily_plan() result
    last_constraints: Optional[dict] = None      # Most recent applied constraints
    last_imported_document_id: Optional[int] = None
    last_completed_subject: Optional[str] = None

    # Stateful Academic Memory Fields
    current_topic: Optional[str] = None
    current_chapter: Optional[str] = None
    current_document: Optional[str] = None
    current_goal: str = "Mastery"
    current_strategy: Optional[str] = None
    current_weak_concept: Optional[str] = None
    mastery_level: str = "Intermediate"          # Beginner (<40%), Intermediate (40-75%), Advanced (>75%)

    history: List[ConversationTurn] = field(default_factory=list)
    conversation_started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def add_turn(self, query: str, response: str, intent: str) -> None:
        self.history.append(ConversationTurn(user_query=query, bot_response=response, intent=intent))
        # Retain last 15 turns
        if len(self.history) > 15:
            self.history = self.history[-15:]
        self.last_query = query
        self.last_intent = intent

    def get_context_summary(self) -> str:
        if not self.history:
            return ""
        recent = self.history[-3:]
        return " | ".join(f"Q: {t.user_query} → A: {t.bot_response[:60]}..." for t in recent)


# Global in-memory store: {user_id: ConversationSession}
_sessions: Dict[int, ConversationSession] = {}


def get_session(user_id: int) -> ConversationSession:
    """Get or create a session for the given user."""
    if user_id not in _sessions:
        _sessions[user_id] = ConversationSession()
    return _sessions[user_id]


def update_session(user_id: int, **kwargs) -> ConversationSession:
    """Update specific fields on a user's session."""
    session = get_session(user_id)
    for key, val in kwargs.items():
        if hasattr(session, key) and val is not None:
            setattr(session, key, val)
    return session


def clear_session(user_id: int) -> None:
    """Clear session data for the given user."""
    if user_id in _sessions:
        del _sessions[user_id]
