"""
services/document_import/duplicate_checker.py — DuplicateChecker

Checks whether an about-to-be-imported task already exists in the database.
Comparison is deterministic — same subject + date within ±1 day.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.task import Task

logger = logging.getLogger(__name__)


def parse_date_flexible(date_str: Optional[str]) -> Optional[datetime]:
    """Parse various date string formats into a datetime object."""
    if not date_str:
        return None

    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %b %Y", "%d %B %Y", "%B %d, %Y",
        "%d/%m/%y", "%d-%m-%y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def find_duplicates(
    user_id: int,
    subject: str,
    due_date_str: Optional[str],
    db: Session,
    date_window_days: int = 1,
) -> list[Task]:
    """
    Find existing tasks that might be duplicates of the given import.

    Criteria:
    - Same user
    - Subject matches (case-insensitive, substring match)
    - Due date within ±date_window_days days (if date is known)

    Returns list of potential duplicate Tasks (may be empty).
    """
    if not subject:
        return []

    subject_lower = subject.lower().strip()
    query = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.is_completed == False,
        )
    )

    all_tasks = query.all()
    duplicates: list[Task] = []

    parsed_date = parse_date_flexible(due_date_str)

    for task in all_tasks:
        # Subject match: either exact substring or significant overlap
        task_subject_lower = (task.subject or "").lower().strip()
        subject_match = (
            subject_lower in task_subject_lower
            or task_subject_lower in subject_lower
            or _word_overlap(subject_lower, task_subject_lower) >= 0.6
        )

        if not subject_match:
            continue

        # Date match
        if parsed_date and task.due_date:
            task_due = task.due_date
            if task_due.tzinfo is None:
                task_due = task_due.replace(tzinfo=timezone.utc)
            date_diff = abs((parsed_date - task_due).days)
            if date_diff <= date_window_days:
                duplicates.append(task)
        elif subject_match and not parsed_date:
            # No date to compare — flag by subject alone
            duplicates.append(task)

    if duplicates:
        logger.info(
            "DuplicateChecker: found %d potential duplicate(s) for subject='%s'",
            len(duplicates), subject,
        )

    return duplicates


def _word_overlap(a: str, b: str) -> float:
    """Compute Jaccard similarity on word sets."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
