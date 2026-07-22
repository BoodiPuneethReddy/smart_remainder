"""
services/scoring.py — Deterministic priority scoring engine.

Formula (spec-exact):
  priority_score = (0.40 * urgency + 0.25 * weakness + 0.25 * importance + 0.10 * effort) * 10

Sub-scores are all 0–10. Final priority_score is 0–100.

This module contains ONLY math — no AI calls, no DB queries. Pure functions.
The Planner Agent orchestrates the full pipeline.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional


# ─── Urgency: days-remaining lookup table ──────────────────────────────────────

def compute_urgency_score(days_remaining: float) -> float:
    """
    Convert days remaining until due date to a 0–10 urgency score.
    Exact thresholds from spec.
    """
    if days_remaining <= 0:
        return 10.0
    elif days_remaining <= 1:
        return 9.0
    elif days_remaining <= 2:
        return 8.0
    elif days_remaining <= 4:
        return 6.0
    elif days_remaining <= 7:
        return 4.0
    elif days_remaining <= 14:
        return 2.0
    else:
        return 1.0


# ─── Importance: task-type lookup table ───────────────────────────────────────

_IMPORTANCE_MAP: dict[str, float] = {
    "exam": 10.0,
    "project": 7.0,
    "assignment": 7.0,
    "quiz": 5.0,
    "homework": 3.0,
    "reading": 3.0,
}


def compute_importance_score(task_type: str) -> float:
    """Map task type string to 0–10 importance score."""
    return _IMPORTANCE_MAP.get(task_type.lower(), 5.0)


# ─── Weakness: historical completion rate ─────────────────────────────────────

def compute_weakness_score(
    subject: str,
    sessions: list[dict],  # list of {"subject": str, "task_completed": int}
) -> float:
    """
    weakness = (1 - completion_rate) * 10
    New subjects with no history → 5.0 (neutral).
    """
    subject_sessions = [s for s in sessions if s["subject"].lower() == subject.lower()]
    if not subject_sessions:
        return 5.0

    total = len(subject_sessions)
    completed = sum(1 for s in subject_sessions if s["task_completed"] == 1)
    completion_rate = completed / total
    return (1.0 - completion_rate) * 10.0


# ─── Effort: hours vs time remaining ─────────────────────────────────────────

def compute_effort_score(estimated_hours: float, days_remaining: float) -> float:
    """
    effort = min(10, estimated_hours / max(days_remaining, 0.5))
    Captures tasks that need a lot of work in little time.
    """
    safe_days = max(days_remaining, 0.5)
    return min(10.0, estimated_hours / safe_days)


# ─── Final priority score ─────────────────────────────────────────────────────

def compute_priority(
    task_type: str,
    subject: str,
    due_date: datetime,
    estimated_hours: float,
    sessions: list[dict],
    retention_value: float = 100.0,
) -> dict:
    """
    Compute all sub-scores and the final priority score for one task.

    Returns a dict with:
      priority_score, urgency_score, importance_score, weakness_score,
      effort_score, days_remaining, top_factors (for explanation generation)
    """
    now = datetime.now(timezone.utc)
    # Normalize due_date to UTC
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    days_remaining = (due_date - now).total_seconds() / 86400

    urgency = compute_urgency_score(days_remaining)
    importance = compute_importance_score(task_type)
    weakness = compute_weakness_score(subject, sessions)
    effort = compute_effort_score(estimated_hours, days_remaining)

    # Weighted contributions (weight × sub_score)
    retention_score = (1.0 - (retention_value / 100.0)) * 10.0

    contributions = {
        "urgency": 0.35 * urgency,
        "weakness": 0.20 * weakness,
        "importance": 0.20 * importance,
        "effort": 0.10 * effort,
        "retention": 0.15 * retention_score,
    }

    priority_score = sum(contributions.values()) * 10.0
    priority_score = round(min(100.0, max(0.0, priority_score)), 2)

    # Top 2 factors by weighted contribution → used for explanation template selection
    sorted_factors = sorted(contributions, key=contributions.get, reverse=True)
    top_factors = sorted_factors[:2]

    return {
        "priority_score": priority_score,
        "urgency_score": round(urgency, 2),
        "importance_score": round(importance, 2),
        "weakness_score": round(weakness, 2),
        "effort_score": round(effort, 2),
        "retention_score": round(retention_score, 2),
        "days_remaining": round(days_remaining, 2),
        "top_factors": top_factors,
        "contributions": contributions,
    }


# ─── Explanation template selection ──────────────────────────────────────────

_EXPLANATION_TEMPLATES: dict[tuple, list[str]] = {
    ("urgency", "importance"): [
        "{subject} is top priority — {task_type} due in {days} day(s) and it's a high-stakes assessment.",
        "Focus on {subject} first: {task_type} in {days} day(s) with major academic weight.",
        "Urgent: {subject} {task_type} in {days} day(s) — one of your most important tasks.",
    ],
    ("urgency", "weakness"): [
        "{subject} is top priority — {task_type} due in {days} day(s) and your completion rate on this subject is lower than average.",
        "Act on {subject} now: deadline in {days} day(s) and past performance shows it needs extra prep time.",
        "{subject} is critical — {task_type} coming up in {days} day(s), and history shows this subject is your toughest.",
    ],
    ("urgency", "effort"): [
        "{subject} is top priority — {task_type} in {days} day(s) needs ~{hours}h of focused work.",
        "High urgency for {subject}: only {days} day(s) left and approximately {hours}h of effort required.",
        "Start {subject} now — {task_type} due in {days} day(s) with {hours}h of work remaining.",
    ],
    ("importance", "weakness"): [
        "{subject} is prioritised — high-stakes {task_type} and your historical performance here has room to improve.",
        "Focus on {subject}: important {task_type} combined with a lower completion rate make this your top study target.",
        "{subject} scores highest — the {task_type}'s importance and your past weakness make it the best use of study time now.",
    ],
    ("importance", "effort"): [
        "{subject} is your priority — significant {task_type} requiring ~{hours}h of dedicated preparation.",
        "Prioritise {subject}: high-impact {task_type} with approximately {hours}h of work needed.",
        "{subject} is top priority — important {task_type} that demands ~{hours}h of focused study.",
    ],
    ("weakness", "effort"): [
        "{subject} needs your attention — {task_type} requires ~{hours}h of work and your past completion rate on this subject is below average.",
        "Focus on {subject}: the {task_type} is effort-intensive (~{hours}h) and your track record shows this subject benefits from extra prep.",
        "{subject} is flagged — effort required (~{hours}h) combined with a historical weakness make it your most important study target.",
    ],
    ("effort", "weakness"): [
        "{subject} needs your attention — {task_type} requires ~{hours}h and your historical completion rate on this subject is below average.",
        "Prioritise {subject}: {task_type} demands ~{hours}h of work and past performance shows extra preparation is needed here.",
        "{subject} is high priority — significant effort (~{hours}h) plus historical weakness make early study critical.",
    ],
    ("effort", "urgency"): [
        "{subject} is top priority — {task_type} in {days} day(s) needs ~{hours}h of focused work.",
        "Act now on {subject}: deadline in {days} day(s) with ~{hours}h of effort still required for the {task_type}.",
    ],
    ("weakness", "urgency"): [
        "{subject} is critical — {task_type} in {days} day(s) and lower completion history means this subject needs your best effort.",
        "Prioritise {subject}: deadline in {days} day(s) combined with past performance data makes this your top focus.",
    ],
    ("weakness", "importance"): [
        "{subject} is top priority — high-stakes {task_type} and your historical completion rate on this subject needs a boost.",
        "Focus on {subject}: important {task_type} combined with a documented weakness make this your best study investment.",
    ],
    ("retention", "urgency"): [
        "Priority increased for {subject} — your retention has dropped, and the {task_type} is due in {days} day(s).",
        "Focus on {subject}: memory retention is low and the deadline is in {days} day(s)."
    ],
    ("retention", "weakness"): [
        "Revision needed for {subject}: retention is down on this historically challenging subject.",
        "{subject} requires study — low retention and past completion performance suggest focusing here."
    ],
    ("retention", "importance"): [
        "{subject} is high impact: you need to revise this important {task_type} as retention has decayed.",
        "Crucial review for {subject}: high-stakes task combined with low memory retention."
    ],
}


def generate_explanation_template(
    subject: str,
    task_type: str,
    top_factors: list[str],
    days_remaining: float,
    estimated_hours: float,
) -> str:
    """
    Select and fill a template explanation based on the top 2 scoring factors.
    Falls back gracefully to a generic template if no exact pair is found.
    """
    import random

    pair = tuple(sorted(top_factors[:2]))
    templates = _EXPLANATION_TEMPLATES.get(pair)

    if not templates:
        # Try the reverse order
        pair_rev = (top_factors[0], top_factors[1]) if len(top_factors) >= 2 else pair
        templates = _EXPLANATION_TEMPLATES.get(pair_rev)

    if not templates:
        # Generic fallback
        templates = [
            "{subject} is top priority based on deadline, importance, and study history.",
        ]

    template = random.choice(templates)
    return template.format(
        subject=subject,
        task_type=task_type,
        days=max(0, math.ceil(days_remaining)),
        hours=round(estimated_hours, 1),
    )
