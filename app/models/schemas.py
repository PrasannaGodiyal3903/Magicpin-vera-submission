from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

# --- Health & Metadata ---
class ContextCounts(BaseModel):
    category: int = 0
    merchant: int = 0
    customer: int = 0
    trigger: int = 0

class HealthResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: int
    contexts_loaded: ContextCounts

class MetadataResponse(BaseModel):
    team_name: str
    team_members: list[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str

# --- Context Ingestion ---
ScopeType = Literal["category", "merchant", "customer", "trigger"]

class ContextPushRequest(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str

class ContextPushSuccess(BaseModel):
    accepted: bool = True
    ack_id: str
    stored_at: str

class ContextPushConflict(BaseModel):
    accepted: bool = False
    reason: str = "stale_version"
    current_version: int

class ContextPushError(BaseModel):
    accepted: bool = False
    reason: str
    details: str

# --- Tick ---
class TickRequest(BaseModel):
    now: str
    available_triggers: list[str] = Field(default_factory=list)

class TickAction(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"]
    trigger_id: str
    template_name: str
    template_params: list[str]
    body: str
    cta: str
    suppression_key: str
    rationale: str

class TickResponse(BaseModel):
    actions: list[TickAction] = Field(default_factory=list)

# --- Reply ---
class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str = "merchant"
    message: str
    received_at: str
    turn_number: int

class ReplyResponse(BaseModel):
    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str

# --- Top-level compose contract ---
class ComposedMessage(BaseModel):
    body: str
    cta: str
    send_as: Literal["vera", "merchant_on_behalf"]
    suppression_key: str
    rationale: str
    template_name: Optional[str] = None
    template_params: Optional[list[str]] = None
