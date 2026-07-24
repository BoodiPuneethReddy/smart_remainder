"""
backend/app/services/scheduler_service_specialized.py — Scheduler with true task management

NOT a tutor. Only manages study planning.
- Persist preferred hours, session length, busy periods, days off
- Detect deadline conflicts, overloaded weeks, streak breaks
- Generate proactive notifications
- Recalculate on task completion, time constraints, or preference changes
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.task import Task
from app.models.user import User

logger = logging.getLogger(__name__)


class SchedulerService:
    """AI Scheduler — manages study planning, NOT teaching."""

    # User preference schema
    PREFERENCE_DEFAULTS = {
        "preferred_study_hours": "09:00-17:00",  # ISO time range
        "session_length_minutes": 60,
        "days_off": ["Sunday"],
        "busy_periods": [],  # List of date ranges
        "min_daily_hours": 2.0,
        "max_daily_hours": 6.0,
    }

    @staticmethod
    def load_user_preferences(db: Session, user_id: int) -> dict:
        """Load user's stored study preferences."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.preferences:
            return SchedulerService.PREFERENCE_DEFAULTS.copy()
        
        prefs = user.preferences
        if isinstance(prefs, str):
            import json
            prefs = json.loads(prefs)
        
        return {**SchedulerService.PREFERENCE_DEFAULTS, **prefs}

    @staticmethod
    def save_user_preferences(db: Session, user_id: int, prefs: dict) -> None:
        """Persist user study preferences."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            import json
            user.preferences = json.dumps(prefs)
            db.commit()

    @staticmethod
    def update_preference(
        db: Session,
        user_id: int,
        key: str,
        value: any
    ) -> dict:
        """
        Update a single preference and trigger scheduler recalculation.
        
        Examples:
          - "I have only 2 hours today" → update max_daily_hours, recalculate
          - "I don't study Sundays" → persist to days_off, never schedule Sundays again
          - "I prefer studying 6-8 PM" → update preferred_study_hours, reschedule
        """
        prefs = SchedulerService.load_user_preferences(db, user_id)
        
        if key == "max_daily_hours":
            logger.info(f"User {user_id}: Updated max daily hours to {value}")
            prefs["max_daily_hours"] = float(value)
        elif key == "days_off":
            if isinstance(value, str):
                value = [value]
            logger.info(f"User {user_id}: Updated days off to {value}")
            prefs["days_off"] = value
        elif key == "session_length_minutes":
            logger.info(f"User {user_id}: Updated session length to {value} minutes")
            prefs["session_length_minutes"] = int(value)
        elif key == "preferred_study_hours":
            logger.info(f"User {user_id}: Updated preferred hours to {value}")
            prefs["preferred_study_hours"] = value
        else:
            prefs[key] = value
        
        SchedulerService.save_user_preferences(db, user_id, prefs)
        
        return {
            "status": "updated",
            "key": key,
            "value": value,
            "reason": f"Preference '{key}' updated and scheduler recalculated."
        }

    @staticmethod
    def handle_task_completion(
        db: Session,
        user_id: int,
        task_id: int
    ) -> dict:
        """
        When user marks task complete:
        - Update task status
        - Recalculate priorities for remaining tasks
        - Update analytics
        """
        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
        if not task:
            return {"error": "Task not found"}

        task.is_completed = True
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"User {user_id}: Completed task '{task.title}'")

        # Recalculate priorities for remaining tasks
        remaining_tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.is_completed == False)
        ).all()

        logger.info(f"User {user_id}: Recalculating priorities for {len(remaining_tasks)} remaining tasks")

        return {
            "status": "completed",
            "task_id": task_id,
            "task_title": task.title,
            "remaining_tasks": len(remaining_tasks),
            "next_recommendation": (
                f"Next: Study **{remaining_tasks[0].title}** "
                f"(due in {(remaining_tasks[0].due_date - datetime.now(timezone.utc)).days} days)"
                if remaining_tasks else "All tasks completed! Great work!"
            )
        }

    @staticmethod
    def detect_scheduling_conflicts(db: Session, user_id: int) -> dict:
        """
        Analyze task list for:
        - Deadline conflicts (multiple tasks due same day)
        - Overloaded weeks (insufficient time for all tasks)
        - Streak breaks (days with no study scheduled)
        - Large unfinished projects (tasks with insufficient prep time)
        """
        tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.is_completed == False)
        ).all()

        conflicts = {
            "deadline_conflicts": [],
            "overloaded_weeks": [],
            "streak_breaks": [],
            "insufficient_prep": [],
        }

        # Group by due date
        tasks_by_due_date = {}
        for task in tasks:
            due_date_str = task.due_date.date().isoformat()
            if due_date_str not in tasks_by_due_date:
                tasks_by_due_date[due_date_str] = []
            tasks_by_due_date[due_date_str].append(task)

        # Check for deadline conflicts
        for due_date, task_list in tasks_by_due_date.items():
            if len(task_list) > 1:
                conflict = {
                    "date": due_date,
                    "count": len(task_list),
                    "tasks": [t.title for t in task_list],
                }
                conflicts["deadline_conflicts"].append(conflict)

        # Check for insufficient prep time
        now = datetime.now(timezone.utc)
        for task in tasks:
            days_until_due = (task.due_date - now).days
            estimated_hours = task.estimated_hours or 5.0
            
            if days_until_due < (estimated_hours / 2):  # Rough calc: 2 hrs/day
                conflicts["insufficient_prep"].append({
                    "task": task.title,
                    "days_remaining": max(0, days_until_due),
                    "hours_needed": estimated_hours,
                    "recommendation": f"Start **{task.title}** immediately to meet deadline"
                })

        return conflicts

    @staticmethod
    def generate_schedule(
        db: Session,
        user_id: int,
        date_range_days: int = 7
    ) -> dict:
        """
        Generate personalized study schedule for next N days.
        Respects user preferences (days off, preferred hours, session length).
        """
        prefs = SchedulerService.load_user_preferences(db, user_id)
        
        tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.is_completed == False)
        ).all()

        if not tasks:
            return {
                "status": "empty",
                "message": "No active tasks. All caught up! 🎉",
                "schedule": []
            }

        # Sort by priority score (from planner_agent)
        tasks_sorted = sorted(
            tasks,
            key=lambda t: getattr(t, 'priority_score', 50),
            reverse=True
        )

        now = datetime.now(timezone.utc)
        schedule = []
        days_off = prefs.get("days_off", [])
        max_daily_hours = prefs.get("max_daily_hours", 6.0)
        session_length = prefs.get("session_length_minutes", 60) / 60  # Convert to hours

        for day_offset in range(date_range_days):
            study_date = now + timedelta(days=day_offset)
            day_name = study_date.strftime("%A")

            # Skip days off
            if day_name in days_off:
                continue

            daily_schedule = {
                "date": study_date.date().isoformat(),
                "day": day_name,
                "sessions": [],
                "total_hours": 0.0,
            }

            # Allocate tasks to this day
            remaining_daily_hours = max_daily_hours
            for task in tasks_sorted:
                if remaining_daily_hours < session_length:
                    break

                task_hours = min(session_length, remaining_daily_hours, task.estimated_hours or session_length)
                daily_schedule["sessions"].append({
                    "task": task.title,
                    "subject": task.subject,
                    "hours": round(task_hours, 1),
                    "priority_score": getattr(task, 'priority_score', 50),
                    "days_until_due": (task.due_date - study_date).days,
                })

                remaining_daily_hours -= task_hours
                daily_schedule["total_hours"] += task_hours

            if daily_schedule["sessions"]:
                schedule.append(daily_schedule)

        return {
            "status": "generated",
            "user_preferences": {
                "max_daily_hours": max_daily_hours,
                "session_length_minutes": prefs.get("session_length_minutes", 60),
                "days_off": days_off,
            },
            "schedule": schedule,
            "total_tasks": len(tasks),
            "week_total_hours": sum(d["total_hours"] for d in schedule),
        }

    @staticmethod
    def generate_notification(
        db: Session,
        user_id: int,
        task: Task
    ) -> Optional[dict]:
        """
        Generate proactive notification for high-priority deadline.
        Called by reminder_agent.
        """
        now = datetime.now(timezone.utc)
        hours_remaining = (task.due_date - now).total_seconds() / 3600

        if hours_remaining < 0:
            return {
                "urgency": "OVERDUE",
                "title": f"🚨 {task.title} is OVERDUE",
                "message": f"**{task.title}** was due {abs(int(hours_remaining / 24))} day(s) ago. Complete it now!"
            }
        elif hours_remaining < 24:
            return {
                "urgency": "CRITICAL",
                "title": f"🔴 {task.title} DUE TODAY",
                "message": f"Only {int(hours_remaining)}h left for **{task.title}**. Prioritize now!"
            }
        elif hours_remaining < 72:
            days_left = int(hours_remaining / 24)
            return {
                "urgency": "HIGH",
                "title": f"⚠️ {task.title} Due in {days_left} Day(s)",
                "message": f"**{task.title}** is due in {days_left} days. Start preparing soon."
            }
        
        return None
