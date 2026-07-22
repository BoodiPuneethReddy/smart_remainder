"""
services/document_import/field_extractor.py — Per-document-type field extraction

Extracts specific fields from text for each document type.
All extraction is deterministic (regex + date parsing).
The AI never participates in field extraction.

Supported document types:
  assignment_notice → subject, title, due_date, submission_time, faculty, instructions
  exam_schedule     → subject, exam_type, date, time, venue, duration
  timetable         → subject, day, time, faculty, room
"""

import re
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field as dc_field

from app.services.document_import.confidence import (
    ExtractedField,
    FieldConfidence,
    score_field,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDocument:
    """Result of field extraction for one document type."""
    document_type: str
    fields: list[ExtractedField]
    missing_required: list[str]  # field names where value is None
    extraction_confidence: float  # average of high/medium scores


# ─── Date/time helpers ─────────────────────────────────────────────────────────

_DATE_FORMATS = [
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
    r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{2,4}",
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}[,\s]+\d{4}",
    r"\d{4}[-/]\d{2}[-/]\d{2}",
]
_DATE_PATTERN = "(" + "|".join(_DATE_FORMATS) + ")"

_TIME_PATTERN = r"(\d{1,2}[:.]\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))"

# ─── Assignment Notice ─────────────────────────────────────────────────────────

_ASSIGNMENT_PATTERNS = {
    "subject": (
        "Subject / Course",
        [
            r"subject\s*:\s*(.+?)(?:\n|$)",
            r"course\s*(?:name|title)?\s*:\s*(.+?)(?:\n|$)",
            r"paper\s*:\s*(.+?)(?:\n|$)",
            r"module\s*:\s*(.+?)(?:\n|$)",
        ],
        ["course code", "subject code", "department"],
    ),
    "title": (
        "Assignment Title",
        [
            r"assignment\s*(?:title|topic|name)?\s*:\s*(.+?)(?:\n|$)",
            r"title\s*:\s*(.+?)(?:\n|$)",
            r"topic\s*:\s*(.+?)(?:\n|$)",
        ],
        ["deadline", "submission", "marks"],
    ),
    "due_date": (
        "Due Date",
        [
            r"(?:due\s+(?:date|on|by)|deadline|submission\s+date|submit\s+by)\s*:?\s*" + _DATE_PATTERN,
            r"last\s+date\s+(?:of\s+)?submission\s*:?\s*" + _DATE_PATTERN,
        ],
        ["submission", "deadline", "submit"],
    ),
    "submission_time": (
        "Submission Time",
        [
            r"(?:submission\s+time|due\s+time|by)\s*:?\s*" + _TIME_PATTERN,
            r"time\s*:\s*" + _TIME_PATTERN,
        ],
        ["submission", "due"],
    ),
    "faculty": (
        "Faculty / Instructor",
        [
            r"(?:faculty|instructor|professor|prof\.?|dr\.?|lecturer)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
            r"assigned\s+by\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
        ],
        ["department", "subject"],
    ),
    "instructions": (
        "Instructions",
        [
            r"instructions?\s*:?\s*(.{20,300}?)(?:\n\n|\Z)",
            r"guidelines?\s*:?\s*(.{20,300}?)(?:\n\n|\Z)",
            r"note\s*:?\s*(.{20,300}?)(?:\n\n|\Z)",
        ],
        [],
    ),
}

# ─── Exam Schedule ─────────────────────────────────────────────────────────────

_EXAM_PATTERNS = {
    "subject": (
        "Subject / Course",
        [
            r"subject\s*:\s*(.+?)(?:\n|$)",
            r"course\s*:\s*(.+?)(?:\n|$)",
            r"paper\s*:\s*(.+?)(?:\n|$)",
        ],
        ["exam", "date", "venue"],
    ),
    "exam_type": (
        "Exam Type",
        [
            r"(end[\s\-]+semester|mid[\s\-]+semester|internal\s+assessment|quiz|test|practical\s+exam)",
            r"exam(?:ination)?\s+type\s*:\s*(.+?)(?:\n|$)",
        ],
        ["semester", "internal", "external"],
    ),
    "date": (
        "Exam Date",
        [
            r"(?:exam\s+date|date\s+of\s+exam|date)\s*:?\s*" + _DATE_PATTERN,
            r"scheduled\s+(?:on|for)\s*:?\s*" + _DATE_PATTERN,
            _DATE_PATTERN,
        ],
        ["exam", "venue", "time"],
    ),
    "time": (
        "Exam Time",
        [
            r"(?:exam\s+time|time\s+of\s+exam|reporting\s+time|start\s+time)\s*:?\s*" + _TIME_PATTERN,
            r"from\s+" + _TIME_PATTERN,
        ],
        ["exam", "venue"],
    ),
    "venue": (
        "Venue / Hall",
        [
            r"(?:venue|hall|room|center|centre)\s*(?:no\.?)?\s*:?\s*(.+?)(?:\n|$)",
            r"examination\s+hall\s*:?\s*(.+?)(?:\n|$)",
        ],
        ["exam", "date"],
    ),
    "duration": (
        "Duration",
        [
            r"duration\s*:?\s*(\d+(?:\.\d+)?\s*(?:hours?|hrs?|minutes?|mins?))",
            r"time\s+allowed\s*:?\s*(\d+(?:\.\d+)?\s*(?:hours?|hrs?))",
            r"(\d+(?:\.\d+)?)\s*hours?\s+exam",
        ],
        ["exam", "time"],
    ),
}

# ─── Timetable ─────────────────────────────────────────────────────────────────

_TIMETABLE_PATTERNS = {
    "subject": (
        "Subject / Course",
        [
            r"subject\s*:\s*(.+?)(?:\n|$)",
            r"course\s*:\s*(.+?)(?:\n|$)",
        ],
        ["room", "faculty", "day"],
    ),
    "day": (
        "Day",
        [
            r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            r"day\s*:\s*(mon|tue|wed|thu|fri|sat|sun)",
        ],
        ["time", "room"],
    ),
    "time": (
        "Class Time",
        [
            r"(?:class\s+)?time\s*:?\s*" + _TIME_PATTERN,
            _TIME_PATTERN + r"\s*[-–to]+\s*" + _TIME_PATTERN,
        ],
        ["room", "day"],
    ),
    "faculty": (
        "Faculty",
        [
            r"(?:faculty|instructor|professor|prof\.?|dr\.?)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
        ],
        ["room", "subject"],
    ),
    "room": (
        "Room / Location",
        [
            r"(?:room|hall|lab|venue)\s*(?:no\.?)?\s*:?\s*(.+?)(?:\n|$)",
            r"location\s*:?\s*(.+?)(?:\n|$)",
        ],
        ["day", "time"],
    ),
}

_PATTERNS_MAP = {
    "assignment_notice": _ASSIGNMENT_PATTERNS,
    "exam_schedule": _EXAM_PATTERNS,
    "timetable": _TIMETABLE_PATTERNS,
}

_REQUIRED_FIELDS = {
    "assignment_notice": ["subject", "due_date"],
    "exam_schedule": ["subject", "date"],
    "timetable": ["subject", "day", "time"],
}


def extract_fields(text: str, document_type: str) -> ExtractedDocument:
    """
    Extract fields for the given document type from extracted text.

    Returns ExtractedDocument with per-field confidence levels.
    Low/not-found fields have value=None — never guessed.
    """
    patterns_map = _PATTERNS_MAP.get(document_type)
    if not patterns_map:
        logger.warning("FieldExtractor: unknown document type '%s'", document_type)
        return ExtractedDocument(
            document_type=document_type,
            fields=[],
            missing_required=[],
            extraction_confidence=0.0,
        )

    extracted_fields: list[ExtractedField] = []
    for field_name, (display_label, patterns, corroborating) in patterns_map.items():
        ef = score_field(
            field_name=field_name,
            display_label=display_label,
            patterns=patterns,
            text=text,
            corroborating_patterns=corroborating,
        )
        extracted_fields.append(ef)

    required = _REQUIRED_FIELDS.get(document_type, [])
    missing = [
        ef.field_name for ef in extracted_fields
        if ef.field_name in required and ef.value is None
    ]

    # Confidence = fraction of fields that have HIGH or MEDIUM confidence
    confident_count = sum(
        1 for ef in extracted_fields
        if ef.confidence in (FieldConfidence.HIGH, FieldConfidence.MEDIUM)
    )
    extraction_confidence = confident_count / max(len(extracted_fields), 1)

    logger.info(
        "FieldExtractor: type=%s fields=%d missing_required=%s confidence=%.2f",
        document_type, len(extracted_fields), missing, extraction_confidence,
    )

    return ExtractedDocument(
        document_type=document_type,
        fields=extracted_fields,
        missing_required=missing,
        extraction_confidence=extraction_confidence,
    )


def extract_for_mixed(text: str, detected_types: list[str]) -> list[ExtractedDocument]:
    """
    For mixed documents: extract fields for each detected type independently.
    Returns a list of ExtractedDocument (one per detected type).
    """
    return [extract_fields(text, dt) for dt in detected_types]


def extract_entities_generic(text: str) -> list[ExtractedField]:
    """
    Fallback for unknown_academic: extract any recognizable entities
    (dates, times, course-like words) without type-specific patterns.
    """
    results = []

    date_field = score_field(
        "detected_date", "Detected Date",
        [_DATE_PATTERN], text, corroborating_patterns=[]
    )
    results.append(date_field)

    time_field = score_field(
        "detected_time", "Detected Time",
        [_TIME_PATTERN], text, corroborating_patterns=[]
    )
    results.append(time_field)

    subject_field = score_field(
        "detected_subject", "Possible Subject",
        [r"(?:subject|course|paper)\s*:\s*(.+?)(?:\n|$)"], text
    )
    results.append(subject_field)

    return [f for f in results if f.value is not None]
