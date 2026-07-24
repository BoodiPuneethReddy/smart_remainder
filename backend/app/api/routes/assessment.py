"""
api/routes/assessment.py — Assessment Agent & Spaced Repetition endpoints.
"""

import re
import math
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

class CreateLinearSessionRequest(BaseModel):
    document_id: int
    personality: str = "Socratic Tutor"
    goal: str = "General Learning"
    learning_mode: str = "Teach Me"
    assessment_type: str = "Mixed"
    difficulty: str = "Adaptive"
    session_length: str = "60 min"


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


# ─── Linear Learning Workspace Endpoints ────────────────────────────────────────

import math

class DocumentAnalysisResponse(BaseModel):
    document_id: int
    filename: str
    subject: str
    has_educational_content: bool
    message: Optional[str] = None
    topics_count: int
    topics: List[str]
    pages_count: int
    estimated_session_minutes: int
    difficulty: str
    reading_time_minutes: int
    question_count: int


from app.services.document_graph import DocumentGraphParser, SemanticTitleCleaner


def clean_heading_title(line: str) -> str:
    return SemanticTitleCleaner.clean(line)


def get_topic_content_block(text: str, target_topic: str) -> dict:
    """
    Retrieves the specific TopicNode from the DocumentGraph for target_topic.
    Returns structured content, paragraphs, definitions, examples, and keywords.
    """
    if not text or not target_topic:
        return {"title": target_topic, "content": "", "summary": f"Study section for {target_topic}", "keywords": [target_topic]}

    graph = DocumentGraphParser.build_graph(text, "document")
    target_clean = SemanticTitleCleaner.clean(target_topic).lower()

    matched_node = None
    for node in graph.get("topics", []):
        t_clean = node["title"].lower()
        if target_clean in t_clean or t_clean in target_clean:
            matched_node = node
            break

    if not matched_node and graph.get("topics"):
        matched_node = graph["topics"][0]

    if matched_node:
        paragraphs = matched_node.get("supporting_paragraphs", [])
        content_text = "\n".join(paragraphs).strip()
        return {
            "title": matched_node["title"],
            "summary": matched_node["summary"],
            "content": content_text,
            "keywords": matched_node["keywords"],
            "definitions": matched_node["definitions"],
            "examples": matched_node["examples"],
            "learning_objectives": matched_node["learning_objectives"],
            "question_bank": matched_node["question_bank"],
            "est_minutes": matched_node["est_minutes"],
            "difficulty": matched_node["difficulty"]
        }

    return {
        "title": SemanticTitleCleaner.clean(target_topic),
        "summary": f"Section overview for {target_topic}",
        "content": text[:500],
        "keywords": [target_topic],
        "definitions": [],
        "examples": [],
        "learning_objectives": [f"Understand {target_topic}"],
        "question_bank": [],
        "est_minutes": 15,
        "difficulty": 3
    }


def extract_topics_from_text(text: str, filename: str) -> tuple[bool, str, List[str], int, int, int]:
    """
    Parses raw PDF text using DocumentGraphParser into a structured Semantic Knowledge Graph.
    Fully data-driven and generalized for ANY educational PDF (Biology, Law, Chemistry, CS, Physics, etc.).
    Returns: (has_educational_content, subject, topics, page_count, est_minutes, question_count)
    """
    if not text or len(text.strip()) < 30:
        return False, "Unknown", [], 1, 0, 0

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text_lower = text.lower()
    
    task_keywords = ["due date", "submission deadline", "timetable", "schedule", "quiz date", "exam date", "venue", "instructor", "rules", "submission"]
    educational_keywords = ["concept", "chapter", "unit", "definition", "algorithm", "theory", "principle", "introduction", "process", "management", "architecture", "overview", "model", "system", "infrastructure", "hardware", "software", "data", "analysis", "method", "structure", "function", "classification", "property", "equation", "law", "mechanism"]

    edu_count = sum(1 for kw in educational_keywords if kw in text_lower)
    task_count = sum(1 for kw in task_keywords if kw in text_lower)

    if edu_count < 2 and task_count > 0 and len(lines) < 25:
        return False, "Academic Schedule", [], 1, 0, 0

    graph = DocumentGraphParser.build_graph(text, filename)
    subject = graph.get("subject", "General Academic Study")
    topics = [t["title"] for t in graph.get("topics", []) if t.get("title")]

    if not topics:
        topics = ["Core Concepts & Definitions", "Foundational Principles", "System Architecture & Theory", "Applications & Analysis"]

    words_count = len(text.split())
    pages_count = max(1, math.ceil(words_count / 250))
    est_minutes = max(15, math.ceil(words_count / 40))
    question_count = max(4, len(topics) * 2)

    return True, subject, topics, pages_count, est_minutes, question_count


@router.get("/documents")
def get_user_learning_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = db.query(ImportedDocument).filter(ImportedDocument.user_id == current_user.id).order_by(ImportedDocument.uploaded_at.desc()).all()
    return [{
        "id": d.id,
        "filename": d.original_filename,
        "subject": d.document_type or "General",
        "created_at": d.uploaded_at.isoformat()
    } for d in docs]


@router.post("/analyze-document", response_model=DocumentAnalysisResponse)
def analyze_learning_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(ImportedDocument).filter(
        and_(ImportedDocument.id == document_id, ImportedDocument.user_id == current_user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    has_edu, subj, topics, pages, est_min, q_count = extract_topics_from_text(
        doc.extracted_text or "", doc.original_filename
    )

    if not has_edu:
        return DocumentAnalysisResponse(
            document_id=doc.id,
            filename=doc.original_filename,
            subject=subj,
            has_educational_content=False,
            message="This document contains schedules/tasks but not enough educational content for an AI learning session. Upload lecture notes or textbooks to begin AI tutoring.",
            topics_count=0,
            topics=[],
            pages_count=pages,
            estimated_session_minutes=0,
            difficulty="N/A",
            reading_time_minutes=0,
            question_count=0
        )

    return DocumentAnalysisResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        subject=subj,
        has_educational_content=True,
        message=None,
        topics_count=len(topics),
        topics=topics,
        pages_count=pages,
        estimated_session_minutes=est_min,
        difficulty="Intermediate",
        reading_time_minutes=max(5, int(est_min * 0.3)),
        question_count=q_count
    )


@router.post("/create-session")
def create_linear_session(
    req: CreateLinearSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIInferenceClient = Depends(get_ai_client_dep),
):
    doc = db.query(ImportedDocument).filter(
        and_(ImportedDocument.id == req.document_id, ImportedDocument.user_id == current_user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    has_edu, subj, topics, pages, est_min, q_count = extract_topics_from_text(
        doc.extracted_text or "", doc.original_filename
    )

    if not has_edu:
        raise HTTPException(status_code=400, detail="This document contains schedules/tasks but not enough educational content for an AI learning session. Upload lecture notes or textbooks to begin AI tutoring.")

    first_topic = topics[0] if topics else f"Complete Document Study ({doc.original_filename})"

    session = TutorService.initialize_session(
        db=db,
        ai_client=ai_client,
        user_id=current_user.id,
        subject=subj,
        topic=first_topic,
        difficulty_level=1,
        assessment_type=req.assessment_type,
        target_goal=req.goal,
        teacher_personality=req.personality,
        learning_mode=req.learning_mode,
        document_id=req.document_id
    )

    first_msg = db.query(TutorMessage).filter(TutorMessage.session_id == session.id).first()
    first_question = first_msg.content if first_msg else f"Welcome to your AI study session for **{subj}**!"

    return {
        "session_id": session.id,
        "subject": subj,
        "filename": doc.original_filename,
        "personality": req.personality,
        "goal": req.goal,
        "learning_mode": req.learning_mode,
        "assessment_type": req.assessment_type,
        "topics": topics,
        "total_topics": len(topics),
        "estimated_minutes": est_min,
        "current_topic_index": 0,
        "current_state": "WAITING_FOR_ANSWER",
        "first_question": first_question
    }
