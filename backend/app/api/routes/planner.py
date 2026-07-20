"""api/routes/planner.py — Planner Agent endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_ai_client_dep
from app.core.database import get_db
from app.models.user import User
from app.agents import planner_agent
from app.services.ai_client import AIInferenceClient
from app.schemas.task import TaskListResponse, TaskResponse

router = APIRouter(prefix="/api/planner", tags=["planner"])


@router.get("/daily")
def get_daily_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """Return today's prioritised study plan with time allocation."""
    return planner_agent.build_daily_plan(current_user.id, db, ai_client)


@router.get("/weekly")
def get_weekly_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """Return the 7-day study schedule."""
    return planner_agent.build_weekly_plan(current_user.id, db, ai_client)


@router.post("/score", response_model=TaskListResponse)
def rescore_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """Trigger a manual priority rescore of all incomplete tasks."""
    tasks = planner_agent.score_all_tasks(current_user.id, db, ai_client)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )
