from __future__ import annotations
import re

CANNED_PATTERNS = [
    r"thank\s+you\s+for\s+contacting",
    r"thanks\s+for\s+(?:contacting|reaching\s+out)",
    r"our\s+team\s+will\s+respond\s+shortly",
    r"will\s+get\s+back\s+to\s+you\s+(?:shortly|soon)",
    r"automated\s+assistant",
    r"auto-reply",
    r"canned\s+message",
    r"currently\s+unavailable",
    r"we\s+are\s+closed\s+right\s+now",
    r"shukriya.*team\s+tak\s+pahuncha",
    r"automated\s+reply",
    r"this\s+is\s+an\s+automated",
    r"hamari\s+team\s+aapko\s+sampark\s+karegi",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CANNED_PATTERNS]

class AutoReplyDetector:
    """Detects WhatsApp Business automated canned replies and repetition loops."""

    @staticmethod
    def is_canned(text: str) -> bool:
        norm = text.strip().lower()
        for pattern in COMPILED_PATTERNS:
            if pattern.search(norm):
                return True
        return False

    @staticmethod
    def is_repeated(text: str, history: list[str]) -> bool:
        if not history:
            return False
        norm = text.strip().lower()
        # If the last message from merchant is identical
        for prev in reversed(history):
            if prev.strip().lower() == norm:
                return True
        return False

    @classmethod
    def evaluate(cls, message: str, previous_merchant_messages: list[str]) -> tuple[bool, str]:
        """
        Evaluate if a message is an auto-reply.
        Returns (is_auto_reply, reason).
        """
        if cls.is_canned(message):
            return True, "canned_auto_reply_pattern"
        if cls.is_repeated(message, previous_merchant_messages):
            return True, "verbatim_repeated_message"
        return False, "human_reply"

auto_reply_detector = AutoReplyDetector()
