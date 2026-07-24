from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/recommendation", tags=["recommendation"])

class RecommendationRequest(BaseModel):
    user_id: int
    question: str
    context: Optional[Dict[str, Any]] = None

class RecommendationResponse(BaseModel):
    answer: str
    intent_detected: List[str]
    source_agent: str

@router.post("", response_model=RecommendationResponse)
def get_recommendation(request: RecommendationRequest):
    q = request.question.lower()
    if any(k in q for k in ["hi", "hello", "hey", "yo"]):
        ans = "Hi! Ready to help you tackle your study goals today. What would you like to do?"
        intent = ["greeting"]
    elif any(k in q for k in ["hours", "reschedule", "study today", "plan"]):
        ans = "I recommend focusing on your highest priority task first. You have dedicated study blocks ready."
        intent = ["study_planning"]
    else:
        ans = f"Based on your study data: focus on high priority tasks to maintain your study streak!"
        intent = ["general"]

    return RecommendationResponse(
        answer=ans,
        intent_detected=intent,
        source_agent="RecommendationAgent"
    )
