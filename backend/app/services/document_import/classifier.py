"""
services/document_import/classifier.py — DocumentClassifier

Classifies extracted document text into one of five categories:
  - assignment_notice
  - exam_schedule
  - timetable
  - mixed_academic   (two or more types detected with confidence)
  - unknown_academic (no type detected above threshold)

Fully deterministic — no AI calls. Same text → same classification always.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

DocumentType = Literal[
    "assignment_notice",
    "exam_schedule",
    "timetable",
    "mixed_academic",
    "unknown_academic",
]

# Keyword groups per document type (order matters — more specific first)
_KEYWORDS: dict[str, list[str]] = {
    "assignment_notice": [
        "assignment",
        "submission",
        r"submit\s+by",
        r"due\s+date",
        r"due\s+on",
        "deadline",
        r"marks?\s*:\s*\d+",
        "weightage",
        r"hand\s*in",
        "project report",
        "lab report",
        "term paper",
        "coursework",
    ],
    "exam_schedule": [
        r"exam(?:ination)?",
        r"end\s*[\-–]?\s*semester",
        r"mid\s*[\-–]?\s*semester",
        r"hall\s*ticket",
        r"seat\s*no",
        "invigilator",
        r"answer\s*sheet",
        r"exam\s*hall",
        r"examination\s*center",
        r"internal\s*assessment",
        "quiz date",
        "test schedule",
    ],
    "timetable": [
        "timetable",
        r"time\s*table",
        r"class\s*schedule",
        r"lecture\s*schedule",
        r"period\s*\d",
        r"room\s*no",
        r"lab\s*session",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        r"slot\s*[A-Z]\d",
        "theory hours",
        "practical hours",
    ],
}

# Score threshold above which a type is "detected"
_DETECTION_THRESHOLD = 2
# Score above which it's considered "mixed" (two types both above threshold)
_MIXED_THRESHOLD = 2


@dataclass
class ClassificationResult:
    document_type: DocumentType
    scores: dict[str, int]
    detected_types: list[str]
    confidence: float   # 0–1, used for downstream UI


def classify(text: str) -> ClassificationResult:
    """
    Classify extracted document text into one of the five document types.

    Args:
        text: Raw extracted text from PDFExtractor or ImageOCRExtractor.

    Returns:
        ClassificationResult with document_type and per-type scores.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for doc_type, keywords in _KEYWORDS.items():
        score = 0
        for kw in keywords:
            matches = len(re.findall(kw, text_lower))
            score += matches
        scores[doc_type] = score

    detected = [t for t, s in scores.items() if s >= _DETECTION_THRESHOLD]
    max_score = max(scores.values()) if scores else 0

    if len(detected) == 0 or max_score < _DETECTION_THRESHOLD:
        doc_type = "unknown_academic"
        confidence = 0.2
    elif len(detected) >= 2:
        doc_type = "mixed_academic"
        confidence = min(0.95, 0.5 + (sum(scores[t] for t in detected) / 30))
    else:
        doc_type = detected[0]
        confidence = min(0.98, 0.5 + (max_score / 20))

    logger.info(
        "DocumentClassifier: type=%s scores=%s confidence=%.2f",
        doc_type, scores, confidence,
    )

    return ClassificationResult(
        document_type=doc_type,
        scores=scores,
        detected_types=detected,
        confidence=confidence,
    )
