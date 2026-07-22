"""
agents/intent_classifier.py — Intent Classifier

Classifies user messages into one of 14 intent categories.
Rule-based regex matching is used first — no AI call for greetings, casual talk, etc.
Only falls back to heuristics for ambiguous messages.

Golden Rule: EVERY message goes through this classifier before ANY agent or AI call.
This is enforced by the entry point in recommendation_agent.py.
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    GREETING = "greeting"
    GOODBYE = "goodbye"
    GRATITUDE = "gratitude"
    SMALL_TALK = "small_talk"
    STUDY_PLANNING = "study_planning"
    SCHEDULE_CONSTRAINT = "schedule_constraint"
    TASK_COMPLETION = "task_completion"
    INFORMATION_QUERY = "information_query"
    TUTOR = "tutor"
    MOTIVATION = "motivation"
    DOCUMENT_IMPORT = "document_import"
    PROFILE_ACCOUNT = "profile_account"
    HELP = "help"
    CASUAL = "casual"
    LEARNING_ANALYTICS = "learning_analytics"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    intents: list[Intent]          # All matched intents (compound support)
    primary_intent: Intent         # First/highest-confidence intent
    confidence: float              # 0–1
    entities: dict                 # Extracted entities (subject, time, etc.)
    needs_clarification: bool      # True if confidence too low to act


# ── Rule sets (checked in priority order) ─────────────────────────────────────

_RULES: list[tuple[Intent, list[str]]] = [
    # No AI call needed for these — pure pattern match
    (Intent.GREETING, [
        r"^(?:hi|hello|hey|yo|good\s+(?:morning|afternoon|evening|day)|sup|what'?s up)\b",
        r"^greetings\b",
        r"^howdy\b",
    ]),
    (Intent.GOODBYE, [
        r"\b(?:bye|goodbye|see\s+you|later|take\s+care|farewell|cya|good\s+night)\b",
    ]),
    (Intent.GRATITUDE, [
        r"\b(?:thanks?|thank\s+you|appreciate\s+(?:it|that|you)|thx|ty|cheers)\b",
    ]),
    (Intent.HELP, [
        r"\b(?:help|what\s+can\s+you\s+do|show\s+(?:commands?|features?)|how\s+do\s+(?:I|you)|capabilities?)\b",
    ]),
    (Intent.CASUAL, [
        r"^(?:who\s+are\s+you|what\s+(?:is|are)\s+you|tell\s+me\s+(?:a\s+)?joke|what'?s\s+your\s+name|nice\.?|cool\.?|okay\.?|ok\.?|lol|haha)\b",
        r"^(?:are\s+you\s+(?:a\s+)?(?:bot|ai|human|robot)|you'?re\s+(?:great|awesome|cool))\b",
    ]),
    (Intent.SMALL_TALK, [
        r"\b(?:how\s+are\s+you|how'?s\s+(?:it\s+going|life|everything)|what'?s\s+new|how\s+do\s+you\s+feel)\b",
    ]),
    # Document import — before study planning
    (Intent.DOCUMENT_IMPORT, [
        r"\b(?:import|read\s+this|scan\s+this|extract\s+from|parse\s+(?:this|my))\b",
        r"\b(?:read|import|scan)\s+my\s+(?:timetable|schedule|pdf|image|assignment|exam)\b",
    ]),
    # Profile/account — prevent routing to planner
    (Intent.PROFILE_ACCOUNT, [
        r"\b(?:change|update|edit|reset|modify)\s+(?:my\s+)?(?:password|email|name|college|profile|dob|date\s+of\s+birth)\b",
        r"\b(?:forgot\s+password|account\s+settings|my\s+profile)\b",
    ]),
    # Task completion
    (Intent.TASK_COMPLETION, [
        r"\b(?:finished|completed?|finish|done\s+with|just\s+(?:finished|completed?)|submitted)\s+(?:my\s+)?(?:task|\d+|[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)\b",
        r"\bmark\s+(?:[A-Za-z0-9]+\s+)?(?:as\s+)?(?:complete|done|finished)\b",
    ]),
    # Schedule constraint
    (Intent.SCHEDULE_CONSTRAINT, [
        r"\b(?:only\s+have|free\s+(?:for|until|after)|just\s+(?:\d+|one|two|three|four|five|six)|can\s+only\s+study|available\s+(?:for|until|after)|got\s+(?:only\s+)?(?:\d+|one|two|three|four|five|six))\b",
        r"\b(?:reschedule|adjust\s+(?:my\s+)?(?:plan|schedule)|shorter\s+session|missed|skipped)\b",
        r"\b(?:have|got|with)\s*(?:only|just)?\s*(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|an?)\s*(?:hours?|hrs?|minutes?|mins?)\b",
        r"\b(?:only|just)\s*(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|an?)\s*(?:hours?|hrs?|minutes?|mins?)\b",
        r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|an?)\s*(?:hours?|hrs?|minutes?|mins?)\s+(?:today|available|free|only|before|until|left|to\s+prepare|to\s+study)\b",
        r"\b(?:before|until|after)\s+(?:dinner|lunch|breakfast|work|school|\d+\s*(?:am|pm|o'?clock))\b",
    ]),
    # Motivation
    (Intent.MOTIVATION, [
        r"\b(?:stressed?|anxious|overwhelmed|tired|can'?t\s+focus|burned?\s+out|frustrated|worried|scared|nervous)\b",
        r"\b(?:don'?t\s+know\s+where\s+to\s+start|feeling\s+(?:lost|stuck|behind))\b",
    ]),
    # Tutor query — Socratic learning, definitions & academic concepts
    (Intent.TUTOR, [
        r"\b(?:explain|teach\s+me|quiz\s+me|definition\s+of|how\s+does|what\s+is\s+(?:normalization|recursion|binary\s+search|sql|a\s+|an\s+)?)\b",
        r"\b(?:recursion|normalization|sql|binary\s+search|algorithm|database|data\s+structure)\b",
    ]),
    # Information query
    (Intent.INFORMATION_QUERY, [
        r"\b(?:what'?s?\s+due|when\s+is|list\s+my|show\s+me|how\s+many|what\s+are\s+my)\b",
        r"\b(?:upcoming|overdue|deadlines?|this\s+week|next\s+week)\b",
    ]),
    # Learning analytics queries
    (Intent.LEARNING_ANALYTICS, [
        r"\b(?:how\s+am\s+I\s+improving|what\s+should\s+I\s+revise|what\s+topics\s+am\s+I\s+forgetting|show\s+my\s+weakest\s+concepts|how\s+is\s+my\s+learning\s+progress|show\s+my\s+mastery|do\s+I\s+need\s+revision\s+today|analytics|progress\s+report)\b",
        r"\b(?:forgetting|mastery|revision|improving|progress|retention|streak|analytics)\b",
    ]),
    # Study planning — most general, check last
    (Intent.STUDY_PLANNING, [
        r"\b(?:what\s+should\s+I\s+study|help\s+me\s+(?:study|plan)|study\s+plan|plan\s+for\s+today|prioritize|my\s+schedule|remind\s+me)\b",
        r"\b(?:what\s+to\s+study|which\s+subject|study\s+(?:next|now|today|first))\b",
    ]),
]

_LOW_CONFIDENCE_THRESHOLD = 0.35


def _extract_subject(message: str) -> Optional[str]:
    """Extract subject name from task completion messages."""
    patterns = [
        r"(?:finished|completed?|done\s+with|submitted)\s+(?:my\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"mark\s+([A-Z][a-z]+)\s+(?:as\s+)?(?:complete|done)",
    ]
    for p in patterns:
        m = re.search(p, message)
        if m:
            return m.group(1).strip()
    m = re.search(r"(?:finished|completed?|done\s+with)\s+(\w+)", message, re.IGNORECASE)
    return m.group(1) if m else None


_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5, "a": 1, "an": 1
}

def _extract_time_minutes(message: str) -> Optional[int]:
    """Extract available minutes from constraint messages."""
    msg = message.lower()
    for word, num in _WORD_TO_NUM.items():
        msg = re.sub(rf"\b{word}\b", str(num), msg)

    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)", msg)
    if m:
        return int(float(m.group(1)) * 60)
    m = re.search(r"(\d+)\s*(?:minutes?|mins?)", msg)
    if m:
        return int(m.group(1))
    return None


def classify(message: str) -> IntentResult:
    """
    Classify a user message into one or more intent categories.

    Rule-based first — no AI call for clearly-patterned intents.
    Returns all matched intents for compound handling.
    Same message → same classification always (deterministic).
    """
    if not message or not message.strip():
        return IntentResult(
            intents=[Intent.UNKNOWN],
            primary_intent=Intent.UNKNOWN,
            confidence=0.0,
            entities={},
            needs_clarification=True,
        )

    msg_lower = message.strip().lower()
    matched_intents: list[Intent] = []

    for intent, patterns in _RULES:
        for pattern in patterns:
            try:
                if re.search(pattern, msg_lower, re.IGNORECASE):
                    if intent not in matched_intents:
                        matched_intents.append(intent)
                    break
            except re.error:
                continue

    entities = {}
    if Intent.TASK_COMPLETION in matched_intents:
        subject = _extract_subject(message)
        if subject:
            entities["completed_subject"] = subject

    if Intent.SCHEDULE_CONSTRAINT in matched_intents:
        minutes = _extract_time_minutes(message)
        if minutes:
            entities["available_minutes"] = minutes

    if not matched_intents:
        confidence = 0.2
        matched_intents = [Intent.UNKNOWN]
    elif len(matched_intents) == 1:
        confidence = 0.9
    else:
        confidence = 0.75  # Compound message

    primary = matched_intents[0]
    needs_clarification = confidence < _LOW_CONFIDENCE_THRESHOLD

    logger.info(
        "IntentClassifier: intents=%s confidence=%.2f entities=%s",
        [i.value for i in matched_intents], confidence, entities,
    )

    return IntentResult(
        intents=matched_intents,
        primary_intent=primary,
        confidence=confidence,
        entities=entities,
        needs_clarification=needs_clarification,
    )
