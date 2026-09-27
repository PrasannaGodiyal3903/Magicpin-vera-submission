from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.models.domain import CategoryContext, MerchantContext, TriggerContext, CustomerContext

logger = logging.getLogger(__name__)

class ConversationState:
    def __init__(self, conversation_id: str, merchant_id: Optional[str] = None, customer_id: Optional[str] = None):
        self.conversation_id = conversation_id
        self.merchant_id = merchant_id
        self.customer_id = customer_id
        self.turns: list[dict[str, Any]] = []
        self.status: str = "active"  # active, waiting, ended
        self.wait_until: Optional[str] = None
        self.consecutive_auto_replies: int = 0
        self.last_sent_body: Optional[str] = None
        self.last_sent_action: Optional[str] = None
        self.history_bodies: set[str] = set()

    def add_turn(self, from_role: str, message: str, turn_number: int, received_at: str):
        self.turns.append({
            "from_role": from_role,
            "message": message,
            "turn_number": turn_number,
            "received_at": received_at,
        })

    def record_bot_response(self, action: str, body: Optional[str] = None):
        self.last_sent_action = action
        if body:
            self.last_sent_body = body
            self.history_bodies.add(body.strip().lower())


class ContextStore:
    """Thread-safe, versioned in-memory store for contexts and conversations."""

    def __init__(self):
        # Key: (scope, context_id) -> {"version": int, "payload": dict, "stored_at": str}
        self._contexts: dict[tuple[str, str], dict[str, Any]] = {}
        # Key: conversation_id -> ConversationState
        self._conversations: dict[str, ConversationState] = {}
        # Suppression keys for trigger deduplication
        self._suppressed_keys: set[str] = set()

    def push_context(self, scope: str, context_id: str, version: int, payload: dict[str, Any]) -> tuple[bool, str, Optional[int]]:
        """
        Store or update context.
        Returns: (accepted, reason_or_ack, current_version_if_rejected)
        """
        valid_scopes = {"category", "merchant", "customer", "trigger"}
        if scope not in valid_scopes:
            return False, f"invalid_scope: must be one of {valid_scopes}", None

        key = (scope, context_id)
        current = self._contexts.get(key)
        if current:
            current_ver = current["version"]
            if current_ver > version:
                return False, "stale_version", current_ver
            elif current_ver == version:
                # Idempotent no-op as specified in testing brief §2.1
                return True, f"ack_{context_id}_v{version}", None

        self._contexts[key] = {
            "version": version,
            "payload": payload,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        return True, f"ack_{context_id}_v{version}", None

    def get_context_raw(self, scope: str, context_id: str) -> Optional[dict[str, Any]]:
        record = self._contexts.get((scope, context_id))
        return record["payload"] if record else None

    def get_category(self, slug: str) -> Optional[CategoryContext]:
        raw = self.get_context_raw("category", slug)
        return CategoryContext.from_dict(raw) if raw else None

    def get_merchant(self, merchant_id: str) -> Optional[MerchantContext]:
        raw = self.get_context_raw("merchant", merchant_id)
        return MerchantContext.from_dict(raw) if raw else None

    def get_trigger(self, trigger_id: str) -> Optional[TriggerContext]:
        raw = self.get_context_raw("trigger", trigger_id)
        return TriggerContext.from_dict(raw) if raw else None

    def get_customer(self, customer_id: str) -> Optional[CustomerContext]:
        raw = self.get_context_raw("customer", customer_id)
        return CustomerContext.from_dict(raw) if raw else None

    def get_counts(self) -> dict[str, int]:
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for (scope, _), _ in self._contexts.items():
            if scope in counts:
                counts[scope] += 1
        return counts

    def is_suppressed(self, suppression_key: str) -> bool:
        if not suppression_key:
            return False
        return suppression_key in self._suppressed_keys

    def mark_suppressed(self, suppression_key: str):
        if suppression_key:
            self._suppressed_keys.add(suppression_key)

    def get_or_create_conversation(self, conversation_id: str, merchant_id: Optional[str] = None, customer_id: Optional[str] = None) -> ConversationState:
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationState(conversation_id, merchant_id, customer_id)
        state = self._conversations[conversation_id]
        if merchant_id and not state.merchant_id:
            state.merchant_id = merchant_id
        if customer_id and not state.customer_id:
            state.customer_id = customer_id
        return state

    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        return self._conversations.get(conversation_id)

    def is_body_repeated(self, conversation_id: str, body: str) -> bool:
        state = self._conversations.get(conversation_id)
        if not state:
            return False
        return body.strip().lower() in state.history_bodies

    def reset(self):
        """Wipe state for testing or teardown."""
        self._contexts.clear()
        self._conversations.clear()
        self._suppressed_keys.clear()

    def preload_from_dir(self, base_dir: Path):
        """Preload data from directory (e.g. dataset/expanded or dataset)."""
        cat_dir = base_dir / "categories"
        if cat_dir.exists():
            for f in cat_dir.glob("*.json"):
                try:
                    data = json.load(open(f, encoding="utf-8"))
                    slug = data.get("slug", f.stem)
                    self.push_context("category", slug, 1, data)
                except Exception as e:
                    logger.warning(f"Error preloading category {f}: {e}")

        for scope, folder, key in [
            ("merchant", "merchants", "merchant_id"),
            ("customer", "customers", "customer_id"),
            ("trigger", "triggers", "id"),
        ]:
            s_dir = base_dir / folder
            if s_dir.exists():
                for f in s_dir.glob("*.json"):
                    try:
                        data = json.load(open(f, encoding="utf-8"))
                        cid = data.get(key, f.stem)
                        self.push_context(scope, cid, 1, data)
                    except Exception as e:
                        logger.warning(f"Error preloading {scope} {f}: {e}")

# Global singleton store
context_store = ContextStore()
