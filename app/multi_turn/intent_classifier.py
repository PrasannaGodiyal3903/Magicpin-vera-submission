from __future__ import annotations
import re
from typing import Literal

IntentType = Literal[
    "opt_out_hostile",
    "commitment_action",
    "wait_request",
    "off_topic_curveball",
    "question_inquiry",
    "affirmative",
    "negative_polite",
    "slot_choice",
    "general"
]

OPT_OUT_PATTERNS = [
    r"stop\s+(?:messaging|sending|bothering)",
    r"not\s+interested",
    r"useless\s+spam",
    r"why\s+are\s+you\s+bothering",
    r"don'?t\s+message",
    r"leave\s+me\s+alone",
    r"unsubscribe",
    r"\bstop\b",
    r"\bcancel\b",
    r"mat\s+(?:bhejo|karo)",
]

COMMITMENT_PATTERNS = [
    r"let'?s\s+do\s+it",
    r"what'?s\s+next",
    r"send\s+(?:me\s+)?(?:the\s+)?(?:abstract|draft|post|details|link|workflow)",
    r"go\s+ahead",
    r"proceed",
    r"confirm",
    r"yes\s+(?:please|send|draft|schedule|do|sure)",
    r"i\s+want\s+to\s+join",
    r"judrna\s+hai",
    r"karna\s+hai",
    r"shuru\s+karo",
    r"banao",
]

WAIT_PATTERNS = [
    r"busy\s+(?:right\s+now|now|today)",
    r"check\s+back\s+later",
    r"call\s+(?:me\s+)?(?:later|after|tomorrow)",
    r"after\s+\d+\s+(?:hours?|mins?|days?)",
    r"thodi\s+der\s+baad",
    r"give\s+me\s+some\s+time",
    r"later",
    r"baad\s+mein",
]

OFF_TOPIC_PATTERNS = [
    r"\bgst\b",
    r"income\s+tax",
    r"file\s+my\s+(?:gst|tax|itr)",
    r"ca\s+services",
    r"personal\s+loan",
    r"weather\s+forecast",
    r"cricket\s+score",
]

class IntentClassifier:
    """Classifies incoming merchant and customer turn messages."""

    @classmethod
    def classify(cls, text: str) -> tuple[IntentType, float]:
        norm = text.strip().lower()

        # Check opt-out / hostile first
        for p in OPT_OUT_PATTERNS:
            if re.search(p, norm):
                return "opt_out_hostile", 0.95

        # Check off-topic curveball
        for p in OFF_TOPIC_PATTERNS:
            if re.search(p, norm):
                return "off_topic_curveball", 0.90

        # Check wait request
        for p in WAIT_PATTERNS:
            if re.search(p, norm):
                return "wait_request", 0.90

        # Check commitment / action
        for p in COMMITMENT_PATTERNS:
            if re.search(p, norm):
                return "commitment_action", 0.95

        # Check slot choice (e.g. "1", "2", "Wed", "Thu")
        if norm in ("1", "2", "wed", "thu", "wednesday", "thursday", "sat", "saturday"):
            return "slot_choice", 0.90

        # Check affirmative
        if norm in ("yes", "ok", "okay", "sure", "yep", "yeah", "haan", "theek hai", "chalega"):
            return "commitment_action", 0.85

        # Check negative polite
        if norm in ("no", "not now", "nah", "nahi", "abhi nahi"):
            return "negative_polite", 0.85

        # Check question
        if "?" in text or any(norm.startswith(w) for w in ("how", "what", "where", "why", "when", "kya", "kaise")):
            return "question_inquiry", 0.80

        return "general", 0.50

intent_classifier = IntentClassifier()
