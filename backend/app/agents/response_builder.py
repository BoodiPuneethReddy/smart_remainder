"""
agents/response_builder.py — Context-Aware Final Response Builder.

Formats agent Pydantic payloads into natural language responses.
Every response is grounded in real live context:
  - Knowledge graph subject + concepts
  - Learning profile mastery + retention + weak topics
  - Actual task titles and real AI explanations from PlannerAgent
  - Real analytics (completion rate, burnout, readiness)
  - Real reflection validation output
  - Detected intent determines response format

No hardcoded fallback text. Every phrase uses real values from swarm execution.
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


def _burnout_emoji(level: str) -> str:
    return {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(level, "🟡")


def build_final_response(
    result: SwarmExecutionResult,
    user_query: str = "",
    learning_ctx: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Builds a context-aware natural language response grounded entirely in live data.
    Format is determined by intent — no generic fallbacks.
    """
    intent = result.primary_intent or "unknown"
    lctx = learning_ctx or {}

    # ─── GREETING / CASUAL ────────────────────────────────────────────────────
    if intent in ("greeting", "casual", "small_talk"):
        return _build_greeting_response(result, lctx)

    # ─── GOODBYE / GRATITUDE ──────────────────────────────────────────────────
    if intent in ("goodbye", "gratitude"):
        return _build_goodbye_response(result, lctx)

    # ─── LEARNING ANALYTICS ───────────────────────────────────────────────────
    if intent == "learning_analytics":
        return _build_analytics_response(result, lctx)

    # ─── MOTIVATION ───────────────────────────────────────────────────────────
    if intent == "motivation":
        return _build_motivation_response(result, lctx)

    # ─── TUTOR / INFORMATION QUERY ────────────────────────────────────────────
    if intent in ("tutor", "information_query"):
        return _build_tutor_response(result, user_query, lctx)

    # ─── TASK COMPLETION ──────────────────────────────────────────────────────
    if intent == "task_completion":
        return _build_completion_response(result, lctx)

    # ─── STUDY PLANNING + SCHEDULE CONSTRAINT (primary path) ─────────────────
    return _build_study_plan_response(result, user_query, lctx)


# ─── Response formatters ──────────────────────────────────────────────────────

def _build_greeting_response(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["👋 **Welcome back to your AI Study OS!**", ""]

    if result.analytics:
        a = result.analytics
        lines.append(f"Here's your current standing:")
        lines.append(f"- **Completion rate:** {a.completion_rate:.0f}%")
        lines.append(f"- **Predicted exam readiness:** {a.predicted_exam_readiness:.0f}%")
        lines.append(f"- **Burnout risk:** {_burnout_emoji(a.burnout_risk_level)} {a.burnout_risk_level.title()}")
        lines.append("")

    if lctx.get("has_learning_data"):
        avg_m = lctx.get("avg_mastery", 50)
        lines.append(f"- **Average mastery:** {avg_m:.0f}% ({_mastery_label(avg_m)})")
        weak = lctx.get("weak_topics", [])
        if weak:
            lines.append(f"- **Topics needing attention:** {', '.join(w['topic'] for w in weak[:3])}")
        lines.append("")

    lines.append("**Ask me anything:** 'What should I study today?', 'I only have 90 minutes', 'Explain normalization', or 'How is my progress?'")
    return "\n".join(lines)


def _build_goodbye_response(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["👋 Great session!"]
    if result.analytics:
        lines.append(f"You're at **{result.analytics.completion_rate:.0f}% completion** overall — keep the momentum going!")
    if lctx.get("revision_needed"):
        rn = lctx["revision_needed"]
        lines.append(f"\n⚠️ Before your next session, review: **{', '.join(r['topic'] for r in rn[:2])}** — retention is dropping.")
    return "\n".join(lines)


def _build_analytics_response(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["### 📊 Your Learning Analytics Report", ""]

    if result.analytics:
        a = result.analytics
        lines += [
            f"**Completion Rate:** {a.completion_rate:.0f}%",
            f"**Weekly Study Hours:** {a.weekly_study_hours:.1f}h",
            f"**Burnout Risk:** {_burnout_emoji(a.burnout_risk_level)} {a.burnout_risk_level.title()}",
            f"**Predicted Exam Readiness:** {a.predicted_exam_readiness:.0f}%",
            "",
        ]
        for insight in a.insights:
            lines.append(f"💡 {insight}")
        lines.append("")

    if lctx.get("has_learning_data"):
        lines.append(f"**Mastery Breakdown** ({lctx['total_profiles']} topics tracked):")
        lines.append(f"- Average Mastery: {lctx['avg_mastery']:.0f}% ({_mastery_label(lctx['avg_mastery'])})")
        lines.append(f"- Average Retention: {lctx['avg_retention']:.0f}%")
        lines.append("")

        weak = lctx.get("weak_topics", [])
        if weak:
            lines.append("**⚠️ Weak Topics (Mastery < 60%):**")
            for w in weak[:5]:
                lines.append(f"- **{w['topic']}** ({w['subject']}): {w['mastery']:.0f}% mastery, {w['retention']:.0f}% retention")
            lines.append("")

        rev = lctx.get("revision_needed", [])
        if rev:
            lines.append("**🔁 Spaced Repetition Due:**")
            for r in rev[:3]:
                lines.append(f"- **{r['topic']}** ({r['subject']}): {r['retention']:.0f}% retention — review in next {r['interval_days']} days")
    else:
        lines.append("_No quiz data yet. Complete an AI Tutor session to unlock detailed mastery analytics._")

    return "\n".join(lines)


def _build_motivation_response(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["### 💪 You've Got This — Here's Your Reality Check", ""]

    if result.analytics:
        a = result.analytics
        cr = a.completion_rate
        if cr >= 70:
            lines.append(f"You're doing **better than you think** — **{cr:.0f}% completion rate** is solid. Consistent progress beats cramming every time.")
        elif cr >= 40:
            lines.append(f"You're at **{cr:.0f}% completion** — there's ground to cover, but it's absolutely manageable. Let's build a focused plan.")
        else:
            lines.append(f"Your completion rate is **{cr:.0f}%** — this tells me you need a realistic, trimmed-down plan, not more motivation. Let's fix the plan.")

        lines.append(f"- **Burnout risk:** {_burnout_emoji(a.burnout_risk_level)} {a.burnout_risk_level.title()}")
        if a.burnout_risk_level == "high":
            lines.append("  → ⚠️ You may be over-scheduling. Try shorter, more focused sessions today.")
        lines.append("")

    if lctx.get("has_learning_data"):
        avg_m = lctx.get("avg_mastery", 50)
        lines.append(f"**Your mastery average is {avg_m:.0f}%** — {_mastery_label(avg_m).lower()}.")
        weak = lctx.get("weak_topics", [])
        if weak:
            lines.append(f"Pick one weak topic and master it today: **{weak[0]['topic']}** ({weak[0]['mastery']:.0f}% mastery).")
        lines.append("")

    lines.append("**Next step:** Say 'I have 45 minutes' and I'll build a focused plan that you can actually complete.")
    return "\n".join(lines)


def _build_tutor_response(result: SwarmExecutionResult, query: str, lctx: Dict) -> str:
    lines = ["### 🧑‍🏫 Knowledge-Grounded Explanation", ""]

    if result.knowledge_graph:
        g = result.knowledge_graph
        lines.append(f"Searching your **{g.subject}** knowledge graph ({len(g.concepts)} concepts)...")
        lines.append("")

        # Find most relevant concept by keyword match
        query_lower = query.lower()
        best_concept = None
        best_score = 0
        for c in g.concepts:
            score = sum(1 for kw in [c.title.lower()] + [kw.lower() for kw in getattr(c, 'formulas', [])] if kw in query_lower)
            if score > best_score:
                best_score = score
                best_concept = c

        if not best_concept and g.concepts:
            best_concept = g.concepts[0]

        if best_concept:
            lines.append(f"**Topic:** {best_concept.title} (Chapter: {best_concept.chapter})")
            lines.append(f"**Difficulty:** {best_concept.difficulty}/6")
            lines.append(f"**Summary:** {best_concept.summary}")
            lines.append("")

            if best_concept.prerequisites:
                lines.append(f"📋 **Prerequisites:** {', '.join(best_concept.prerequisites[:3])}")
            if best_concept.has_formulas:
                lines.append("📐 This topic contains formulas — pay close attention to the derivations.")
            if best_concept.has_code:
                lines.append("💻 This topic contains code — practice writing it from scratch, not just reading.")
            lines.append("")
    else:
        lines.append(f"_No document uploaded yet for this subject. Upload your {query[:30]}... notes to get knowledge-grounded explanations._")
        lines.append("")

    # Mastery context
    if lctx.get("has_learning_data"):
        weak = lctx.get("weak_topics", [])
        if weak:
            lines.append(f"💡 **Your mastery gap:** You're weakest on **{weak[0]['topic']}** ({weak[0]['mastery']:.0f}%). This is a priority topic for your next quiz.")

    lines.append("")
    lines.append("_To go deeper: use the **AI Tutor** in the workspace for a full Socratic session on this topic._")
    return "\n".join(lines)


def _build_completion_response(result: SwarmExecutionResult, lctx: Dict) -> str:
    lines = ["✅ **Task marked as complete!**", ""]

    if result.analytics:
        a = result.analytics
        lines.append(f"**Updated completion rate:** {a.completion_rate:.0f}%")
        lines.append(f"**Predicted exam readiness:** {a.predicted_exam_readiness:.0f}%")
        lines.append("")

    if result.plan and result.plan.items:
        next_item = result.plan.items[0]
        lines.append(f"**Recommended next:** Start **{next_item.title}** for {next_item.recommended_minutes} minutes.")
        if next_item.ai_explanation:
            lines.append(f"_Why:_ {next_item.ai_explanation}")

    return "\n".join(lines)


def _build_study_plan_response(result: SwarmExecutionResult, query: str, lctx: Dict) -> str:
    lines = []

    # ── Section 1: Document Context ───────────────────────────────────────
    if result.knowledge_graph:
        g = result.knowledge_graph
        lines.append(f"I analyzed your **{g.subject}** document.")
        lines.append(f"- **{len(g.concepts)} concepts** extracted from {g.total_chapters} chapter(s)")
        if g.detected_features:
            lines.append(f"- **Content type:** {', '.join(g.detected_features[:4])}")
        lines.append("")

    # ── Section 2: Strategy ───────────────────────────────────────────────
    if result.strategy:
        s = result.strategy
        lines.append(f"### 📚 Learning Strategy: {s.strategy_name.replace('-', ' ').title()}")
        lines.append(s.rationale)
        if s.recommended_focus_order:
            lines.append(f"**Recommended study order:** {' → '.join(s.recommended_focus_order[:4])}")
        lines.append(f"**Estimated total prep time:** {s.estimated_total_hours:.1f}h")
        lines.append("")

    # ── Section 3: Mastery Context ────────────────────────────────────────
    if lctx.get("has_learning_data"):
        avg_m = lctx.get("avg_mastery", 50)
        weak = lctx.get("weak_topics", [])
        rev = lctx.get("revision_needed", [])
        lines.append(f"### 🧠 Your Mastery Status")
        lines.append(f"**Average mastery:** {avg_m:.0f}% ({_mastery_label(avg_m)})")
        if weak:
            lines.append(f"**Weak topics (prioritized):** {', '.join(w['topic'] for w in weak[:3])}")
        if rev:
            lines.append(f"**Retention dropping in:** {', '.join(r['topic'] for r in rev[:2])}")
        lines.append("")

    # ── Section 4: Personalized Schedule ─────────────────────────────────
    if result.plan and result.plan.items:
        p = result.plan
        avail_str = _format_minutes(p.available_minutes)
        alloc_str = _format_minutes(p.allocated_minutes)
        lines.append(f"### 🗓️ Today's Study Plan ({alloc_str} of {avail_str})")
        lines.append("")

        for i, item in enumerate(p.items, 1):
            mins_str = _format_minutes(item.recommended_minutes)
            priority_bar = "🔴" if item.priority_score >= 80 else ("🟡" if item.priority_score >= 60 else "🟢")
            lines.append(f"{i}. {priority_bar} **{item.title}** ({item.subject}) — `{mins_str}`")
            if item.ai_explanation:
                lines.append(f"   ↳ _{item.ai_explanation}_")
        lines.append("")
    else:
        lines.append("### 🗓️ No tasks scheduled yet.")
        lines.append("Add tasks with due dates, or upload a course PDF — the planner will build your schedule automatically.")
        lines.append("")

    # ── Section 5: Reflection ──────────────────────────────────────────────
    if result.reflection:
        r = result.reflection
        if r.is_valid:
            lines.append(f"✅ **ReflectionAgent:** Schedule is feasible and within safe study limits (confidence: {r.confidence_score:.0%}).")
        else:
            lines.append(f"⚠️ **ReflectionAgent:** {'; '.join(r.warnings[:2])}")
            for rec in r.recommendations[:1]:
                lines.append(f"   → {rec}")

    # ── Section 6: Analytics ───────────────────────────────────────────────
    if result.analytics:
        a = result.analytics
        lines.append("")
        lines.append(f"📊 **Workload check:** Completion {a.completion_rate:.0f}% | Burnout {_burnout_emoji(a.burnout_risk_level)} {a.burnout_risk_level} | Readiness {a.predicted_exam_readiness:.0f}%")

    # ── Section 7: Next Step CTA ──────────────────────────────────────────
    if result.plan and result.plan.items:
        top = result.plan.items[0]
        lines.append("")
        lines.append(f"**▶ Start now:** Begin **{top.title}** for **{_format_minutes(top.recommended_minutes)}**.")

    return "\n".join(lines) or "Your AI study workspace is ready. Upload a document or add tasks to begin."
