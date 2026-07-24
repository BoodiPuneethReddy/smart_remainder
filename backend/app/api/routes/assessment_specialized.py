"""
backend/app/api/routes/assessment_specialized.py — Assessment routes using specialized tutor

Routes:
  POST /api/assessment/tutor/session — Initialize specialized tutor session
  POST /api/assessment/tutor/respond — Evaluate answer with behavioral specialization
  GET /api/assessment/tutor/session/{session_id} — Get session state
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_current_user, get_db, get_ai_client_dep
from app.models.user import User
from app.models.tutor_session import TutorSession
from app.services.tutor_service_specialized import SpecializedTutorService
from app.services.ai_client import AIInferenceClient
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/assessment/tutor", tags=["tutor-specialized"])


class TutorSessionRequest(BaseModel):
    subject: str
    topic: str
    difficulty_level: int = 1
    assessment_type: str = "Mixed"
    target_goal: str = "General Learning"
    teacher_personality: str = "Socratic Tutor"
    learning_mode: str = "Teach Me"
    document_id: Optional[int] = None


class TutorResponseRequest(BaseModel):
    session_id: int
    student_answer: str
    time_taken_seconds: int = 30


class TutorSessionResponse(BaseModel):
    session_id: int
    status: str
    initial_message: str
    personality: str
    learning_mode: str
    assessment_type: str
    target_goal: str


class TutorEvaluationResponse(BaseModel):
    status: str
    explanation: str
    metrics: dict
    strengths: list
    missing_points: list
    misconceptions: list
    difficulty_level: int
    mastery_score: float


@router.post("/session", response_model=TutorSessionResponse)
def start_tutor_session(
    request: TutorSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """
    Initialize a specialized AI tutor session with behavioral customization.
    
    The tutor will adapt tone, teaching style, question format, and difficulty
    based on the selected personality, learning mode, assessment type, and study focus.
    """
    try:
        session = SpecializedTutorService.initialize_session(
            db=db,
            ai_client=ai_client,
            user_id=current_user.id,
            subject=request.subject,
            topic=request.topic,
            difficulty_level=request.difficulty_level,
            assessment_type=request.assessment_type,
            target_goal=request.target_goal,
            teacher_personality=request.teacher_personality,
            learning_mode=request.learning_mode,
            document_id=request.document_id,
        )

        # Get the initial message from session
        initial_message = session.tutor_messages[0].content if session.tutor_messages else ""

        return TutorSessionResponse(
            session_id=session.id,
            status="active",
            initial_message=initial_message,
            personality=request.teacher_personality,
            learning_mode=request.learning_mode,
            assessment_type=request.assessment_type,
            target_goal=request.target_goal,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start session: {str(e)}")


@router.post("/respond", response_model=TutorEvaluationResponse)
def submit_tutor_response(
    request: TutorResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """
    Submit student answer and receive specialized evaluation.
    
    The evaluation respects:
    - Teacher personality (Friendly, Professor, Interviewer, Coach, Socratic)
    - Learning mode (Teach, Test, Challenge, Interview, Revise)
    - Assessment format (MCQ, Short Answer, True/False, Mixed)
    - Study focus (College, Placement, GATE, General)
    """
    try:
        result = SpecializedTutorService.evaluate_and_respond(
            db=db,
            ai_client=ai_client,
            session_id=request.session_id,
            student_answer=request.student_answer,
            time_taken_seconds=request.time_taken_seconds,
        )

        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])

        return TutorEvaluationResponse(
            status=result.get("status", "SUCCESS"),
            explanation=result.get("explanation", ""),
            metrics=result.get("metrics", {}),
            strengths=result.get("strengths", []),
            missing_points=result.get("missing_points", []),
            misconceptions=result.get("misconceptions", []),
            difficulty_level=result.get("difficulty_level", 1),
            mastery_score=result.get("mastery_score", 0.0),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to evaluate: {str(e)}")


@router.get("/session/{session_id}")
def get_session_state(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current state of a tutor session."""
    session = db.query(TutorSession).filter(
        TutorSession.id == session_id,
        TutorSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "subject": session.subject,
        "topic": session.topic,
        "status": session.status,
        "personality": session.teacher_personality,
        "learning_mode": session.learning_mode,
        "assessment_type": session.assessment_type,
        "target_goal": session.target_goal,
        "difficulty_level": session.difficulty_level,
        "score": session.score,
        "attempts": session.attempts,
        "message_count": len(session.tutor_messages) if session.tutor_messages else 0,
        "created_at": session.created_at,
    }
