from __future__ import annotations
import re
from typing import Any, Optional

URL_PATTERN = re.compile(
    r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(?:com|in|org|net|co|io|app)/[^\s]*)',
    re.IGNORECASE
)

class SafetyValidator:
    """Validates and cleans message output against challenge safety and quality rules."""

    @staticmethod
    def strip_urls(text: str) -> str:
        """Meta WhatsApp templates reject raw URLs; strip them to prevent -3 penalty."""
        cleaned = URL_PATTERN.sub('', text)
        # Clean up any leftover double spaces
        cleaned = re.sub(r' +', ' ', cleaned).strip()
        return cleaned

    @staticmethod
    def sanitize_taboos(text: str, taboos: list[str]) -> str:
        """Replace taboo words that violate category clinical/legal guidelines."""
        sanitized = text
        for taboo in taboos:
            if not taboo:
                continue
            # Remove notes in parentheses from taboos, e.g. "doctor approved" or "FDA-approved (...)"
            clean_taboo = re.sub(r'\(.*?\)', '', taboo).strip()
            if not clean_taboo:
                continue
            pattern = re.compile(re.escape(clean_taboo), re.IGNORECASE)
            sanitized = pattern.sub('', sanitized)
        sanitized = re.sub(r' +', ' ', sanitized).strip()
        return sanitized

    @staticmethod
    def validate_action_fields(action: dict[str, Any]) -> tuple[bool, list[str]]:
        """Ensure all required fields for a tick action are populated."""
        required = [
            "conversation_id", "merchant_id", "send_as",
            "trigger_id", "body", "cta", "suppression_key", "rationale"
        ]
        missing = [f for f in required if not action.get(f)]
        return len(missing) == 0, missing

    @staticmethod
    def clean_message(body: str, taboos: Optional[list[str]] = None) -> str:
        """Apply all sanitization rules to the composed message body."""
        body = SafetyValidator.strip_urls(body)
        if taboos:
            body = SafetyValidator.sanitize_taboos(body, taboos)
        return body.strip()

validator = SafetyValidator()
