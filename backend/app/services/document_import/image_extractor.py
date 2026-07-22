"""
services/document_import/image_extractor.py — ImageOCRExtractor

Extracts text from images (JPG/PNG) using Tesseract OCR via pytesseract.
Gracefully disabled if Tesseract is not installed — OCR_AVAILABLE is checked
at module import time in ocr_status.py.
"""

import logging
from app.services.document_import.protocol import DocumentExtractor
from app.services.document_import.ocr_status import OCR_AVAILABLE

logger = logging.getLogger(__name__)

_IMAGE_TYPES = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    ".jpg",
    ".jpeg",
    ".png",
})


class ImageOCRExtractor:
    """
    Implements DocumentExtractor for images using Tesseract OCR.
    Returns empty string and logs a warning if Tesseract is unavailable —
    never crashes the application.
    """

    def supports(self, file_type: str) -> bool:
        return OCR_AVAILABLE and file_type.lower() in _IMAGE_TYPES

    def extract_text(self, file_path: str) -> str:
        if not OCR_AVAILABLE:
            logger.warning(
                "ImageOCRExtractor: Tesseract not available — cannot process %s",
                file_path,
            )
            return ""

        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            logger.error("ImageOCRExtractor: missing dependency (%s)", exc)
            return ""

        try:
            # Preprocessing improves OCR accuracy on academic documents
            img = Image.open(file_path)

            # Convert to RGB if needed (handles RGBA, palette images)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # OCR with page segmentation mode 6 (uniform block of text)
            text = pytesseract.image_to_string(img, config="--psm 6")
            result = text.strip()

            logger.info(
                "ImageOCRExtractor: extracted %d chars from %s",
                len(result), file_path,
            )
            return result

        except Exception as exc:
            logger.warning(
                "ImageOCRExtractor: OCR failed for %s: %s — returning empty string",
                file_path, exc,
            )
            return ""
