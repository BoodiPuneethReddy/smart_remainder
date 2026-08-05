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
    Builds a clean, human, conversational academic response.
    Completely free of robotic agent names or static machine headers.
    """
    intent = result.primary_intent or "unknown"
    lctx = learning_ctx or {}

    # If Gemini or AI Client generated a custom mentor explanation in result, prefer it
    if hasattr(result, "custom_nl_response") and result.custom_nl_response:
        return result.custom_nl_response

    # ─── GREETING / CASUAL ────────────────────────────────────────────────────
    if intent in ("greeting", "casual", "small_talk"):
        return _build_natural_greeting(result, lctx)

    # ─── TUTOR / INFORMATION QUERY ────────────────────────────────────────────
    if intent in ("tutor", "information_query"):
        return _build_natural_tutor(result, user_query, lctx)

    # ─── LEARNING ANALYTICS ───────────────────────────────────────────────────
    if intent == "learning_analytics":
        return _build_natural_analytics(result, lctx)

    # ─── MOTIVATION ───────────────────────────────────────────────────────────
    if intent == "motivation":
        return _build_natural_motivation(result, lctx)

    # ─── STUDY PLANNING / SCHEDULE ────────────────────────────────────────────
    return _build_natural_study_plan(result, user_query, lctx)


def _build_natural_greeting(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["Hello! Welcome back to your study session. 👋", ""]
    if result.analytics:
        lines.append(f"• **Current Task Completion:** {result.analytics.completion_rate:.0f}%")
        lines.append(f"• **Predicted Exam Readiness:** {result.analytics.predicted_exam_readiness:.0f}%")
    if lctx.get("has_learning_data"):
        avg_m = lctx.get("avg_mastery", 50)
        lines.append(f"• **Average Mastery:** {avg_m:.0f}% ({_mastery_label(avg_m)})")
        weak = lctx.get("weak_topics", [])
        if weak:
            lines.append(f"• **Focus Topics:** {', '.join(w['topic'] for w in weak[:2])}")
        lines.append("")

    lines.append("What would you like to accomplish today? Ask me to explain a concept, build a custom schedule, or review your weak topics.")
    return "\n".join(lines)


def _build_natural_tutor(result: SwarmExecutionResult, query: str, lctx: Dict) -> str:
    lines = []
    if result.knowledge_graph and result.knowledge_graph.concepts:
        g = result.knowledge_graph
        query_lower = query.lower()
        best_concept = None
        for c in g.concepts:
            if c.title.lower() in query_lower:
                best_concept = c
                break
        if not best_concept:
            best_concept = g.concepts[0]

        lines.append(f"### {best_concept.title}")
        lines.append(best_concept.summary)
        lines.append("")
        if best_concept.prerequisites:
            lines.append(f"**Prerequisites to keep in mind:** {', '.join(best_concept.prerequisites[:3])}")
    else:
        lines.append(f"Here is what you need to know regarding **{query}**:")
        lines.append("This concept is foundational. Let's break down the key principles step-by-step.")

    return "\n".join(lines)


def _build_natural_analytics(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["### 📊 Learning Progress Summary", ""]
    if result.analytics:
        a = result.analytics
        lines.append(f"• **Task Completion:** {a.completion_rate:.0f}%")
        lines.append(f"• **Predicted Readiness:** {a.predicted_exam_readiness:.0f}%")
        lines.append(f"• **Burnout Status:** {a.burnout_risk_level.title()}")
        lines.append("")

    if lctx.get("has_learning_data"):
        lines.append(f"• **Average Mastery:** {lctx['avg_mastery']:.0f}% ({_mastery_label(lctx['avg_mastery'])})")
        lines.append(f"• **Average Retention:** {lctx['avg_retention']:.0f}%")
        lines.append("")

    if lctx.get("weak_topics"):
        lines.append("**Key Areas for Improvement:**")
        for w in lctx["weak_topics"][:3]:
            lines.append(f"• {w['topic']} ({w['mastery']:.0f}% mastery)")

    return "\n".join(lines)


def _build_natural_motivation(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["### 💪 Performance Check-In", ""]
    if result.analytics:
        a = result.analytics
        lines.append(f"You're at **{a.completion_rate:.0f}% task completion**.")
        if a.burnout_risk_level == "high":
            lines.append("Take a short break—quality study time is better than pushing through exhaustion.")
        else:
            lines.append("Consistent, focused blocks will get you to 100% exam readiness.")
    return "\n".join(lines)


def _build_natural_study_plan(result: SwarmExecutionResult, query: str, lctx: Dict) -> str:
    lines = []
    if result.plan and result.plan.items:
        p = result.plan
        avail = p.available_minutes
        avail_str = f"{avail // 60}h {avail % 60}m" if avail >= 60 else f"{avail}m"
        lines.append(f"Here is your recommended study plan for **{avail_str}**:")
        lines.append("")

        for i, item in enumerate(p.items, 1):
            mins_str = f"{item.recommended_minutes // 60}h {item.recommended_minutes % 60}m" if item.recommended_minutes >= 60 else f"{item.recommended_minutes}m"
            lines.append(f"{i}. **{item.title}** ({item.subject}) — `{mins_str}`")
            if item.ai_explanation:
                lines.append(f"   _{item.ai_explanation}_")
        lines.append("")
        lines.append(f"**Action Plan:** Start with **{p.items[0].title}** to tackle high-priority topics first.")
    else:
        lines.append("I can help you build a personalized study schedule. Let me know how much time you have today (e.g. 'I have 2 hours') or upload your course materials.")

    return "\n".join(lines)
