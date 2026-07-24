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
    "text/plain",
    "text/markdown",
    ".pdf",
    ".txt",
    ".md",
})


class PDFExtractor:
    """
    Implements DocumentExtractor for PDF, TXT, and MD files.
    Uses pdfplumber / pypdf for PDF and plain text reader fallback.
    """

    def supports(self, file_type: str) -> bool:
        return file_type.lower() in _PDF_TYPES

    def extract_text(self, file_path: str) -> str:
        if file_path.endswith('.txt') or file_path.endswith('.md'):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as exc:
                logger.warning("PDFExtractor: failed reading text file %s: %s", file_path, exc)

        text_parts: list[str] = []
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text)
                    else:
                        tables = page.extract_tables() or []
                        for table in tables:
                            for row in table:
                                row_text = " \t ".join(cell or "" for cell in row if cell)
                                if row_text.strip():
                                    text_parts.append(row_text)
        except Exception as exc:
            logger.warning("PDFExtractor: pdfplumber not available or failed on %s: %s", file_path, exc)

        if not text_parts or not "".join(text_parts).strip():
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    txt = page.extract_text() or ""
                    if txt.strip():
                        text_parts.append(txt)
            except Exception as exc2:
                logger.warning("PDFExtractor: pypdf fallback also failed on %s: %s", file_path, exc2)

        if not text_parts or not "".join(text_parts).strip():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_txt = f.read()
                    if len(raw_txt.strip()) > 10:
                        return raw_txt
            except Exception:
                pass

        result = "\n".join(text_parts)
        logger.info(
            "PDFExtractor: extracted %d chars from %s",
            len(result), file_path,
        )
        return result
