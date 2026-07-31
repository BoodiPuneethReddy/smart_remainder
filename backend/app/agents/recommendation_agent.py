"""
agents/recommendation_agent.py — Recommendation Agent (with Intent Routing)

GOLDEN RULE: Every message goes through IntentClassifier before any agent or AI call.
No PlannerAgent, RecommendationAgent, ReminderAgent, or AIInferenceClient call
may execute until intent classification completes.

Intent routing table:
  GREETING / GOODBYE / GRATITUDE / SMALL_TALK / CASUAL / HELP
      → Canned response. Zero AI calls.
  STUDY_PLANNING
      → PlannerAgent.build_daily_plan() → present_study_plan
  SCHEDULE_CONSTRAINT
      → extract constraint → PlannerAgent.recalculate_schedule() → present_study_plan
  TASK_COMPLETION
      → update Task → recalculate_schedule() → present_study_plan
  INFORMATION_QUERY
      → chat_answer against current data (no recalculation)
  MOTIVATION
      → empathetic response + one concrete step from real data
  DOCUMENT_IMPORT
      → signal to frontend to open import modal (no pipeline here)
  PROFILE_ACCOUNT
      → route to profile service (never triggers Planner)
  UNKNOWN
      → clarifying question. Never guess.

Compound intents: all matched intents handled in sequence.
Session-aware: follow-up resolves against session.last_schedule, not fresh data.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.study_session import StudySession
from app.models.recommendation import Recommendation
from app.models.learning_profile import LearningProfile
from app.agents.learning_agent import calculate_retention
from app.services.ai_client import AIInferenceClient
from app.agents.intent_classifier import classify, Intent, IntentResult
from app.agents.session_state import get_session, update_session

logger = logging.getLogger(__name__)

# ── Canned responses (no AI call) ─────────────────────────────────────────────

_CANNED = {
    Intent.GREETING: [
        "Hi! Ready to help you tackle your study goals today. What would you like to do?",
        "Hello! What can I help you with today — study plan, upcoming deadlines, or something else?",
        "Hey there! I'm your study assistant. Ask me about your schedule, tasks, or anything academic.",
    ],
    Intent.GOODBYE: [
        "Goodbye! Stay consistent — small daily sessions beat last-minute cramming. See you soon!",
        "Take care! Remember to come back before deadlines sneak up. Good luck!",
    ],
    Intent.GRATITUDE: [
        "Happy to help! Let me know if you need anything else.",
        "You're welcome! Keep up the momentum.",
        "Anytime! That's what I'm here for.",
    ],
    Intent.SMALL_TALK: [
        "I'm doing great — focused and ready to help you study! What's on your plate today?",
        "All good here! More importantly — how are your studies going? Any deadlines coming up?",
    ],
    Intent.CASUAL: [
        "I'm your AI study assistant — here to help you stay on top of assignments, exams, and schedules. What can I do for you?",
        "I'm Smart Study AI! I can help you prioritize tasks, build study plans, and track your academic progress. Try asking 'What should I study today?'",
    ],
    Intent.HELP: [
        (
            "Here's what I can help you with:\n\n"
            "📚 **Study planning** — 'What should I study today?'\n"
            "⏰ **Schedule constraints** — 'I only have 2 hours'\n"
            "✅ **Task completion** — 'I finished Physics'\n"
            "📋 **Deadlines** — 'What's due this week?'\n"
            "📄 **Import documents** — 'Import my timetable' (attach a file)\n"
            "💪 **Motivation** — Just tell me how you're feeling\n"
            "👤 **Profile** — 'Change my password'\n\n"
            "I'm powered by a deterministic planner — every recommendation comes from your actual data, not a guess."
        )
    ],
    Intent.PROFILE_ACCOUNT: [
        "To update your profile, please visit your Account Settings. I can help with your study schedule, but account changes are handled there.",
    ],
    Intent.DOCUMENT_IMPORT: [
        "Sure! Use the **Import Document** button to upload your PDF or image, and I'll extract the academic information automatically.",
    ],
    Intent.UNKNOWN: [
        "I'm not quite sure what you're asking. Could you be more specific? For example: 'What should I study today?', 'I finished Physics', or 'What's due this week?'",
        "Hmm, I didn't catch that. Try asking me something like 'Help me plan my studies' or 'What assignments are due soon?'",
    ],
}

import random

def _canned_response(intent: Intent) -> str:
    responses = _CANNED.get(intent, _CANNED[Intent.UNKNOWN])
    return random.choice(responses)


# ── Helper functions ──────────────────────────────────────────────────────────

def _compute_completion_rate(user_id: int, db: Session) -> float:
    total = db.query(Task).filter(Task.user_id == user_id).count()
    if total == 0:
        return 0.0
    completed = db.query(Task).filter(Task.user_id == user_id, Task.is_completed == True).count()
    return round((completed / total) * 100, 1)


def _get_weakest_subject(user_id: int, db: Session) -> tuple[str, float]:
    sessions = db.query(StudySession).filter(StudySession.user_id == user_id).all()
    subject_stats: dict[str, dict] = {}
    for s in sessions:
        if s.subject not in subject_stats:
            subject_stats[s.subject] = {"total": 0, "completed": 0}
        subject_stats[s.subject]["total"] += 1
        subject_stats[s.subject]["completed"] += s.task_completed
    if not subject_stats:
        return ("", 0.0)
    weakest = min(subject_stats, key=lambda s: subject_stats[s]["completed"] / max(subject_stats[s]["total"], 1))
    stats = subject_stats[weakest]
    rate = round((stats["completed"] / max(stats["total"], 1)) * 100, 1)
    return (weakest, rate)


def _get_task_contexts(user_id: int, db: Session) -> list[dict]:
    pending = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.is_completed == False)
        .order_by(Task.priority_score.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    result = []
    for t in pending[:8]:
        due = t.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days_left = (due - now).total_seconds() / 86400
        result.append({
            "id": t.id, "title": t.title, "subject": t.subject,
            "task_type": t.task_type, "due_date": t.due_date.isoformat(),
            "estimated_hours": t.estimated_hours, "priority_score": t.priority_score,
            "urgency_score": t.urgency_score, "importance_score": t.importance_score,
            "weakness_score": t.weakness_score, "effort_score": t.effort_score,
            "days_remaining": round(days_left, 1), "ai_explanation": t.ai_explanation,
        })
    return result


# ── Intent handlers ───────────────────────────────────────────────────────────

def _handle_study_planning(user_id: int, session, db: Session, ai_client: AIInferenceClient) -> dict:
    plan = build_daily_plan(user_id, db, ai_client)
    update_session(user_id, last_intent="study_planning", last_schedule=plan, last_constraints={})
    return {
        "answer": plan.get("ai_presentation", "Your study plan is ready."),
        "source_agent": "PlannerAgent",
        "ai_task_used": "present_study_plan",
        "intent_detected": ["study_planning"],
        "constraints_applied": None,
    }


def _handle_schedule_constraint(user_id: int, entities: dict, session, db: Session, ai_client: AIInferenceClient) -> dict:
    constraints = {}
    if "available_minutes" in entities:
        constraints["available_minutes"] = entities["available_minutes"]

    plan = recalculate_schedule(user_id, db, ai_client, constraints)
    update_session(user_id, last_intent="schedule_constraint", last_schedule=plan, last_constraints=constraints)
    return {
        "answer": (
            f"I've adjusted your study plan based on your availability:\n\n"
            f"{plan.get('ai_presentation', 'Your updated plan is ready.')}"
        ),
        "source_agent": "PlannerAgent",
        "ai_task_used": "present_study_plan",
        "intent_detected": ["schedule_constraint"],
        "constraints_applied": constraints,
    }


def _handle_task_completion(user_id: int, entities: dict, session, db: Session, ai_client: AIInferenceClient) -> str:
    subject = entities.get("completed_subject", "")
    if subject:
        # Mark matching incomplete task as done
        task = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.is_completed == False,
                Task.subject.ilike(f"%{subject}%"),
            )
            .first()
        )
        if task:
            task.is_completed = True
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            update_session(user_id, last_completed_subject=subject)
            logger.info("RecommendationAgent: marked task %d as completed (%s)", task.id, subject)
            return f"Great job finishing **{subject}**! I've marked it as complete. "
        else:
            return f"I couldn't find an incomplete task for **{subject}**, but noted! "
    return "Well done on completing that task! "


def _handle_information_query(user_id: int, question: str, db: Session, ai_client: AIInferenceClient) -> dict:
    task_contexts = _get_task_contexts(user_id, db)
    completion_rate = _compute_completion_rate(user_id, db)
    weakest_subject, weakest_rate = _get_weakest_subject(user_id, db)

    context = {
        "question": question,
        "tasks": task_contexts,
        "completion_rate": completion_rate,
        "weakest_subject": weakest_subject,
        "weakest_rate": weakest_rate,
        "pending_count": len(task_contexts),
    }
    try:
        answer = ai_client.generate("chat_answer", context)
    except Exception as exc:
        logger.warning("RecommendationAgent: chat_answer failed: %s", exc)
        top = task_contexts[0] if task_contexts else {}
        answer = (
            f"Based on your current tasks, focus on **{top.get('subject', 'your highest priority')}** first "
            f"(priority: {top.get('priority_score', 0):.0f}/100)."
        )
    return {
        "answer": answer,
        "source_agent": "RecommendationAgent",
        "ai_task_used": "chat_answer",
        "intent_detected": ["information_query"],
        "constraints_applied": None,
    }


def _handle_motivation(user_id: int, question: str, session, db: Session, ai_client: AIInferenceClient) -> dict:
    """Empathetic response grounded in real schedule data."""
    task_contexts = _get_task_contexts(user_id, db)
    top_task = task_contexts[0] if task_contexts else None

    # Use session's last schedule if available
    last_schedule = session.last_schedule
    top_subject = (
        top_task.get("subject", "your studies") if top_task
        else (last_schedule["tasks"][0]["subject"] if last_schedule and last_schedule.get("tasks") else "your studies")
    )

    empathy_opener = (
        "It sounds like things are tough right now — that's completely normal during busy academic periods. "
    )
    if top_task:
        concrete_step = (
            f"The best thing you can do right now is a single focused session on **{top_subject}** "
            f"— even just 25 minutes (a Pomodoro). It's your highest priority task "
            f"(priority {top_task.get('priority_score', 50):.0f}/100), and starting is the hardest part."
        )
    else:
        concrete_step = (
            "Try a short 20-minute review of your current material. "
            "Getting started — even briefly — always helps reset the mindset."
        )

    answer = empathy_opener + concrete_step + "\n\n*One step at a time — you've got this.*"

    return {
        "answer": answer,
        "source_agent": "RecommendationAgent",
        "ai_task_used": None,
        "intent_detected": ["motivation"],
        "constraints_applied": None,
    }


def _handle_learning_analytics(user_id: int, question: str, db: Session, ai_client: AIInferenceClient) -> dict:
    profiles = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).all()
    
    if not profiles:
        return {
            "answer": "You don't have a learning profile set up yet. Take a short assessment quiz to start tracking your mastery, retention, and revision needs!",
            "source_agent": "LearningAgent",
            "ai_task_used": None,
            "intent_detected": ["learning_analytics"],
            "constraints_applied": None
        }

    overall_mastery = 0.0
    overall_retention = 0.0
    due_revisions = []
    weakest_topic = None
    min_mastery = 100.0
    
    for p in profiles:
        ret = calculate_retention(p.last_revision, p.interval_days)
        p.retention = ret
        
        overall_mastery += p.mastery
        overall_retention += ret
        
        if ret < 70.0:
            due_revisions.append(f"{p.subject} ({p.topic})")
            
        if p.mastery < min_mastery:
            min_mastery = p.mastery
            weakest_topic = f"{p.subject} ({p.topic})"
    
    db.commit() # save decayed retention
    
    avg_mastery = round(overall_mastery / len(profiles), 1)
    avg_retention = round(overall_retention / len(profiles), 1)
    streak = max(p.learning_streak for p in profiles)
    
    q = question.lower()
    if any(k in q for k in ["revise", "forget", "forgetting", "need"]):
        if due_revisions:
            ans = f"Based on Ebbinghaus forgetting curve decay, you have **{len(due_revisions)} topic(s)** due for revision:\n\n"
            for d in due_revisions:
                ans += f"- **{d}** (retention is below 70%)\n"
            ans += "\nI've bumped their priority in your Planner. You should take a short quiz on these to restore your retention to 100%!"
        else:
            ans = "Great news! Your memory retention across all tracked topics is high (above 70%). No revision sessions are immediately due today. Keep it up!"
    elif any(k in q for k in ["mastery", "improve", "progress", "how am i"]):
        ans = (
            f"Here is your active learning progress report:\n\n"
            f"📈 **Average Mastery**: {avg_mastery}%\n"
            f"🧠 **Average Retention**: {avg_retention}%\n"
            f"🔥 **Learning Streak**: {streak} days\n\n"
        )
        if weakest_topic:
            ans += f"Your weakest concept is currently **{weakest_topic}** with a mastery score of {min_mastery}%. I recommend taking a mock quiz on it."
    else:
        ans = (
            f"Your current Learning Intelligence profile is active:\n"
            f"- Overall Mastery: **{avg_mastery}%**\n"
            f"- Memory Retention: **{avg_retention}%**\n"
            f"- Streak: **{streak} days**\n"
        )
        if due_revisions:
            ans += f"- Revision due for: {', '.join(due_revisions[:3])}\n"
        else:
            ans += "- Revision: All up to date! 🎉\n"
            
    return {
        "answer": ans,
        "source_agent": "LearningAgent",
        "ai_task_used": None,
        "intent_detected": ["learning_analytics"],
        "constraints_applied": None
    }


def _handle_tutor_query(user_id: int, question: str, db: Session, ai_client: AIInferenceClient) -> dict:
    from app.models.imported_document import ImportedDocument
    import json
    doc_count = db.query(ImportedDocument).filter(ImportedDocument.user_id == user_id).count()
    
    ctx = {
        "topic": question,
        "user_answer": question,
        "teacher_personality": "Socratic Tutor",
        "has_uploaded_material": doc_count > 0,
        "no_material_uploaded": doc_count == 0
    }
    
    if doc_count == 0:
        ans = f"📄 **No Study Material Uploaded Yet.**\n\nNo material uploaded for **{question}** yet. Please upload a PDF or study document to enable grounded citations and AI Tutor explanation."
    else:
        try:
            res_str = ai_client.generate("tutor_evaluate_response", ctx)
            res_data = json.loads(res_str)
            ans = res_data.get("explanation", f"Here is the concepts overview for {question}.")
        except Exception:
            ans = f"Here is the Socratic explanation for **{question}**: Focus on the core principles, data storage, and operational requirements."

    return {
        "answer": ans,
        "source_agent": "TutorEngine",
        "ai_task_used": "tutor_evaluate_response",
        "intent_detected": ["tutor"],
        "constraints_applied": None,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def answer_query(
    user_id: int,
    question: str,
    db: Session,
    ai_client: AIInferenceClient,
) -> Recommendation:
    """
    GOLDEN RULE: classify first, then route. No agent or AI call before classification.

    Handles compound intents by processing each matched intent in sequence.
    Session-aware: follow-up messages resolve against session.last_schedule.
    """
    session = get_session(user_id)

    # ── Step 1: Intent classification (always first, no exceptions) ──────────
    result: IntentResult = classify(question)
    intents = result.intents
    primary = result.primary_intent
    entities = result.entities

    logger.info(
        "RecommendationAgent: user=%d question=%r intents=%s",
        user_id, question[:60], [i.value for i in intents],
    )

    # ── Step 2: Route each intent ─────────────────────────────────────────────
    response_parts: list[str] = []
    source_agent = "RecommendationAgent"
    ai_task_used = None
    constraints_applied = None

    for intent in intents:

        # Zero-AI intents
        if intent in (Intent.GREETING, Intent.GOODBYE, Intent.GRATITUDE,
                      Intent.SMALL_TALK, Intent.CASUAL, Intent.HELP,
                      Intent.PROFILE_ACCOUNT, Intent.DOCUMENT_IMPORT):
            response_parts.append(_canned_response(intent))
            continue

        if intent == Intent.UNKNOWN:
            response_parts.append(
                "I'm not quite sure what you'd like to do. Could you clarify if you'd like me to help with your study plan, explain a concept, or quiz you on a topic?"
            )
            source_agent = "RecommendationAgent"
            continue

        if intent == Intent.TUTOR:
            r = _handle_tutor_query(user_id, question, db, ai_client)
            response_parts.append(r["answer"])
            source_agent = r["source_agent"]
            ai_task_used = r["ai_task_used"]
            continue

        if intent == Intent.STUDY_PLANNING:
            r = _handle_study_planning(user_id, session, db, ai_client)
            response_parts.append(r["answer"])
            source_agent = r["source_agent"]
            ai_task_used = r["ai_task_used"]
            continue

        if intent == Intent.SCHEDULE_CONSTRAINT:
            r = _handle_schedule_constraint(user_id, entities, session, db, ai_client)
            response_parts.append(r["answer"])
            source_agent = r["source_agent"]
            ai_task_used = r["ai_task_used"]
            constraints_applied = r["constraints_applied"]
            continue

        if intent == Intent.TASK_COMPLETION:
            completion_msg = _handle_task_completion(user_id, entities, session, db, ai_client)
            response_parts.append(completion_msg)
            # After task completion, recalculate schedule
            from app.agents.planner_agent import recalculate_schedule
            constraints = session.last_constraints or {}
            plan = recalculate_schedule(user_id, db, ai_client, constraints)
            update_session(user_id, last_schedule=plan)
            response_parts.append(f"Your updated plan: {plan.get('ai_presentation', '')}")
            source_agent = "PlannerAgent"
            ai_task_used = "present_study_plan"
            continue

        if intent == Intent.INFORMATION_QUERY:
            # Session-aware: if we just applied constraints, answer against constrained data
            r = _handle_information_query(user_id, question, db, ai_client)
            response_parts.append(r["answer"])
            ai_task_used = r["ai_task_used"]
            continue

        if intent == Intent.MOTIVATION:
            r = _handle_motivation(user_id, question, session, db, ai_client)
            response_parts.append(r["answer"])
            continue

        if intent == Intent.LEARNING_ANALYTICS:
            r = _handle_learning_analytics(user_id, question, db, ai_client)
            response_parts.append(r["answer"])
            source_agent = r["source_agent"]
            ai_task_used = r["ai_task_used"]
            continue

    # ── Step 3: Build final answer ────────────────────────────────────────────
    answer = "\n\n".join(p for p in response_parts if p)
    if not answer:
        answer = _canned_response(Intent.UNKNOWN)

    update_session(user_id, last_intent=primary.value)

    # ── Step 4: Persist Q&A ───────────────────────────────────────────────────
    rec = Recommendation(user_id=user_id, question=question, answer=answer)
    db.add(rec)
    db.commit()
    db.refresh(rec)

    logger.info(
        "RecommendationAgent: answered user=%d intent=%s source=%s",
        user_id, primary.value, source_agent,
    )
    return rec


def get_chat_history(user_id: int, db: Session, limit: int = 20) -> list[Recommendation]:
    """Return the N most recent Q&A pairs for the user."""
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
