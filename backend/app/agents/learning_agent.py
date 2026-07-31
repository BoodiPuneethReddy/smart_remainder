"""
agents/learning_agent.py — Learning Agent

Responsibilities:
1. Update Mastery / Confidence score based on quiz scores.
2. Calculate memory retention using the Ebbinghaus forgetting curve.
3. Schedule spaced repetition revision intervals.
4. Trigger PlannerAgent task priority recalculations.

All calculations are 100% deterministic and unit-testable.
"""

import math
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.learning_profile import LearningProfile
from app.models.task import Task

logger = logging.getLogger(__name__)

# Spaced repetition intervals in days
SR_INTERVALS = [1, 3, 7, 14, 30]

# Quiz score evaluation thresholds
QUIZ_HIGH_THRESHOLD: float = 80.0
QUIZ_LOW_THRESHOLD: float = 60.0

# Memory retention score limits
MIN_RETENTION_SCORE: float = 10.0
MAX_RETENTION_SCORE: float = 100.0


def calculate_retention(last_revision: datetime, interval_days: int) -> float:
    """
    Deterministic memory retention score based on the Ebbinghaus Forgetting Curve.
    Formula: R = e^(-t / S) * 100
    - t: time elapsed in days since last revision.
    - S: memory strength factor (derived from spaced repetition interval).
    """
    if last_revision.tzinfo is None:
        last_revision = last_revision.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    elapsed_seconds = (now - last_revision).total_seconds()
    elapsed_days = max(0.0, elapsed_seconds / 86400.0)
    
    # S scales with interval_days. Slower decay if interval is larger.
    # If interval_days is 7, and elapsed_days is 7, R = e^(-7/14) = e^(-0.5) ~ 60.6%
    strength = float(max(1, interval_days)) * 2.0
    
    retention = math.exp(-elapsed_days / strength) * 100.0
    return round(max(MIN_RETENTION_SCORE, min(MAX_RETENTION_SCORE, retention)), 1)


def schedule_revision(current_interval: int, quiz_score: float) -> int:
    """
    Deterministic spaced repetition interval scheduler.
    Increases interval on success, reduces on failure.
    """
    try:
        idx = SR_INTERVALS.index(current_interval)
    except ValueError:
        # Fallback to closest interval
        idx = 0
        for i, val in enumerate(SR_INTERVALS):
            if val <= current_interval:
                idx = i

    if quiz_score >= QUIZ_HIGH_THRESHOLD:
        # Increase interval
        next_idx = min(len(SR_INTERVALS) - 1, idx + 1)
        return SR_INTERVALS[next_idx]
    elif quiz_score < QUIZ_LOW_THRESHOLD:
        # Decrease interval
        prev_idx = max(0, idx - 1)
        return SR_INTERVALS[prev_idx]
    else:
        # Keep same interval
        return SR_INTERVALS[idx]


def update_learning_profile(
    db: Session,
    user_id: int,
    subject: str,
    topic: str,
    quiz_score: float,
    correct_count: int,
    total_questions: int,
    study_hours: float = 0.0,
) -> LearningProfile:
    """
    Update mastery, confidence, retention, and spaced repetition intervals
    deterministically after a quiz.
    """
    # Fetch or create learning profile
    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == user_id,
            LearningProfile.subject.ilike(subject.strip()),
            LearningProfile.topic.ilike(topic.strip()),
        )
        .first()
    )

    now = datetime.now(timezone.utc)

    if not profile:
        profile = LearningProfile(
            user_id=user_id,
            subject=subject.strip(),
            topic=topic.strip(),
            mastery=50.0,
            confidence=50.0,
            retention=100.0,
            attempts_count=0,
            correct_count=0,
            avg_quiz_score=0.0,
            study_hours=0.0,
            revision_count=0,
            learning_streak=1,
            interval_days=1,
            last_revision=now,
        )
        db.add(profile)
        db.flush()

    # Calculate streak
    last_rev = profile.last_revision
    if last_rev.tzinfo is None:
        last_rev = last_rev.replace(tzinfo=timezone.utc)
    
    days_since_last = (now - last_rev).total_seconds() / 86400.0
    if 0.8 <= days_since_last <= 1.8:
        profile.learning_streak += 1
    elif days_since_last > 1.8:
        profile.learning_streak = 1  # reset streak

    # Update basic stats
    profile.attempts_count += total_questions
    profile.correct_count += correct_count
    profile.study_hours += study_hours
    profile.revision_count += 1
    profile.last_revision = now

    # Update average quiz score
    if profile.revision_count == 1:
        profile.avg_quiz_score = quiz_score
    else:
        profile.avg_quiz_score = (profile.avg_quiz_score * (profile.revision_count - 1) + quiz_score) / profile.revision_count

    # Mastery gradual evolution (never jumps to 100 in one go)
    # Formula: mastery = (0.7 * mastery) + (0.3 * quiz_score)
    profile.mastery = round((0.7 * profile.mastery) + (0.3 * quiz_score), 1)

    # Confidence calculation:
    # Consistency increases confidence, fluctuations drop it.
    if quiz_score >= 80.0:
        profile.confidence = round(min(100.0, profile.confidence + 10.0), 1)
    elif quiz_score < 60.0:
        profile.confidence = round(max(0.0, profile.confidence - 15.0), 1)
    else:
        # Neutral score (60-80) shifts confidence slightly towards the quiz score
        profile.confidence = round((0.9 * profile.confidence) + (0.1 * quiz_score), 1)

    # Update spaced repetition interval
    profile.interval_days = schedule_revision(profile.interval_days, quiz_score)

    # Re-calculate retention immediately (should be 100% since they just revised)
    profile.retention = calculate_retention(profile.last_revision, profile.interval_days)

    db.commit()
    db.refresh(profile)

    logger.info(
        "LearningAgent: Updated profile user=%d subject=%r topic=%r mastery=%.1f%% retention=%.1f%% confidence=%.1f%% interval=%d days",
        user_id, subject, topic, profile.mastery, profile.retention, profile.confidence, profile.interval_days
    )

    return profile


def trigger_planner_recalculation(db: Session, user_id: int, ai_client) -> None:
    """
    Trigger task priority recalculation in PlannerAgent to propagate new memory metrics.
    """
    from app.agents.planner_agent import score_all_tasks
    try:
        score_all_tasks(user_id, db, ai_client)
        logger.info("LearningAgent: Triggered PlannerAgent task rescoring for user %d", user_id)
    except Exception as exc:
        logger.error("LearningAgent: Failed to trigger task rescoring: %s", exc)
