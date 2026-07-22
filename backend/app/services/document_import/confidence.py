"""
services/document_import/confidence.py — FieldConfidence and ConfidenceScorer

Confidence levels for extracted fields:
  HIGH   (≥0.8) — pattern matched with 2+ corroborating signals → auto-populated
  MEDIUM (0.4–0.79) — partial match or single signal → populated, flagged for user review
  LOW    (<0.4)  — weak or no match → left blank, user must fill
  NOT_FOUND      — no evidence in text at all → blank, flagged as missing

The AI never intervenes in confidence scoring.
Same extraction input → same confidence level always.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import re


class FieldConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_FOUND = "not_found"


@dataclass
class ExtractedField:
    field_name: str
    value: Optional[str]           # None if LOW or NOT_FOUND
    raw_match: Optional[str]       # The exact regex match from the text
    confidence: FieldConfidence
    display_label: str             # Human-readable field label for UI


def score_field(
    field_name: str,
    display_label: str,
    patterns: list[str],
    text: str,
    corroborating_patterns: Optional[list[str]] = None,
) -> ExtractedField:
    """
    Try all patterns against text; score the result deterministically.

    Args:
        field_name: Machine field name (e.g. "subject")
        display_label: UI label (e.g. "Subject / Course")
        patterns: Regex patterns to try (tried in order, first match wins)
        text: Full extracted document text
        corroborating_patterns: Additional patterns that, if matched,
                                boost confidence to HIGH

    Returns:
        ExtractedField with value and confidence level.
        Value is None when confidence is LOW or NOT_FOUND.
    """
    text_lower = text.lower()
    primary_match: Optional[re.Match] = None
    matched_value: Optional[str] = None

    for pattern in patterns:
        try:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                primary_match = m
                # Use named group "val" if present, else first capture group
                try:
                    matched_value = m.group("val").strip()
                except (IndexError, AttributeError):
                    groups = m.groups()
                    matched_value = groups[0].strip() if groups else m.group(0).strip()
                break
        except re.error:
            continue

    if primary_match is None:
        return ExtractedField(
            field_name=field_name,
            value=None,
            raw_match=None,
            confidence=FieldConfidence.NOT_FOUND,
            display_label=display_label,
        )

    # Count corroborating signals
    corroborating_count = 0
    if corroborating_patterns:
        for cp in corroborating_patterns:
            try:
                if re.search(cp, text_lower):
                    corroborating_count += 1
            except re.error:
                pass

    if corroborating_count >= 2:
        confidence = FieldConfidence.HIGH
    elif corroborating_count >= 1:
        confidence = FieldConfidence.MEDIUM
    else:
        confidence = FieldConfidence.LOW

    # LOW confidence → leave blank, never guess
    if confidence == FieldConfidence.LOW:
        return ExtractedField(
            field_name=field_name,
            value=None,
            raw_match=matched_value,
            confidence=FieldConfidence.LOW,
            display_label=display_label,
        )

    return ExtractedField(
        field_name=field_name,
        value=matched_value,
        raw_match=matched_value,
        confidence=confidence,
        display_label=display_label,
    )
