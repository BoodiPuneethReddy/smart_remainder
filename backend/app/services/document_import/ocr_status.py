"""
services/document_import/ocr_status.py — Tesseract OCR availability check.

Runs once at module import time. Sets OCR_AVAILABLE as a module constant.
All code that needs to know if OCR works imports from here — single source of truth.
"""
import shutil
import logging

logger = logging.getLogger(__name__)

def _detect_tesseract() -> bool:
    """Check if Tesseract binary is on PATH."""
    try:
        path = shutil.which("tesseract")
        if path:
            logger.info("Tesseract OCR: available at %s — image imports enabled", path)
            return True
        else:
            logger.warning(
                "Tesseract OCR: not found on PATH — image imports disabled. "
                "Install: https://github.com/UB-Mannheim/tesseract/wiki (Windows) "
                "or `apt install tesseract-ocr` (Linux)."
            )
            return False
    except Exception as exc:
        logger.warning("Tesseract OCR: detection failed (%s) — image imports disabled", exc)
        return False


# Module constant — imported by extractors, API routes, and frontend capability endpoint
OCR_AVAILABLE: bool = _detect_tesseract()
