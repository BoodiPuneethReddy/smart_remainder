"""
agents/intent_classifier.py — Multi-Turn Intent & Entity Classifier

Classifies user messages into intent categories and extracts structured entities
including relative date shifts (tomorrow, next week), time constraints (minutes/hours),
subject keywords, and follow-up flags.

Golden Rule: No query ever returns 'needs_clarification=True' to trigger canned greetings.
Ambiguous follow-ups inherit session context from session_state.
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

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
    intents: List[Intent]          # All matched intents (compound support)
    primary_intent: Intent         # First/highest-confidence intent
    confidence: float              # 0–1
    entities: Dict[str, Any]       # Extracted entities (subject, time, date_shift, is_followup, etc.)
    needs_clarification: bool      # Always False — system resolves ambiguous context from session memory


# ── Rule sets (checked in priority order) ─────────────────────────────────────

_RULES: List[tuple[Intent, List[str]]] = [
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
    (Intent.DOCUMENT_IMPORT, [
        r"\b(?:import|read\s+this|scan\s+this|extract\s+from|parse\s+(?:this|my))\b",
        r"\b(?:read|import|scan)\s+my\s+(?:timetable|schedule|pdf|image|assignment|exam)\b",
    ]),
    (Intent.PROFILE_ACCOUNT, [
        r"\b(?:change|update|edit|reset|modify)\s+(?:my\s+)?(?:password|email|name|college|profile|dob|date\s+of\s+birth)\b",
        r"\b(?:forgot\s+password|account\s+settings|my\s+profile)\b",
    ]),
    (Intent.TASK_COMPLETION, [
        r"\b(?:finished|completed?|finish|done\s+with|just\s+(?:finished|completed?)|submitted)\s+(?:my\s+)?(?:task|\d+|[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)\b",
        r"\bmark\s+(?:[A-Za-z0-9]+\s+)?(?:as\s+)?(?:complete|done|finished)\b",
    ]),
    (Intent.SCHEDULE_CONSTRAINT, [
        r"\b(?:what\s+about\s+tomorrow|what\s+about\s+next\s+week|how\s+about\s+tomorrow)\b",
        r"\b(?:only\s+have|free\s+(?:for|until|after)|just\s+(?:\d+|one|two|three|four|five|six)|can\s+only\s+study|available\s+(?:for|until|after)|got\s+(?:only\s+)?(?:\d+|one|two|three|four|five|six))\b",
        r"\b(?:reschedule|adjust\s+(?:my\s+)?(?:plan|schedule)|shorter\s+session|missed|skipped)\b",
        r"\b(?:have|got|with)\s*(?:only|just)?\s*(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|an?)\s*(?:hours?|hrs?|minutes?|mins?)\b",
        r"\b(?:only|just)\s*(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|an?)\s*(?:hours?|hrs?|minutes?|mins?)\b",
        r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|an?)\s*(?:hours?|hrs?|minutes?|mins?)\s+(?:today|tomorrow|available|free|only|before|until|left|to\s+prepare|to\s+study)\b",
        r"\b(?:before|until|after)\s+(?:dinner|lunch|breakfast|work|school|\d+\s*(?:am|pm|o'?clock))\b",
    ]),
    (Intent.MOTIVATION, [
        r"\b(?:stressed?|anxious|overwhelmed|tired|can'?t\s+focus|burned?\s+out|frustrated|worried|scared|nervous)\b",
        r"\b(?:don'?t\s+know\s+where\s+to\s+start|feeling\s+(?:lost|stuck|behind))\b",
    ]),
    (Intent.TUTOR, [
        r"\b(?:explain|teach\s+me|quiz\s+me|definition\s+of|how\s+does|what\s+is|tell\s+me\s+about|simplify|simplify\s+that|give\s+(?:another|an?)\s+example|continue|why|why\?|why\s+is\s+that|can\s+I\s+skip|summarize)\b",
        r"\b(?:recursion|normalization|bcnf|sql|binary\s+search|algorithm|database|data\s+structure|operating\s+system|deadlock)\b",
    ]),
    (Intent.INFORMATION_QUERY, [
        r"\b(?:what'?s?\s+due|when\s+is|list\s+my|show\s+me|how\s+many|what\s+are\s+my)\b",
        r"\b(?:upcoming|overdue|deadlines?|this\s+week|next\s+week)\b",
    ]),
    (Intent.LEARNING_ANALYTICS, [
        r"\b(?:how\s+am\s+I\s+improving|what\s+should\s+I\s+revise|what\s+topics\s+am\s+I\s+forgetting|show\s+my\s+weakest\s+concepts|how\s+is\s+my\s+learning\s+progress|show\s+my\s+mastery|do\s+I\s+need\s+revision\s+today|analytics|progress\s+report)\b",
        r"\b(?:forgetting|mastery|revision|improving|progress|retention|streak|analytics)\b",
    ]),
    (Intent.STUDY_PLANNING, [
        r"\b(?:what\s+should\s+I\s+study|help\s+me\s+(?:study|plan)|study\s+plan|plan\s+for\s+today|prioritize|my\s+schedule|remind\s+me)\b",
        r"\b(?:what\s+to\s+study|which\s+subject|study\s+(?:next|now|today|first))\b",
    ]),
]

_COMPILED_RULES: List[tuple[Intent, List[re.Pattern]]] = [
    (intent, [re.compile(p, re.IGNORECASE) for p in patterns])
    for intent, patterns in _RULES
]


_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5, "a": 1, "an": 1
}


def _extract_time_minutes(message: str) -> Optional[int]:
    """Extract available study time in minutes."""
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


def _extract_date_shift(message: str) -> Optional[str]:
    """Extract relative date target: 'tomorrow', 'next_week', 'today'."""
    msg = message.lower()
    if "tomorrow" in msg:
        return "tomorrow"
    if "next week" in msg or "next 7 days" in msg:
        return "next_week"
    if "today" in msg or "tonight" in msg:
        return "today"
    return None


def _check_is_followup(message: str) -> bool:
    """Detect follow-up queries that build on preceding context."""
    msg = message.lower().strip()
    followup_patterns = [
        r"^what\s+about\b",
        r"^how\s+about\b",
        r"^what\s+if\b",
        r"^and\s+for\b",
        r"\binstead\b",
        r"\balso\b",
        r"\bcan\s+we\s+make\s+it\b",
        r"\bmake\s+it\b",
        r"\btomorrow\b",
    ]
    return any(re.search(p, msg) for p in followup_patterns)


def classify(message: str) -> IntentResult:
    """
    Classify user message into intents and extract structured entities.
    Determines primary intent, compound intents, relative date shifts, and follow-up flags.
    Never returns needs_clarification=True.
    """
    if not message or not message.strip():
        return IntentResult(
            intents=[Intent.UNKNOWN],
            primary_intent=Intent.UNKNOWN,
            confidence=0.0,
            entities={},
            needs_clarification=False,
        )

    msg_lower = message.strip().lower()
    matched_intents: List[Intent] = []

    for intent, compiled_patterns in _COMPILED_RULES:
        for pattern in compiled_patterns:
            if pattern.search(msg_lower):
                if intent not in matched_intents:
                    matched_intents.append(intent)
                break

    entities: Dict[str, Any] = {}
    
    # Extract time minutes
    minutes = _extract_time_minutes(message)
    if minutes:
        entities["available_minutes"] = minutes

    # Extract date shift
    date_shift = _extract_date_shift(message)
    if date_shift:
        entities["date_shift"] = date_shift

    # Check follow-up
    is_followup = _check_is_followup(message)
    if is_followup:
        entities["is_followup"] = True

    if not matched_intents:
        # If it's a follow-up or contains time/date shift, route to STUDY_PLANNING / SCHEDULE_CONSTRAINT
        if minutes or date_shift or is_followup:
            matched_intents = [Intent.SCHEDULE_CONSTRAINT if minutes else Intent.STUDY_PLANNING]
            confidence = 0.75
        else:
            confidence = 0.5
            matched_intents = [Intent.UNKNOWN]
    elif len(matched_intents) == 1:
        confidence = 0.9
    else:
        confidence = 0.75

    primary = matched_intents[0]

    logger.info(
        "IntentClassifier: intents=%s primary=%s confidence=%.2f entities=%s",
        [i.value for i in matched_intents], primary.value, confidence, entities,
    )

    return IntentResult(
        intents=matched_intents,
        primary_intent=primary,
        confidence=confidence,
        entities=entities,
        needs_clarification=False,
    )
