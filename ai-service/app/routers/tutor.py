import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter(prefix="/tutor", tags=["tutor"])

class TutorRequest(BaseModel):
    topic: str
    student_answer: Optional[str] = ""
    teacher_personality: Optional[str] = "Socratic Tutor"
    learning_mode: Optional[str] = "Teach Me"
    assessment_type: Optional[str] = "Mixed"
    has_uploaded_material: Optional[bool] = True

class TutorResponse(BaseModel):
    understanding: int
    reasoning: int
    application: int
    confidence: int
    explanation: str
    should_draw_whiteboard: bool
    diagram_data: Optional[Dict[str, Any]] = None

@router.post("", response_model=TutorResponse)
def evaluate_tutor_session(request: TutorRequest):
    topic = request.topic
    personality = request.teacher_personality
    mode = request.learning_mode
    has_material = request.has_uploaded_material

    if not has_material:
        return TutorResponse(
            understanding=0,
            reasoning=0,
            application=0,
            confidence=0,
            explanation=f"No material uploaded for **{topic}** yet. Please upload a PDF or document for **{topic}** to enable grounded citations and tutor analysis.",
            should_draw_whiteboard=False,
            diagram_data=None
        )

    mode_prefix = f"📘 [{mode}] " if mode else ""
    p_tone = f"({personality}): " if personality else ""
    exp = f"{mode_prefix}{p_tone}You are thinking in the right direction for **{topic}**. Consider how it manages data integrity and operational consistency."

    return TutorResponse(
        understanding=85,
        reasoning=80,
        application=75,
        confidence=88,
        explanation=exp,
        should_draw_whiteboard=True,
        diagram_data={"type": "flowchart TD", "nodes": [{"id": "1", "label": topic}]}
    )
