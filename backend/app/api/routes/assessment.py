"""
api/routes/assessment.py — Assessment Agent & Spaced Repetition endpoints.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_ai_client_dep
from app.core.database import get_db
from app.models.user import User
from app.models.imported_document import ImportedDocument
from app.models.learning_profile import LearningProfile
from app.models.question_citation import QuestionCitation
from app.models.tutor_session import TutorSession, TutorMessage
from app.models.study_note import StudyNote
from app.models.mistake_journal import MistakeJournal
from app.models.learning_objective import LearningObjective
from app.services.tutor_service import TutorService
from app.agents import learning_agent
from app.services.ai_client import AIInferenceClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assessment", tags=["assessment"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GenerateQuizRequest(BaseModel):
    subject: str
    topic: str
    document_id: Optional[int] = None


class QuizOptionQuestion(BaseModel):
    id: str
    question_text: str
    options: List[str]


class QuizResponse(BaseModel):
    topic: str
    subject: str
    questions: List[QuizOptionQuestion]


class SubmitAnswersRequest(BaseModel):
    answers: Dict[str, str]  # question_citation_id -> selected_option
    time_taken_seconds: int


class QuestionEvaluation(BaseModel):
    question_id: str
    is_correct: bool
    explanation: str


class SubmitResponse(BaseModel):
    status: str  # "SUCCESS" | "SPEED_GUESS_DETECTED"
    message: str
    score: Optional[float] = None
    correct_count: Optional[int] = None
    total_questions: Optional[int] = None
    evaluations: Optional[List[QuestionEvaluation]] = None


class CitationResponse(BaseModel):
    question_text: str
    correct_answer: str
    document_name: Optional[str] = None
    page_range: Optional[str] = None
    retrieved_context: Optional[str] = None
    generated_rubric: Optional[str] = None


class TopicAnalytics(BaseModel):
    id: int
    subject: str
    topic: str
    mastery: float
    confidence: float
    retention: float
    avg_quiz_score: float
    attempts_count: int
    revision_count: int
    interval_days: int
    learning_streak: int
    last_revision: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=QuizResponse)
def generate_assessment(
    req: GenerateQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """
    Retrieves document text (if document_id is provided) and calls the AI to
    generate 3 multiple-choice questions with answers, rubrics, and source context.
    """
    extracted_text = ""
    if req.document_id:
        doc = db.query(ImportedDocument).filter(
            ImportedDocument.id == req.document_id,
            ImportedDocument.user_id == current_user.id
        ).first()
        if doc:
            extracted_text = doc.extracted_text

    ai_ctx = {
        "text": extracted_text,
        "subject": req.subject,
        "topic": req.topic,
        "document_id": req.document_id,
    }

    try:
        raw_quiz_json = ai_client.generate("generate_quiz", ai_ctx)
        parsed_questions = json.loads(raw_quiz_json)
    except Exception as exc:
        logger.error("Failed to generate quiz via AI: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate assessment questions. Please try again."
        )

    response_questions = []
    # Save citations to DB and prepare questions for frontend (without answer keys)
    for idx, pq in enumerate(parsed_questions):
        citation = QuestionCitation(
            user_id=current_user.id,
            subject=req.subject,
            topic=req.topic,
            question_text=pq.get("question_text", f"Question {idx+1}"),
            options=json.dumps(pq.get("options", [])),
            correct_answer=pq.get("correct_answer", ""),
            document_id=req.document_id,
            chunk_id=pq.get("chunk_id", ""),
            page_range=pq.get("page_range", "Page 1"),
            retrieved_context=pq.get("retrieved_context", ""),
            generated_rubric=pq.get("generated_rubric", "")
        )
        db.add(citation)
        db.flush()  # get citation.id

        response_questions.append(
            QuizOptionQuestion(
                id=str(citation.id),
                question_text=citation.question_text,
                options=json.loads(citation.options)
            )
        )

    db.commit()

    return QuizResponse(
        topic=req.topic,
        subject=req.subject,
        questions=response_questions
    )


@router.post("/submit", response_model=SubmitResponse)
def submit_answers(
    req: SubmitAnswersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    """
    Evaluates quiz submissions, handles speed guess protection,
    updates mastery metrics through LearningAgent, and triggers rescheduling.
    """
    total_q = len(req.answers)
    if total_q == 0:
        raise HTTPException(status_code=400, detail="No answers submitted.")

    # Speed guessing protection: reject if finished faster than 5 seconds per question
    min_time_allowed = total_q * 5
    if req.time_taken_seconds < min_time_allowed:
        logger.warning(
            "Assessment: speed guessing detected for user %d (took %ds for %d questions)",
            current_user.id, req.time_taken_seconds, total_q
        )
        return SubmitResponse(
            status="SPEED_GUESS_DETECTED",
            message="This assessment appears to have been completed too quickly. It won't affect your learning profile. Would you like to retry?"
        )

    # Load citations from DB to match answers
    questions_list = []
    citations_map = {}
    for q_id_str, student_ans in req.answers.items():
        try:
            q_id = int(q_id_str)
        except ValueError:
            continue
        
        cit = db.query(QuestionCitation).filter(
            QuestionCitation.id == q_id,
            QuestionCitation.user_id == current_user.id
        ).first()
        
        if cit:
            citations_map[cit.id] = cit
            questions_list.append({
                "id": str(cit.id),
                "question_text": cit.question_text,
                "correct_answer": cit.correct_answer,
                "generated_rubric": cit.generated_rubric
            })

    if not questions_list:
        raise HTTPException(status_code=400, detail="Invalid question IDs submitted.")

    # Call AI client to run rubric evaluation
    ai_ctx = {
        "answers": req.answers,
        "questions": questions_list
    }
    
    try:
        raw_eval_json = ai_client.generate("evaluate_rubric", ai_ctx)
        parsed_eval = json.loads(raw_eval_json)
    except Exception as exc:
        logger.error("Failed to evaluate answers via AI: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation server error. Please try again."
        )

    evaluations = []
    correct_count = 0
    
    for ev in parsed_eval.get("evaluations", []):
        evaluations.append(
            QuestionEvaluation(
                question_id=ev.get("question_id"),
                is_correct=ev.get("is_correct", False),
                explanation=ev.get("explanation", "")
            )
        )
        if ev.get("is_correct"):
            correct_count += 1

    score = parsed_eval.get("score", (correct_count / len(questions_list)) * 100.0)

    # Use first question's metadata for subject/topic grouping
    first_cit = citations_map[int(questions_list[0]["id"])]
    subject = first_cit.subject or "General Study"
    topic = first_cit.topic or "Concepts"

    # Update Learning Profile via LearningAgent
    learning_agent.update_learning_profile(
        db=db,
        user_id=current_user.id,
        subject=subject,
        topic=topic,
        quiz_score=score,
        correct_count=correct_count,
        total_questions=len(questions_list)
    )

    # Trigger Planner rescoring to apply updated retention priority immediately
    learning_agent.trigger_planner_recalculation(db, current_user.id, ai_client)

    return SubmitResponse(
        status="SUCCESS",
        message="Assessment evaluation complete.",
        score=score,
        correct_count=correct_count,
        total_questions=len(questions_list),
        evaluations=evaluations
    )


@router.get("/citation/{question_id}", response_model=CitationResponse)
def get_citation(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return citation and source details for a question (source document, page range, context, explanation).
    """
    cit = db.query(QuestionCitation).filter(
        QuestionCitation.id == question_id,
        QuestionCitation.user_id == current_user.id
    ).first()

    if not cit:
        raise HTTPException(status_code=404, detail="Question citation not found.")

    doc_name = None
    if cit.document_id:
        doc = db.query(ImportedDocument).filter(ImportedDocument.id == cit.document_id).first()
        if doc:
            doc_name = doc.original_filename

    return CitationResponse(
        question_text=cit.question_text,
        correct_answer=cit.correct_answer,
        document_name=doc_name or "Imported Timetable / Syllabus",
        page_range=cit.page_range,
        retrieved_context=cit.retrieved_context,
        generated_rubric=cit.generated_rubric
    )


@router.get("/learning-profile", response_model=List[TopicAnalytics])
def get_learning_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the user's learning profiles with updated exponential memory decay.
    """
    profiles = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id
    ).all()

    response = []
    for p in profiles:
        # Dynamically recalculate retention
        ret = learning_agent.calculate_retention(p.last_revision, p.interval_days)
        p.retention = ret
        
        response.append(
            TopicAnalytics(
                id=p.id,
                subject=p.subject,
                topic=p.topic,
                mastery=p.mastery,
                confidence=p.confidence,
                retention=p.retention,
                avg_quiz_score=p.avg_quiz_score,
                attempts_count=p.attempts_count,
                revision_count=p.revision_count,
                interval_days=p.interval_days,
                learning_streak=p.learning_streak,
                last_revision=p.last_revision.isoformat()
            )
        )

    # Save calculated decays
    db.commit()
    return response


# ─── Socratic Tutor Schemas ────────────────────────────────────────────────────

class TutorStartRequest(BaseModel):
    subject: str
    topic: str
    difficulty_level: Optional[int] = 1
    assessment_type: str = "mixed"
    target_goal: str = "General Learning"
    teacher_personality: str = "Socratic Tutor"
    learning_mode: str = "Mixed"
    document_id: Optional[int] = None


class TutorRespondRequest(BaseModel):
    session_id: int
    student_answer: str
    time_taken_seconds: int


class TutorNoteRequest(BaseModel):
    subject: str
    topic: str
    content: str


# ─── Socratic Tutor Routes ─────────────────────────────────────────────────────

@router.post("/tutor/start")
def start_tutor_session(
    req: TutorStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    session = TutorService.initialize_session(
        db=db,
        ai_client=ai_client,
        user_id=current_user.id,
        subject=req.subject,
        topic=req.topic,
        difficulty_level=req.difficulty_level,
        assessment_type=req.assessment_type,
        target_goal=req.target_goal,
        teacher_personality=req.teacher_personality,
        learning_mode=req.learning_mode,
        document_id=req.document_id
    )
    # Get first message content
    first_msg = db.query(TutorMessage).filter(TutorMessage.session_id == session.id).first()
    return {
        "session_id": session.id,
        "first_question": first_msg.content if first_msg else "Hello! Let's start studying.",
        "difficulty_level": session.difficulty_level
    }


@router.post("/tutor/respond")
def respond_to_tutor(
    req: TutorRespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    res = TutorService.evaluate_and_respond(
        db=db,
        ai_client=ai_client,
        session_id=req.session_id,
        student_answer=req.student_answer,
        time_taken_seconds=req.time_taken_seconds
    )
    # Trigger Planner recalculation
    learning_agent.trigger_planner_recalculation(db, current_user.id, ai_client)
    return res


@router.post("/tutor/note")
def save_study_note(
    req: TutorNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = TutorService.add_study_note(
        db=db,
        user_id=current_user.id,
        subject=req.subject,
        topic=req.topic,
        content=req.content
    )
    return {"status": "SUCCESS", "note_id": note.id}


@router.get("/tutor/session/{session_id}")
def get_tutor_session_log(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(TutorSession).filter(
        and_(TutorSession.id == session_id, TutorSession.user_id == current_user.id)
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Tutoring session not found.")
        
    messages = db.query(TutorMessage).filter(TutorMessage.session_id == session_id).order_by(TutorMessage.timestamp.asc()).all()
    
    chat_log = []
    for msg in messages:
        sources_list = []
        for chunk in msg.chunks:
            sources_list.append({
                "document_name": chunk.document_name,
                "page_number": chunk.page_number,
                "paragraph_number": chunk.paragraph_number or 1,
                "lecture_name": chunk.lecture_name or "Lecture 3"
            })
        chat_log.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "evaluation_confidence": msg.evaluation_confidence,
            "timestamp": msg.timestamp.isoformat(),
            "sources": sources_list
        })
    return {"session": {"subject": session.subject, "topic": session.topic}, "chat_log": chat_log}


@router.get("/tutor/sessions")
def list_tutor_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.query(TutorSession).filter(TutorSession.user_id == current_user.id).order_by(TutorSession.created_at.desc()).all()
    return [{
        "id": s.id,
        "subject": s.subject,
        "topic": s.topic,
        "difficulty_level": s.difficulty_level,
        "created_at": s.created_at.isoformat()
    } for s in sessions]


@router.get("/tutor/mistake-journal")
def get_mistake_journal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mistakes = db.query(MistakeJournal).filter(MistakeJournal.user_id == current_user.id).order_by(MistakeJournal.last_attempt.desc()).all()
    return [{
        "id": m.id,
        "subject": m.subject,
        "topic": m.topic,
        "question_text": m.question_text,
        "student_answer": m.student_answer,
        "explanation": m.explanation,
        "mistakes_count": m.mistakes_count,
        "last_attempt": m.last_attempt.isoformat(),
        "revision_due": m.revision_due.isoformat()
    } for m in mistakes]


@router.get("/tutor/study-notes")
def list_study_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes = db.query(StudyNote).filter(StudyNote.user_id == current_user.id).order_by(StudyNote.created_at.desc()).all()
    return [{
        "id": n.id,
        "subject": n.subject,
        "topic": n.topic,
        "content": n.content,
        "created_at": n.created_at.isoformat()
    } for n in notes]


@router.get("/tutor/learning-objectives")
def get_objectives(
    subject: str,
    topic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # import from tutor_service helper
    from app.services.tutor_service import get_or_create_objectives
    objectives = get_or_create_objectives(db, subject, topic)
    return [{
        "id": o.id,
        "objective_text": o.objective_text,
        "priority_stars": o.priority_stars,
        "is_mastered": o.is_mastered
    } for o in objectives]
