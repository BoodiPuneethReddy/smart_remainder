"""
services/document_import/pdf_extractor.py — PDFExtractor

Extracts text from PDF files using pdfplumber.
Handles multi-page documents, tables, and mixed layouts.
"""

import logging
from app.services.document_import.protocol import DocumentExtractor

logger = logging.getLogger(__name__)

_PDF_TYPES = frozenset({
    "application/pdf",
    "application/x-pdf",
    ".pdf",
})


class PDFExtractor:
    """
    Implements DocumentExtractor for PDF files.
    Uses pdfplumber for reliable text extraction including tables.
    """

    def supports(self, file_type: str) -> bool:
        return file_type.lower() in _PDF_TYPES

    def extract_text(self, file_path: str) -> str:
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed — cannot extract PDF text")
            return ""

        text_parts: list[str] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text)
                    else:
                        # Fallback to extract_tables only if extract_text is empty
                        tables = page.extract_tables() or []
                        for table in tables:
                            for row in table:
                                row_text = " \t ".join(cell or "" for cell in row if cell)
                                if row_text.strip():
                                    text_parts.append(row_text)
        except Exception as exc:
            logger.warning("PDFExtractor: failed to extract from %s: %s", file_path, exc)
            return ""

        result = "\n".join(text_parts)
        logger.info(
            "PDFExtractor: extracted %d chars from %s",
            len(result), file_path,
        )
        return result
