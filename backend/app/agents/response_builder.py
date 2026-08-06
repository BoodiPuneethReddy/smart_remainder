"""
agents/response_builder.py — Personal Academic Mentor Response Generator.

Formats agent execution payloads into clean, natural mentor responses.
Completely eliminates robotic machine headers like 'ReflectionAgent', 'StrategyAgent',
or 'I analyzed your document'.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from app.agents.models import SwarmExecutionResult

logger = logging.getLogger(__name__)


def _format_minutes(minutes: int) -> str:
    if minutes >= 60:
        h = minutes // 60
        m = minutes % 60
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{minutes}m"


def _mastery_label(score: float) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Developing"
    if score >= 40:
        return "Needs Work"
    return "Critical Gap"


def build_final_response(
    result: SwarmExecutionResult,
    user_query: str = "",
    learning_ctx: Optional[Dict[str, Any]] = None,
    history: Optional[list] = None,
) -> str:
    """
    Builds a clean, human, conversational AI Coach response.
    - Friendly, short, and productivity focused.
    - Zero machine telemetry headers, agent logs, or raw stats dumps.
    - Automatically redirects learning requests to Tutor Mode.
    """
    intent = (result.primary_intent or "unknown").lower()
    q_lower = user_query.lower().strip()

    # ── 1. Learning Request Handoff to AI Tutor ──────────────────────────────
    learning_triggers = ["explain", "teach me", "quiz me", "revise", "bcnf", "normalization", "interview questions", "start learning", "what is", "how does"]
    if intent in ("tutor", "information_query") or any(kw in q_lower for kw in learning_triggers):
        return "Opening Tutor Mode... 🎓 Launching your dedicated learning workspace..."

    # ── 2. Greetings ──────────────────────────────────────────────────────────
    if intent in ("greeting", "casual", "small_talk") or any(kw in q_lower for kw in ["hi", "hello", "hey", "good morning", "good afternoon"]):
        return "Hi! 👋 Welcome back! What would you like to work on today?"

    # ── 3. Goodbyes ───────────────────────────────────────────────────────────
    if intent == "goodbye" or any(kw in q_lower for kw in ["bye", "goodbye", "see you", "cya", "later"]):
        return "See you later! Keep up the great work. 😊"

    # ── 4. Gratitude ──────────────────────────────────────────────────────────
    if intent == "gratitude" or any(kw in q_lower for kw in ["thank you", "thanks", "thx", "appreciate"]):
        return "You're very welcome! Let me know whenever you're ready to plan your next session. 😊"

    # ── 5. Task Completion ───────────────────────────────────────────────────
    if intent == "task_completion" or "completed all" in q_lower or "finished all" in q_lower or "done with all" in q_lower:
        return "🎉 Awesome work! You completed everything on today's schedule. That's excellent consistency. Enjoy the rest of your day—you've earned it!"

    # ── 6. Low Energy / Motivation ───────────────────────────────────────────
    if "don't want to study" in q_lower or "not in the mood" in q_lower or "feeling lazy" in q_lower or intent == "motivation":
        return "That's okay. Everyone has off days. Even spending just 15 minutes reviewing something keeps your momentum alive. Small progress is still progress."

    # ── 7. Extra Time ─────────────────────────────────────────────────────────
    if "extra time" in q_lower or "free time" in q_lower:
        return "Great! Since you have extra time, I'd recommend opening Tutor Mode and studying another topic while you're fresh."

    # ── 8. Study Planning / Scheduling ────────────────────────────────────────
    if result.plan and result.plan.items:
        p = result.plan
        avail = p.available_minutes
        avail_str = f"{avail // 60}h {avail % 60}m" if avail >= 60 else f"{avail}m"
        lines = [f"Here is your optimized schedule for today ({avail_str} total):", ""]

        for i, item in enumerate(p.items[:3], 1):
            mins_str = f"{item.recommended_minutes // 60}h {item.recommended_minutes % 60}m" if item.recommended_minutes >= 60 else f"{item.recommended_minutes}m"
            lines.append(f"{i}. **{item.title}** ({item.subject}) — `{mins_str}`")

        lines.append("")
        lines.append(f"Focus first on **{p.items[0].title}**. Let me know if you'd like to adjust this!")
        return "\n".join(lines)

    return "I'm your AI Study Coach! I can help you plan your daily schedule, manage your tasks, and keep you motivated. For studying or learning topics, ask me to open Tutor Mode!"
