"""
agents/session_state.py — Per-user conversation session state

Lightweight in-memory session store. No Redis, no database, no external deps.
Future Scope: replace _sessions dict with Redis for persistence across restarts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ConversationSession:
    """
    Holds conversation context for a single user session.
    Fields tracked per the Architecture Refinement specification:
      - last_intent
      - last_schedule
      - last_applied_constraints
      - last_imported_document
      - last_completed_subject
      - conversation_timestamp
    """
    last_intent: Optional[str] = None
    last_schedule: Optional[dict] = None         # Most recent build_daily_plan() result
    last_constraints: Optional[dict] = None      # Most recent applied constraints
    last_imported_document_id: Optional[int] = None
    last_completed_subject: Optional[str] = None
    conversation_started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# Global in-memory store: {user_id: ConversationSession}
# Future: Replace with Redis-backed session store
_sessions: dict[int, ConversationSession] = {}


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
