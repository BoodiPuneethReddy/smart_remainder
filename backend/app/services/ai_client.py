"""
services/ai_client.py — AI Inference Client

Architecture:
  AIInferenceClient (Protocol)  — the contract both implementations satisfy
  LocalAIService                — rich template-based NL generation, zero deps
  RemoteAIService               — calls AMD JupyterLab endpoint over HTTP,
                                  automatically falls back to LocalAIService
                                  on any failure

Agents call:  ai_client.generate(task, context) → str
They never branch on which implementation is active — that decision is made
once at startup by get_ai_client().

task must be one of:
  "explain_priority"  — one-sentence explanation of why a task is top priority
  "chat_answer"       — free-text answer to a student's study question
  "reminder_message"  — personalized notification wording for an urgent task
"""

import logging
import random
from datetime import datetime
from typing import Protocol, runtime_checkable

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ─── Contract ──────────────────────────────────────────────────────────────────

VALID_TASKS = {"explain_priority", "chat_answer", "reminder_message"}


@runtime_checkable
class AIInferenceClient(Protocol):
    """The single interface all agents use. Implementations are interchangeable."""

    def generate(self, task: str, context: dict) -> str:
        """
        Generate natural-language text for a given task.

        Args:
            task:    One of "explain_priority", "chat_answer", "reminder_message"
            context: Task-specific dict containing subject, scores, question, etc.

        Returns:
            A natural-language string appropriate for the task.
        """
        ...


# ─── LocalAIService ────────────────────────────────────────────────────────────

class LocalAIService:
    """
    Template-based NL generation — no external dependencies, no model downloads.
    Rich enough to be convincing in a live demo while being 100% deterministic
    and reliable (critical: the demo must never fail because of AI).
    """

    # Templates keyed by (task, dominant_factor_pair)
    _priority_templates = {
        ("urgency", "importance"): [
            "{subject} is your top priority right now — {task_type} due in {days} day(s) and it carries significant weight in your grade.",
            "Focus on {subject} first: the {task_type} is due in {days} day(s) and this type of task has the highest academic impact.",
            "Urgent attention needed for {subject} — only {days} day(s) until the {task_type} and it's a high-stakes assessment.",
        ],
        ("urgency", "weakness"): [
            "{subject} needs immediate attention — the {task_type} is due in {days} day(s) and your historical completion rate on {subject} suggests extra prep time is needed.",
            "Prioritising {subject}: deadline in {days} day(s) combined with lower past performance makes this a critical study target.",
            "{subject} is flagged high-priority — {task_type} due soon and your completion history on this subject is below average.",
        ],
        ("urgency", "effort"): [
            "{subject} is top priority — the {task_type} is due in {days} day(s) and requires approximately {hours}h of focused work.",
            "Act now on {subject}: only {days} day(s) left and ~{hours}h of effort still needed for the {task_type}.",
            "High urgency for {subject} — tight deadline in {days} day(s) with a significant time investment of ~{hours}h remaining.",
        ],
        ("importance", "weakness"): [
            "{subject} is your priority focus — it's a high-stakes {task_type} and your past performance on {subject} shows room to improve.",
            "Study {subject} next: the {task_type} carries major academic weight and your completion rate on this subject is lower than others.",
            "{subject} ranks highest — important {task_type} combined with a historical weakness make it the best use of your study time now.",
        ],
        ("importance", "effort"): [
            "{subject} deserves focused effort — it's a significant {task_type} that requires ~{hours}h of dedicated study time.",
            "Prioritise {subject}: this {task_type} has high academic impact and will need approximately {hours}h to complete well.",
            "{subject} scores highest — the {task_type}'s importance and required effort of ~{hours}h demand your attention now.",
        ],
        ("effort", "weakness"): [
            "{subject} is prioritised because it requires ~{hours}h of work and your historical completion rate suggests this subject needs extra attention.",
            "Focus on {subject} — significant effort (~{hours}h) is needed for the {task_type} and past sessions show this subject benefits from extra practice.",
            "{subject} needs your attention: the {task_type} is effort-intensive (~{hours}h) and your track record on {subject} makes early preparation essential.",
        ],
    }

    _chat_templates = {
        "what_to_study": [
            "Based on your current task list, I recommend studying **{top_subject}** first — it has the highest priority score ({score}/100) due to {reason}. After that, move to **{second_subject}** which is due in {days2} day(s).",
            "Your most urgent focus should be **{top_subject}** (priority {score}/100). {reason}. Once that's under control, shift to **{second_subject}**.",
            "I'd suggest starting with **{top_subject}** — it's your highest-priority task right now ({score}/100) because {reason}. Follow up with **{second_subject}** when you're done.",
        ],
        "how_long": [
            "For **{subject}**, I recommend a {duration}-minute focused session today. Based on the estimated {hours}h total effort and {days} day(s) remaining, spreading ~{daily}h per day will keep you on track.",
            "Plan for {duration} minutes on **{subject}** today. With {days} day(s) until the deadline and {hours}h of total work, a daily study block of ~{daily}h is your target.",
            "I suggest a {duration}-minute session for **{subject}** — that gives you the right daily pace ({daily}h/day) to finish the {hours}h of work before the deadline in {days} day(s).",
        ],
        "weakest_subject": [
            "Looking at your study history, **{subject}** has the most room for improvement — your completion rate there is {rate}% compared to your overall average of {avg}%. I'd recommend scheduling extra practice sessions this week.",
            "Your historical data shows **{subject}** as your weakest area ({rate}% completion rate). Blocking dedicated study time for it will improve both your score and your confidence before the next assessment.",
            "Based on past sessions, **{subject}** needs the most attention — only {rate}% of tasks have been completed on time. Focus a session on fundamentals this week to turn that around.",
        ],
        "schedule": [
            "Here's your recommended study plan for today:\n\n1. **{t1}** — {d1} min ({reason1})\n2. **{t2}** — {d2} min ({reason2})\n3. **{t3}** — {d3} min ({reason3})\n\nTotal: {total} min. Take a 10-minute break between each block.",
            "I've built a balanced plan for your day:\n\n🔴 **{t1}** — {d1} min (highest priority)\n🟡 **{t2}** — {d2} min (upcoming deadline)\n🟢 **{t3}** — {d3} min (keep momentum)\n\nThat's {total} min of focused study with breaks between blocks.",
        ],
        "general": [
            "Based on your current academic workload, here's what I'd recommend: {advice}. Your overall completion rate is {completion}%, which is {assessment}. Keep building momentum!",
            "Looking at your tasks and study history: {advice}. You're at {completion}% completion overall — {assessment}. Small, consistent sessions beat cramming every time.",
            "Here's my analysis of your study situation: {advice}. With {completion}% of tasks completed, you're {assessment}. Focus on the high-priority items first.",
        ],
    }

    _reminder_templates = {
        "critical": [
            "🚨 **Urgent: {subject} {task_type} due TODAY!** You have approximately {hours}h of work remaining. Drop everything and start now — use the Pomodoro technique (25 min on, 5 min break) to power through.",
            "⚡ **{subject} {task_type} — DUE TODAY.** Priority score: {score}/100. Clear your schedule and focus. Even {hours}h of solid effort will make a significant difference.",
            "🔴 **CRITICAL: {subject} {task_type} is due today.** Score: {score}/100. Start immediately — every hour counts now.",
        ],
        "high": [
            "⚠️ **{subject} {task_type} due in {days} day(s).** Priority {score}/100. Plan at least {daily}h of study today to stay on track.",
            "📚 **Reminder: {subject} {task_type} — {days} day(s) away.** With priority score {score}/100, this deserves a dedicated study block today. Recommended: {daily}h.",
            "🟠 **{subject} {task_type} coming up in {days} day(s).** It's ranked high-priority ({score}/100). A focused {daily}h session today will keep you in good shape.",
        ],
        "medium": [
            "📅 **Heads up: {subject} {task_type} in {days} day(s).** Priority {score}/100. A short review session today will reduce stress later — try {daily}h to start.",
            "💡 **Study reminder: {subject}** — {task_type} due in {days} day(s). Priority score: {score}/100. Scheduling even 30–45 minutes today pays off.",
            "🟡 **{subject} {task_type} — {days} day(s) to go.** Don't let it sneak up on you. A small study block now is worth much more than cramming later.",
        ],
    }

    def generate(self, task: str, context: dict) -> str:
        """Dispatch to the appropriate template generator."""
        if task == "explain_priority":
            return self._explain_priority(context)
        elif task == "chat_answer":
            return self._chat_answer(context)
        elif task == "reminder_message":
            return self._reminder_message(context)
        else:
            logger.warning("LocalAIService: unknown task type '%s'", task)
            return f"AI analysis complete for task: {task}."

    def _explain_priority(self, ctx: dict) -> str:
        """Generate a one-sentence priority explanation from sub-scores."""
        subject = ctx.get("subject", "This task")
        task_type = ctx.get("task_type", "task")
        days = ctx.get("days_remaining", 0)
        hours = ctx.get("estimated_hours", 2)
        top_factors = ctx.get("top_factors", ["urgency", "importance"])

        # Normalize factor pair to canonical order
        factor_pair = tuple(sorted(top_factors[:2]))
        templates = self._priority_templates.get(
            factor_pair,
            self._priority_templates[("urgency", "importance")]
        )
        template = random.choice(templates)
        return template.format(
            subject=subject,
            task_type=task_type,
            days=max(0, int(days)),
            hours=round(float(hours), 1),
            daily=round(float(hours) / max(int(days), 1), 1),
        )

    def _chat_answer(self, ctx: dict) -> str:
        """Generate a contextual answer to a student's study question."""
        question = ctx.get("question", "").lower()
        tasks = ctx.get("tasks", [])
        completion_rate = ctx.get("completion_rate", 75)
        weakest_subject = ctx.get("weakest_subject", "")
        top_tasks = sorted(tasks, key=lambda t: t.get("priority_score", 0), reverse=True)

        # Detect question intent
        if any(w in question for w in ["what", "which", "study", "focus", "start"]):
            if len(top_tasks) >= 2:
                t1, t2 = top_tasks[0], top_tasks[1]
                score = round(t1.get("priority_score", 85))
                reason = self._get_priority_reason(t1)
                template = random.choice(self._chat_templates["what_to_study"])
                return template.format(
                    top_subject=t1.get("subject", "your top subject"),
                    score=score,
                    reason=reason,
                    second_subject=t2.get("subject", "your next subject"),
                    days2=max(0, t2.get("days_remaining", 3)),
                )

        if any(w in question for w in ["long", "hours", "minutes", "time", "duration"]):
            if top_tasks:
                t = top_tasks[0]
                hours = t.get("estimated_hours", 3)
                days = max(1, t.get("days_remaining", 1))
                daily = round(hours / days, 1)
                duration = min(120, max(30, int(daily * 60)))
                template = random.choice(self._chat_templates["how_long"])
                return template.format(
                    subject=t.get("subject", "this subject"),
                    duration=duration,
                    hours=hours,
                    days=days,
                    daily=daily,
                )

        if any(w in question for w in ["weak", "worst", "struggle", "difficult", "hard"]):
            if weakest_subject:
                rate = ctx.get("weakest_rate", 55)
                avg = round(completion_rate)
                template = random.choice(self._chat_templates["weakest_subject"])
                return template.format(
                    subject=weakest_subject,
                    rate=rate,
                    avg=avg,
                )

        if any(w in question for w in ["plan", "schedule", "day", "today"]):
            if len(top_tasks) >= 3:
                t1, t2, t3 = top_tasks[0], top_tasks[1], top_tasks[2]
                template = random.choice(self._chat_templates["schedule"])
                return template.format(
                    t1=t1.get("subject", "Subject 1"), d1=90,
                    reason1="highest priority",
                    t2=t2.get("subject", "Subject 2"), d2=60,
                    reason2="upcoming deadline",
                    t3=t3.get("subject", "Subject 3"), d3=45,
                    reason3="keep momentum",
                    total=195,
                )

        # Fallback: general advice
        assessment = "great" if completion_rate >= 80 else "progressing well" if completion_rate >= 60 else "something to improve"
        advice = f"focus on your top {min(3, len(top_tasks))} priority tasks first, then work through the rest systematically"
        template = random.choice(self._chat_templates["general"])
        return template.format(
            advice=advice,
            completion=round(completion_rate),
            assessment=assessment,
        )

    def _reminder_message(self, ctx: dict) -> str:
        """Generate personalized notification wording for an urgent task."""
        subject = ctx.get("subject", "Your subject")
        task_type = ctx.get("task_type", "task")
        days = ctx.get("days_remaining", 1)
        hours = ctx.get("estimated_hours", 2)
        score = round(ctx.get("priority_score", 80))
        daily = round(hours / max(int(days), 1), 1)

        if days <= 0:
            tier = "critical"
        elif days <= 2:
            tier = "high"
        else:
            tier = "medium"

        templates = self._reminder_templates[tier]
        template = random.choice(templates)
        return template.format(
            subject=subject,
            task_type=task_type,
            days=max(0, int(days)),
            hours=round(float(hours), 1),
            score=score,
            daily=daily,
        )

    @staticmethod
    def _get_priority_reason(task: dict) -> str:
        """Build a brief reason string from a task's sub-scores."""
        urgency = task.get("urgency_score", 5)
        importance = task.get("importance_score", 5)
        weakness = task.get("weakness_score", 5)
        days = task.get("days_remaining", 3)

        if urgency >= 8:
            return f"deadline in {max(0, int(days))} day(s)"
        if importance >= 8:
            return "it's a high-stakes assessment"
        if weakness >= 7:
            return "your historical performance on this subject needs a boost"
        return "it has the highest combined priority score"


# ─── RemoteAIService ───────────────────────────────────────────────────────────

class RemoteAIService:
    """
    Calls the AMD JupyterLab inference endpoint over HTTP.
    On any failure (timeout, non-200, connection error), automatically falls
    back to LocalAIService for that request and logs a warning.
    The demo will never hard-fail because AMD is briefly unreachable.
    """

    def __init__(self, url: str, token: str, timeout: float = 10.0):
        self._url = url.rstrip("/") + "/generate"
        self._token = token
        self._timeout = timeout
        self._fallback = LocalAIService()

    def generate(self, task: str, context: dict) -> str:
        try:
            response = httpx.post(
                self._url,
                json={"task": task, "context": context},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("result", data.get("text", ""))
        except Exception as exc:
            logger.warning(
                "RemoteAIService: call to %s failed (%s). Falling back to LocalAIService.",
                self._url,
                exc,
            )
            return self._fallback.generate(task, context)


# ─── Factory ───────────────────────────────────────────────────────────────────

def get_ai_client() -> AIInferenceClient:
    """
    Return the correct AIInferenceClient based on AI_SERVICE_MODE config.
    Called once at startup; the result is passed to agents via dependency injection.
    """
    settings = get_settings()
    mode = settings.ai_service_mode.lower()

    if mode == "remote":
        if not settings.ai_service_token:
            logger.warning(
                "AI_SERVICE_MODE=remote but AI_SERVICE_TOKEN is empty — "
                "falling back to LocalAIService."
            )
            return LocalAIService()
        logger.info(
            "AI client: RemoteAIService → %s (timeout %.1fs)",
            settings.ai_service_url,
            settings.ai_service_timeout,
        )
        return RemoteAIService(
            url=settings.ai_service_url,
            token=settings.ai_service_token,
            timeout=settings.ai_service_timeout,
        )

    logger.info("AI client: LocalAIService (template-based, zero deps)")
    return LocalAIService()
