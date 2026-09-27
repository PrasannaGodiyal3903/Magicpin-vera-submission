from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Literal

@dataclass
class CategoryContext:
    slug: str
    display_name: str = ""
    voice: dict[str, Any] = field(default_factory=dict)
    offer_catalog: list[dict[str, Any]] = field(default_factory=list)
    peer_stats: dict[str, Any] = field(default_factory=dict)
    digest: list[dict[str, Any]] = field(default_factory=list)
    patient_content_library: list[dict[str, Any]] = field(default_factory=list)
    seasonal_beats: list[dict[str, Any]] = field(default_factory=list)
    trend_signals: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryContext:
        return cls(
            slug=data.get("slug", "unknown"),
            display_name=data.get("display_name", data.get("slug", "Local Business")),
            voice=data.get("voice", {}),
            offer_catalog=data.get("offer_catalog", []),
            peer_stats=data.get("peer_stats", {}),
            digest=data.get("digest", []),
            patient_content_library=data.get("patient_content_library", []),
            seasonal_beats=data.get("seasonal_beats", []),
            trend_signals=data.get("trend_signals", []),
            raw=data,
        )

@dataclass
class MerchantContext:
    merchant_id: str
    category_slug: str = ""
    identity: dict[str, Any] = field(default_factory=dict)
    subscription: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, Any] = field(default_factory=dict)
    offers: list[dict[str, Any]] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    customer_aggregate: dict[str, Any] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    review_themes: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.identity.get("name", "Your Business")

    @property
    def owner_first_name(self) -> str:
        return self.identity.get("owner_first_name", "")

    @property
    def locality(self) -> str:
        return self.identity.get("locality", "")

    @property
    def city(self) -> str:
        return self.identity.get("city", "")

    @property
    def languages(self) -> list[str]:
        return self.identity.get("languages", ["en"])

    @property
    def is_verified(self) -> bool:
        return bool(self.identity.get("verified", False))

    @property
    def active_offers(self) -> list[dict[str, Any]]:
        return [o for o in self.offers if o.get("status") == "active"]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MerchantContext:
        return cls(
            merchant_id=data.get("merchant_id", "unknown"),
            category_slug=data.get("category_slug", ""),
            identity=data.get("identity", {}),
            subscription=data.get("subscription", {}),
            performance=data.get("performance", {}),
            offers=data.get("offers", []),
            conversation_history=data.get("conversation_history", []),
            customer_aggregate=data.get("customer_aggregate", {}),
            signals=data.get("signals", []),
            review_themes=data.get("review_themes", []),
            raw=data,
        )

@dataclass
class TriggerContext:
    id: str
    scope: Literal["merchant", "customer"] = "merchant"
    kind: str = "unknown"
    source: Literal["external", "internal"] = "internal"
    merchant_id: str = ""
    customer_id: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)
    urgency: int = 1
    suppression_key: str = ""
    expires_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TriggerContext:
        return cls(
            id=data.get("id", "trg_unknown"),
            scope=data.get("scope", "merchant"),
            kind=data.get("kind", "unknown"),
            source=data.get("source", "internal"),
            merchant_id=data.get("merchant_id", ""),
            customer_id=data.get("customer_id"),
            payload=data.get("payload", {}),
            urgency=data.get("urgency", 1),
            suppression_key=data.get("suppression_key", f"trg:{data.get('id', 'unknown')}"),
            expires_at=data.get("expires_at", ""),
            raw=data,
        )

@dataclass
class CustomerContext:
    customer_id: str
    merchant_id: str = ""
    identity: dict[str, Any] = field(default_factory=dict)
    relationship: dict[str, Any] = field(default_factory=dict)
    state: str = "active"
    preferences: dict[str, Any] = field(default_factory=dict)
    consent: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        raw_name = self.identity.get("name", "Customer")
        # Strip notes like "Aanya (parent: Sneha)" or "Mr. Sharma (son's phone)"
        return raw_name

    @property
    def clean_name(self) -> str:
        name = self.name
        if "(" in name:
            name = name.split("(")[0].strip()
        return name

    @property
    def language_pref(self) -> str:
        return self.identity.get("language_pref", "en")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomerContext:
        return cls(
            customer_id=data.get("customer_id", "unknown"),
            merchant_id=data.get("merchant_id", ""),
            identity=data.get("identity", {}),
            relationship=data.get("relationship", {}),
            state=data.get("state", "active"),
            preferences=data.get("preferences", {}),
            consent=data.get("consent", {}),
            raw=data,
        )
