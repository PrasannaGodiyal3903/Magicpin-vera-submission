from __future__ import annotations
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import (
    HealthResponse, ContextCounts, MetadataResponse,
    ContextPushRequest, ContextPushSuccess, ContextPushConflict, ContextPushError,
    TickRequest, TickResponse, TickAction,
    ReplyRequest, ReplyResponse
)
from app.storage.context_store import context_store
from app.composer.engine import engagement_composer
from app.multi_turn.reply_handler import reply_handler

START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    if os.getenv("PRELOAD_DATASET", "false").lower() in ("true", "1"):
        if settings.EXPANDED_DIR.exists():
            context_store.preload_from_dir(settings.EXPANDED_DIR)
    yield

app = FastAPI(
    title="magicpin Vera Assistant",
    description="Merchant AI Assistant for the magicpin AI Challenge",
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/v1/healthz", response_model=HealthResponse)
async def healthz():
    uptime = int(time.time() - START_TIME)
    counts = context_store.get_counts()
    return HealthResponse(
        status="ok",
        uptime_seconds=uptime,
        contexts_loaded=ContextCounts(**counts)
    )

@app.get("/v1/metadata", response_model=MetadataResponse)
async def metadata():
    return MetadataResponse(
        team_name=settings.TEAM_NAME,
        team_members=settings.TEAM_MEMBERS,
        model=settings.MODEL,
        approach=settings.APPROACH,
        contact_email=settings.CONTACT_EMAIL,
        version=settings.VERSION,
        submitted_at=settings.SUBMITTED_AT
    )

@app.post("/v1/context", status_code=200)
async def push_context(body: ContextPushRequest):
    valid_scopes = {"category", "merchant", "customer", "trigger"}
    if body.scope not in valid_scopes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": "invalid_scope", "details": f"Scope must be one of {valid_scopes}"}
        )

    accepted, result, cur_ver = context_store.push_context(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload
    )

    if not accepted:
        if result == "stale_version":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"accepted": False, "reason": "stale_version", "current_version": cur_ver}
            )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": "invalid_request", "details": result}
        )

    return ContextPushSuccess(
        accepted=True,
        ack_id=result,
        stored_at=datetime.now(timezone.utc).isoformat()
    )

@app.post("/v1/tick", response_model=TickResponse)
async def tick(body: TickRequest):
    actions: list[TickAction] = []

    for trg_id in body.available_triggers:
        trigger = context_store.get_trigger(trg_id)
        if not trigger:
            continue

        # Deduplication check via suppression key
        if trigger.suppression_key and context_store.is_suppressed(trigger.suppression_key):
            continue

        merchant_id = trigger.merchant_id
        if not merchant_id:
            continue

        merchant = context_store.get_merchant(merchant_id)
        if not merchant:
            continue

        category = context_store.get_category(merchant.category_slug)
        if not category:
            continue

        customer = None
        if trigger.customer_id:
            customer = context_store.get_customer(trigger.customer_id)

        # Compose message using master 4-context engine
        msg = engagement_composer.compose(category, merchant, trigger, customer)

        conv_id = f"conv_{merchant_id}_{trigger.id}"
        action = TickAction(
            conversation_id=conv_id,
            merchant_id=merchant_id,
            customer_id=trigger.customer_id,
            send_as=msg.send_as,
            trigger_id=trigger.id,
            template_name=msg.template_name or "vera_generic_v1",
            template_params=msg.template_params or [merchant.name, "update"],
            body=msg.body,
            cta=msg.cta,
            suppression_key=msg.suppression_key,
            rationale=msg.rationale
        )

        # Record suppression and conversation state
        if msg.suppression_key:
            context_store.mark_suppressed(msg.suppression_key)

        conv = context_store.get_or_create_conversation(conv_id, merchant_id, trigger.customer_id)
        conv.record_bot_response("send", msg.body)

        actions.append(action)

    return TickResponse(actions=actions)

@app.post("/v1/reply", response_model=ReplyResponse)
async def reply(body: ReplyRequest):
    return reply_handler.handle(body)

@app.post("/v1/teardown")
async def teardown():
    """Optional teardown hook as requested by challenge spec to wipe state."""
    context_store.reset()
    return {"status": "ok", "message": "State reset successfully"}
