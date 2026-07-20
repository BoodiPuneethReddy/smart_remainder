"""
api/routes/tasks.py — Task CRUD endpoints.
All routes are protected — require valid JWT.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_ai_client_dep
from app.core.database import get_db
from app.models.task import Task
from app.models.study_session import StudySession
from app.models.user import User
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.ai_client import AIInferenceClient
from app.services.scoring import compute_priority, generate_explanation_template

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _score_task(task: Task, user_id: int, db: Session, ai_client: AIInferenceClient) -> None:
    """Compute and persist priority score for a single task."""
    sessions = db.query(StudySession).filter(StudySession.user_id == user_id).all()
    session_dicts = [{"subject": s.subject, "task_completed": s.task_completed} for s in sessions]

    result = compute_priority(
        task_type=task.task_type,
        subject=task.subject,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        sessions=session_dicts,
    )
    task.priority_score = result["priority_score"]
    task.urgency_score = result["urgency_score"]
    task.importance_score = result["importance_score"]
    task.weakness_score = result["weakness_score"]
    task.effort_score = result["effort_score"]

    template_explanation = generate_explanation_template(
        subject=task.subject,
        task_type=task.task_type,
        top_factors=result["top_factors"],
        days_remaining=result["days_remaining"],
        estimated_hours=task.estimated_hours,
    )
    try:
        task.ai_explanation = ai_client.generate("explain_priority", {
            "subject": task.subject,
            "task_type": task.task_type,
            "days_remaining": result["days_remaining"],
            "estimated_hours": task.estimated_hours,
            "top_factors": result["top_factors"],
            "priority_score": result["priority_score"],
        }) or template_explanation
    except Exception:
        task.ai_explanation = template_explanation


@router.get("", response_model=TaskListResponse)
def list_tasks(
    include_completed: bool = Query(False),
    subject: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Task).filter(Task.user_id == current_user.id)
    if not include_completed:
        q = q.filter(Task.is_completed == False)
    if subject:
        q = q.filter(Task.subject.ilike(f"%{subject}%"))
    if task_type:
        q = q.filter(Task.task_type == task_type)
    tasks = q.order_by(Task.priority_score.desc()).all()
    return TaskListResponse(tasks=[TaskResponse.model_validate(t) for t in tasks], total=len(tasks))


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    task = Task(user_id=current_user.id, **task_data.model_dump())
    db.add(task)
    db.flush()
    _score_task(task, current_user.id, db, ai_client)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    updates: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(task, field, value)

    if updates.is_completed is True and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
        # Record a study session for completion
        session = StudySession(
            user_id=current_user.id,
            subject=task.subject,
            task_completed=1,
            task_id=task.id,
            duration_minutes=int(task.estimated_hours * 60),
        )
        db.add(session)

    _score_task(task, current_user.id, db, ai_client)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
