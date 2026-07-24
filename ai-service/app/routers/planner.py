from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/planner", tags=["planner"])

class PlannerRequest(BaseModel):
    user_id: int
    tasks: List[Dict[str, Any]]
    available_minutes: Optional[int] = None

class PlannerResponse(BaseModel):
    schedule: List[Dict[str, Any]]
    total_minutes: int
    ai_presentation: str

@router.post("", response_model=PlannerResponse)
def compute_plan(request: PlannerRequest):
    tasks = request.tasks
    sorted_tasks = sorted(tasks, key=lambda t: t.get("priority_score", 50.0), reverse=True)
    
    schedule = []
    total = 0
    for idx, t in enumerate(sorted_tasks[:5]):
        duration = min(90, int(t.get("estimated_hours", 2.0) * 60))
        schedule.append({
            "slot": idx + 1,
            "task_id": t.get("id"),
            "subject": t.get("subject", "General"),
            "title": t.get("title", "Study Block"),
            "duration_minutes": duration,
            "priority_score": t.get("priority_score", 50.0)
        })
        total += duration

    presentation = f"Here is your AI-optimized study schedule ({total} min total across {len(schedule)} focused blocks):\n\n"
    for s in schedule:
        presentation += f"{s['slot']}. **{s['subject']}**: {s['title']} — {s['duration_minutes']} min (Priority {s['priority_score']:.0f}/100)\n"

    return PlannerResponse(
        schedule=schedule,
        total_minutes=total,
        ai_presentation=presentation
    )
