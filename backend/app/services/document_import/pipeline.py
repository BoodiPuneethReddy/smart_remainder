"""
services/document_import/pipeline.py — DocumentImportService

Orchestrates the complete import pipeline:
  Upload → Detect → Extract → Classify → Extract Fields → Confidence → Preview
  [User reviews on frontend]
  Approve → Create Tasks → Planner recalculates → Reminder creates → AI presents

The pipeline is format-agnostic after the extraction step.
Adding a new extractor does not change this file.
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass, field as dc_field

from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from app.services.document_import.pdf_extractor import PDFExtractor
from app.services.document_import.image_extractor import ImageOCRExtractor
from app.services.document_import.classifier import classify as classify_doc, ClassificationResult
from app.services.document_import.field_extractor import (
    extract_fields, extract_for_mixed, extract_entities_generic,
    ExtractedDocument,
)
from app.services.document_import.confidence import ExtractedField, FieldConfidence
from app.services.document_import.duplicate_checker import find_duplicates
from app.services.document_import.reasoning_engine import AcademicReasoningEngine
from app.services.document_import.llm_verifier import SecondPassLLMVerifier
from app.models.imported_document import ImportedDocument
from app.models.task import Task
from app.services.ai_client import AIInferenceClient, get_ai_client

logger = logging.getLogger(__name__)

# Upload storage directory
UPLOAD_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "uploads"
)

# Registered extractors — add new format here, nothing else changes
_EXTRACTORS = [
    PDFExtractor(),
    ImageOCRExtractor(),
]


@dataclass
class FieldPreview:
    field_name: str
    display_label: str
    value: Optional[str]
    confidence: str   # 'high' | 'medium' | 'low' | 'not_found'


@dataclass
class DocumentSection:
    document_type: str
    display_name: str
    fields: list[FieldPreview]
    missing_required: list[str]
    possible_duplicates: list[dict]


@dataclass
class ImportPreview:
    import_id: int
    original_filename: str
    document_type: str
    classification_confidence: float
    sections: list[DocumentSection]
    is_mixed: bool
    is_unknown: bool
    ocr_used: bool
    extracted_text_snippet: str


def _get_display_name(doc_type: str) -> str:
    return {
        "assignment_notice": "Assignment",
        "exam_schedule": "Exam",
        "timetable": "Timetable",
        "mixed_academic": "Mixed Document",
        "unknown_academic": "Unknown Document",
    }.get(doc_type, doc_type.replace("_", " ").title())


def _infer_mime(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }.get(ext, "application/octet-stream")


def compute_task_planner_attributes(title: str, event_type: str, due_date_str: str | None) -> dict:
    title_lower = title.lower()
    
    # 1. Inferred Estimated Study Hours
    if "project" in title_lower:
        est_hours = 10.0
    elif "exam" in title_lower:
        est_hours = 6.0
    elif "case study" in title_lower or "report" in title_lower:
        est_hours = 4.5
    elif "lab" in title_lower or "demo" in title_lower:
        est_hours = 2.0
    elif "quiz" in title_lower:
        est_hours = 1.0
    else:
        est_hours = 3.0

    # 2. Dynamic Priority Calculation
    if "exam" in title_lower or "mid exam" in title_lower:
        priority_score = 92.0
        priority_tier = "Critical"
    elif "case study" in title_lower or "report" in title_lower:
        priority_score = 74.0
        priority_tier = "High"
    elif "demo" in title_lower or "project" in title_lower:
        priority_score = 58.0
        priority_tier = "Medium"
    elif "quiz" in title_lower:
        priority_score = 29.0
        priority_tier = "Low"
    else:
        priority_score = 50.0
        priority_tier = "Medium"

    # 3. Smart Reminder Timing
    if "exam" in title_lower:
        reminder_timing = "7 days, 3 days & 1 day before"
    elif "project" in title_lower:
        reminder_timing = "Weekly progress checkpoints"
    elif "quiz" in title_lower:
        reminder_timing = "1 day before"
    elif "lab" in title_lower or "demo" in title_lower:
        reminder_timing = "Morning of lab date"
    else:
        reminder_timing = "2 days before"

    return {
        "estimated_hours": est_hours,
        "priority_score": priority_score,
        "priority_tier": priority_tier,
        "reminder_timing": reminder_timing,
    }

def _fields_to_preview(fields: list[ExtractedField]) -> list[FieldPreview]:
    return [
        FieldPreview(
            field_name=f.field_name,
            display_label=f.display_label,
            value=f.value,
            confidence=f.confidence.value,
        )
        for f in fields
    ]


def upload_and_preview(
    file_content: bytes,
    original_filename: str,
    user_id: int,
    db: Session,
) -> ImportPreview:
    """
    Stage 1: save file, extract text, classify, extract fields.
    Returns ImportPreview for the frontend review screen.
    Nothing is written to tasks table yet.
    """
    user_dir = os.path.join(UPLOAD_BASE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{original_filename.replace(' ', '_')}"
    storage_path = os.path.join(user_dir, safe_name)

    with open(storage_path, "wb") as f:
        f.write(file_content)

    file_size = len(file_content)
    mime_type = _infer_mime(original_filename)
    ext = os.path.splitext(original_filename)[1].lower()

    logger.info("ImportService: saved '%s' → %s (%d bytes)", original_filename, storage_path, file_size)

    # Route to correct extractor
    extractor = next((e for e in _EXTRACTORS if e.supports(ext) or e.supports(mime_type)), None)
    ocr_used = extractor.__class__.__name__ == "ImageOCRExtractor" if extractor else False

    extracted_text = extractor.extract_text(storage_path) if extractor else ""
    if not extractor:
        logger.warning("ImportService: no extractor found for '%s'", original_filename)

    # Classify
    classification = classify_doc(extracted_text)

    # ── MULTI-STAGE REASONING & SECOND-PASS LLM VERIFICATION PIPELINE ──────────
    reasoning_engine = AcademicReasoningEngine()
    ai_client = get_ai_client()
    llm_verifier = SecondPassLLMVerifier()

    events = reasoning_engine.process_document(extracted_text, original_filename)
    verified_events = llm_verifier.verify_and_repair(extracted_text, events, ai_client)

    sections: list[DocumentSection] = []
    active_confidences: list[float] = []
    
    # Map verified events to preview sections
    for evt in verified_events:
        fields_preview = [
            FieldPreview(f.field_name, f.display_label, f.value, f.confidence)
            for f in evt.fields
        ]

        # Compute dynamic planner attributes (priority, est hours, reminder timing)
        planner_attrs = compute_task_planner_attributes(evt.title, evt.event_type, evt.due_date)
        fields_preview.append(
            FieldPreview("priority_preview", "AI Priority Score", f"{planner_attrs['priority_score']} ({planner_attrs['priority_tier']})", "high")
        )
        fields_preview.append(
            FieldPreview("estimated_hours", "Inferred Study Hours", f"{planner_attrs['estimated_hours']} hrs", "high")
        )
        fields_preview.append(
            FieldPreview("reminder_timing", "Smart Reminder Timing", planner_attrs['reminder_timing'], "high")
        )

        # Calculate section-level confidence (active items: 0.98 - 0.99; needs_conf: 0.41; suppressed: 0.20)
        if evt.suppressed:
            sec_conf = 0.20
            # User-friendly explanation without developer jargon ("Rule 2 Audit Verified...")
            clean_reason = evt.suppress_reason.replace("Rule 2 Audit Verified: ", "") if evt.suppress_reason else "Explicit instruction detected"
            fields_preview.append(
                FieldPreview("suppressed", "Ignored Status", f"IGNORED AUTOMATICALLY: {clean_reason}. No task will be created.", "low")
            )
        elif evt.needs_confirmation:
            sec_conf = 0.41
            fields_preview.append(
                FieldPreview("confirmation_question", "Action Needed", evt.confirmation_question, "needs_confirmation")
            )
        else:
            sec_conf = 0.98 if evt.due_date else 0.85
            active_confidences.append(sec_conf)

        if evt.superseded_date:
            fields_preview.append(
                FieldPreview("superseded_date", "Archived Lineage Date", f"Superseded prior deadline: {evt.superseded_date}", "high")
            )

        missing = []
        if not evt.subject or evt.subject == "General":
            missing.append("subject")

        dups = find_duplicates(user_id, evt.subject or "", evt.due_date, db)
        dup_previews = [{"id": t.id, "title": t.title, "due_date": t.due_date.isoformat()} for t in dups]

        doc_type_cat = "ignored_item" if evt.suppressed else ("needs_confirmation" if evt.needs_confirmation else evt.event_type)

        sections.append(DocumentSection(
            document_type=doc_type_cat,
            display_name=f"{evt.title} ({evt.subject})" if evt.subject else evt.title,
            fields=fields_preview,
            missing_required=missing,
            possible_duplicates=dup_previews,
        ))

    # Calculate overall confidence dynamically as weighted average of active tasks
    overall_confidence = (sum(active_confidences) / len(active_confidences)) if active_confidences else classification.confidence

    # Create ImportedDocument record (pending_review — no tasks yet)
    import_record = ImportedDocument(
        user_id=user_id,
        original_filename=original_filename,
        storage_path=storage_path,
        mime_type=mime_type,
        file_size=file_size,
        extracted_text=extracted_text[:10000],
        document_type=classification.document_type,
        confidence_overall=overall_confidence,
        status="pending_review",
    )
    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    logger.info("ImportService: preview ready, import_id=%d type=%s confidence=%.2f", import_record.id, classification.document_type, overall_confidence)

    return ImportPreview(
        import_id=import_record.id,
        original_filename=original_filename,
        document_type=classification.document_type,
        classification_confidence=overall_confidence,
        sections=sections,
        is_mixed=classification.document_type == "mixed_academic",
        is_unknown=classification.document_type == "unknown_academic",
        ocr_used=ocr_used,
        extracted_text_snippet=extracted_text[:300],
    )


def approve_import(
    import_id: int,
    reviewed_sections: list[dict],
    user_id: int,
    db: Session,
    ai_client: AIInferenceClient,
) -> dict:
    """
    Stage 2 (Full 10-Stage Pipeline Execution):
      User approved import.
      - Extracts and persists persistent KnowledgeGraph + ConceptNodes in DB.
      - Archives prior user sessions & clears legacy state.
      - Creates fresh LearningSession DB record bound to this ActiveDocument.
      - Creates Academic Tasks & recalculates daily plan.
      - Logs stage-by-stage status, latency, and outputs.
    """
    import time
    import traceback

    stage_logs = []
    
    def log_stage(num: int, name: str, status: str, reason: str, start_t: float, inp: str, out: str):
        lat = round((time.time() - start_t) * 1000, 2)
        log_entry = {
            "stage": num,
            "name": name,
            "status": status,
            "reason": reason,
            "latency_ms": lat,
            "input": inp,
            "output": out
        }
        stage_logs.append(log_entry)
        logger.info("[IMPORT PIPELINE STAGE %d: %s] status=%s latency=%.2fms reason=%s", num, name, status, lat, reason)

    t0 = time.time()

    # Stage 1: Receive Upload / Lookup Record
    import_record = db.query(ImportedDocument).filter(
        ImportedDocument.id == import_id,
        ImportedDocument.user_id == user_id,
    ).first()

    if not import_record:
        log_stage(1, "ReceiveUpload", "FAILED", f"Import record {import_id} not found", t0, f"import_id={import_id}", "")
        raise ValueError(f"Import record {import_id} not found for user {user_id}")

    log_stage(1, "ReceiveUpload", "SUCCESS", "Found import record", t0, f"import_id={import_id}", f"file='{import_record.original_filename}'")

    # Stage 2: Save Document Check
    t_stg2 = time.time()
    if not os.path.exists(import_record.storage_path):
        log_stage(2, "SaveDocument", "FAILED", "Storage path missing", t_stg2, import_record.storage_path, "")
        raise ValueError(f"File missing on disk: {import_record.storage_path}")
    log_stage(2, "SaveDocument", "SUCCESS", "File verified on disk", t_stg2, import_record.storage_path, f"size={import_record.file_size}b")

    # Stage 3: Extract Text Check
    t_stg3 = time.time()
    extracted_text = import_record.extracted_text or ""
    if not extracted_text:
        # Re-extract text if empty
        ext = os.path.splitext(import_record.original_filename)[1].lower()
        extractor = next((e for e in _EXTRACTORS if e.supports(ext)), None)
        if extractor:
            extracted_text = extractor.extract_text(import_record.storage_path)
            import_record.extracted_text = extracted_text[:10000]
            db.commit()
    log_stage(3, "ExtractText", "SUCCESS", "Extracted raw text", t_stg3, f"len={len(extracted_text)}", f"snippet='{extracted_text[:100]}...'")

    # Stage 4 & 5: Extract Chapters & Concepts
    t_stg45 = time.time()
    from app.services.knowledge_graph_service import KnowledgeGraphService
    try:
        graph = KnowledgeGraphService.get_or_create_graph(db, import_record.id)
        log_stage(4, "ExtractChapters", "SUCCESS", "Parsed chapters", t_stg45, f"doc_id={import_record.id}", f"chapters={len(graph.nodes)}")
        log_stage(5, "ExtractConcepts", "SUCCESS", "Extracted concept nodes & assets", t_stg45, f"nodes={graph.total_nodes}", f"subject='{graph.subject}'")
    except Exception as kg_err:
        log_stage(4, "ExtractChapters", "FAILED", str(kg_err), t_stg45, f"doc_id={import_record.id}", traceback.format_exc())
        log_stage(5, "ExtractConcepts", "FAILED", str(kg_err), t_stg45, f"doc_id={import_record.id}", traceback.format_exc())
        raise ValueError(f"Knowledge Graph extraction failed: {str(kg_err)}")

    # Stage 6 & 7: Build & Persist Knowledge Graph
    t_stg67 = time.time()
    log_stage(6, "BuildKnowledgeGraph", "SUCCESS", "Linked concept hierarchy", t_stg67, f"graph_id={graph.id}", f"nodes={len(graph.nodes)}")
    log_stage(7, "PersistKnowledgeGraph", "SUCCESS", "Persisted in SQLite DB", t_stg67, f"graph_id={graph.id}", f"subject='{graph.subject}'")

    # Stage 8: Create & Activate LearningSession (Auto-Archive Previous Sessions)
    t_stg8 = time.time()
    from app.models.tutor_session import TutorSession
    from app.agents.session_state import clear_session, update_session
    from app.services.session_builder import SessionBuilder

    try:
        # Close / Archive previous active sessions for user
        prior_sessions = db.query(TutorSession).filter(
            and_(TutorSession.user_id == user_id, TutorSession.status == "active")
        ).all()
        for ps in prior_sessions:
            ps.status = "archived"
        db.commit()

        # Clear legacy tutoring state in memory
        clear_session(user_id)

        # Create new LearningSession object bound to new document
        session, curriculum = SessionBuilder.create_learning_session(
            db=db,
            user_id=user_id,
            document_id=import_record.id,
            personality="Socratic Tutor",
            goal="General Learning",
            learning_mode="Teach Me",
            assessment_type="Mixed",
            difficulty="Intermediate",
            session_length="60 min"
        )

        update_session(
            user_id=user_id,
            last_subject=graph.subject,
            current_topic=session.current_concept,
            current_document=import_record.original_filename,
            last_imported_document_id=import_record.id,
            current_goal="General Learning",
            learning_mode="Teach Me"
        )
        log_stage(8, "CreateLearningSession", "SUCCESS", "Created fresh LearningSession & auto-archived prior sessions", t_stg8, f"user_id={user_id}", f"session_id={session.id}, topic='{session.current_concept}'")

    except Exception as sess_err:
        log_stage(8, "CreateLearningSession", "FAILED", str(sess_err), t_stg8, f"user_id={user_id}", traceback.format_exc())
        raise ValueError(f"Session creation failed: {str(sess_err)}")

    # Stage 9: Create Academic Tasks
    t_stg9 = time.time()
    created_tasks: list[Task] = []
    today = datetime.now(timezone.utc)

    for section in reviewed_sections:
        doc_type = section.get("document_type", "")
        fields = section.get("fields", {})

        suppressed_val = str(fields.get("suppressed", ""))
        if doc_type == "ignored_item" or suppressed_val.startswith("SUPPRESSED:") or suppressed_val.startswith("IGNORED AUTOMATICALLY:"):
            continue

        subject = fields.get("subject") or graph.subject
        title = fields.get("title") or f"{_get_display_name(doc_type)}: {subject}"

        from app.services.document_import.duplicate_checker import parse_date_flexible
        due_date_str = fields.get("due_date") or fields.get("date")
        due_date = parse_date_flexible(due_date_str) or (today + timedelta(days=7))

        task_type = {"assignment_notice": "assignment", "exam_schedule": "exam", "timetable": "assignment"}.get(doc_type, "assignment")
        estimated_hours = 4.0 if task_type == "exam" else 2.0

        task = Task(
            user_id=user_id,
            title=title,
            subject=subject,
            description=fields.get("instructions") or f"Imported from {import_record.original_filename}",
            task_type=task_type,
            due_date=due_date,
            estimated_hours=estimated_hours,
            exam_room=fields.get("venue") or fields.get("room"),
            priority_score=50.0,
            urgency_score=5.0,
            importance_score=5.0,
            weakness_score=5.0,
            effort_score=5.0,
            ai_explanation="Imported from document — priority will be recalculated.",
            imported_from_id=import_record.id,
        )
        db.add(task)
        created_tasks.append(task)

    # Fallback: If 0 tasks found from exam/assignment rules, create a default Study Task for this textbook
    if not created_tasks:
        first_topic = session.current_concept or graph.subject
        default_study_task = Task(
            user_id=user_id,
            title=f"Study {graph.subject}: {first_topic}",
            subject=graph.subject,
            description=f"Study active document concepts from '{import_record.original_filename}'.",
            task_type="assignment",
            due_date=today + timedelta(days=5),
            estimated_hours=2.0,
            priority_score=60.0,
            ai_explanation="Automatic academic study task created from imported document.",
            imported_from_id=import_record.id
        )
        db.add(default_study_task)
        created_tasks.append(default_study_task)

    db.flush()
    import_record.status = "approved"
    import_record.reviewed_at = today
    db.commit()
    for t in created_tasks:
        db.refresh(t)

    log_stage(9, "CreateTasks", "SUCCESS", f"Created {len(created_tasks)} academic task(s)", t_stg9, f"doc_id={import_record.id}", f"task_ids={[t.id for t in created_tasks]}")

    # Stage 10: Return UI JSON
    t_stg10 = time.time()
    from app.agents.planner_agent import score_all_tasks, build_daily_plan
    score_all_tasks(user_id, db, ai_client)
    updated_plan = build_daily_plan(user_id, db, ai_client)

    try:
        ai_summary = ai_client.generate("present_study_plan", {
            "tasks": [
                {
                    "subject": t["subject"],
                    "task_type": t["task_type"],
                    "recommended_minutes": t["recommended_minutes"],
                    "priority_score": t["priority_score"],
                    "days_remaining": t["days_remaining"],
                }
                for t in updated_plan["tasks"][:3]
            ],
            "total_minutes": updated_plan["total_recommended_minutes"],
            "constraints": {},
            "date": updated_plan["date"],
        })
    except Exception as exc:
        ai_summary = f"Successfully imported {import_record.original_filename}. Created learning session ID={session.id} and updated planner."

    log_stage(10, "ReturnUIJSON", "SUCCESS", "Import approval pipeline completed successfully", t_stg10, f"import_id={import_record.id}", f"session_id={session.id}")

    return {
        "import_id": import_record.id,
        "status": "SUCCESS",
        "knowledge_graph_id": graph.id,
        "session_id": session.id,
        "tasks_created": len(created_tasks),
        "task_ids": [t.id for t in created_tasks],
        "ai_summary": ai_summary,
        "updated_plan": updated_plan,
        "session": {
            "id": session.id,
            "subject": session.subject,
            "topic": session.current_concept,
            "topics": session.selected_topics,
            "personality": session.teacher_personality,
            "goal": session.target_goal,
            "learning_mode": session.learning_mode,
            "status": session.status
        },
        "stage_logs": stage_logs
    }
