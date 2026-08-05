"""
agents/session_state.py — Per-user multi-turn conversation session state.

Holds conversation history, subject context, previous constraints, and topic memory.
Allows follow-up queries (e.g. "What about tomorrow?", "Make it 30 mins", "Explain chapter 2")
to inherit previous intent, subject domain, and schedule parameters seamlessly.
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
    Holds multi-turn conversation context for a single user session.
    """
    last_intent: Optional[str] = None
    last_query: Optional[str] = None
    last_subject: Optional[str] = None
    last_time_limit: Optional[int] = None        # minutes
    last_schedule: Optional[dict] = None         # Most recent build_daily_plan() result
    last_constraints: Optional[dict] = None      # Most recent applied constraints
    last_imported_document_id: Optional[int] = None
    last_completed_subject: Optional[str] = None
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
    """Update specific session fields for a user."""
    session = get_session(user_id)
    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)
    return session


def clear_session(user_id: int) -> None:
    """Clear the session for a user (e.g., on logout)."""
    _sessions.pop(user_id, None)
