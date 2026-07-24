"""api/routes/import_routes.py — Document Import API"""

import os
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.models.imported_document import ImportedDocument
from app.services.ai_client import AIInferenceClient, get_ai_client
from app.services.document_import.pipeline import upload_and_preview, approve_import
from app.services.document_import.ocr_status import OCR_AVAILABLE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["import"])

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class ApproveRequest(BaseModel):
    import_id: int
    reviewed_sections: list[dict]   # [{document_type, fields: {name: value}}]


@router.get("/capabilities")
def get_capabilities():
    """
    Returns what file types are currently supported.
    Image OCR availability depends on Tesseract being installed.
    Frontend uses this to show 'Supported ✓ PDF / ✗ Image OCR (install Tesseract)'
    """
    return {
        "pdf": True,
        "image": OCR_AVAILABLE,
        "ocr_message": None if OCR_AVAILABLE else (
            "Image OCR is unavailable. PDF imports work normally. "
            "Install Tesseract to enable image extraction: "
            "https://github.com/UB-Mannheim/tesseract/wiki"
        ),
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AIInferenceClient = Depends(get_ai_client),
):
    """
    Stage 1 of import pipeline: Upload file, run extraction + classification.
    Returns ImportPreview for frontend review. No tasks created yet.
    """
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: PDF, JPG, PNG.",
        )

    if ext in (".jpg", ".jpeg", ".png") and not OCR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Image OCR is unavailable. Please upload a PDF instead, "
                "or install Tesseract to enable image imports."
            ),
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    try:
        preview = upload_and_preview(
            file_content=content,
            original_filename=filename,
            user_id=current_user.id,
            db=db,
        )
    except Exception as exc:
        logger.error("Import upload failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed. Please try again.",
        )

    # Convert dataclasses to dicts for JSON response
    return {
        "import_id": preview.import_id,
        "original_filename": preview.original_filename,
        "document_type": preview.document_type,
        "classification_confidence": preview.classification_confidence,
        "is_mixed": preview.is_mixed,
        "is_unknown": preview.is_unknown,
        "ocr_used": preview.ocr_used,
        "extracted_text_snippet": preview.extracted_text_snippet,
        "sections": [
            {
                "document_type": s.document_type,
                "display_name": s.display_name,
                "fields": [
                    {
                        "field_name": f.field_name,
                        "display_label": f.display_label,
                        "value": f.value,
                        "confidence": f.confidence,
                    }
                    for f in s.fields
                ],
                "missing_required": s.missing_required,
                "possible_duplicates": s.possible_duplicates,
            }
            for s in preview.sections
        ],
    }


@router.post("/approve")
def approve_document_import(
    body: ApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AIInferenceClient = Depends(get_ai_client),
):
    """
    Stage 2: User reviewed and approved fields. Create tasks, run planner+reminder, get AI summary.
    Nothing was saved before this call — this is the gate.
    """
    try:
        result = approve_import(
            import_id=body.import_id,
            reviewed_sections=body.reviewed_sections,
            user_id=current_user.id,
            db=db,
            ai_client=ai_client,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Import approve failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import approval failed. Please try again.",
        )
    return result


@router.get("/history")
def get_import_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
):
    """Returns the user's most recent document imports for the dashboard widget."""
    records = (
        db.query(ImportedDocument)
        .filter(ImportedDocument.user_id == current_user.id)
        .order_by(ImportedDocument.uploaded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "original_filename": r.original_filename,
            "document_type": r.document_type,
            "status": r.status,
            "confidence_overall": r.confidence_overall,
            "uploaded_at": r.uploaded_at.isoformat(),
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        }
        for r in records
    ]


@router.get("/{import_id}/source")
def view_source_document(
    import_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    View Source: serve the original uploaded file for traceability.
    Judges can verify extracted fields came from the actual document.
    """
    record = db.query(ImportedDocument).filter(
        ImportedDocument.id == import_id,
        ImportedDocument.user_id == current_user.id,
    ).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")

    if not os.path.exists(record.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file no longer available on disk.",
        )

    return FileResponse(
        path=record.storage_path,
        media_type=record.mime_type or "application/octet-stream",
        filename=record.original_filename,
    )
