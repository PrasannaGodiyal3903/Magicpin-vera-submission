"""
magicpin AI Challenge — Main Bot Module
=======================================
Implements:
1. `compose(category, merchant, trigger, customer)` standalone entrypoint as specified in challenge-brief.md §7.1
2. `app` FastAPI application instance for running the HTTP server
"""

from typing import Optional, Any
from app.composer.engine import engagement_composer
from app.main import app

def compose(
    category: dict[str, Any],
    merchant: dict[str, Any],
    trigger: dict[str, Any],
    customer: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Inputs are the dicts loaded from the dataset JSON.
    Return a dict with keys: body, cta, send_as, suppression_key, rationale.
    Must be deterministic given the same inputs.
    Must complete in < 30s per call.
    """
    msg = engagement_composer.compose(
        category=category,
        merchant=merchant,
        trigger=trigger,
        customer=customer
    )
    return {
        "body": msg.body,
        "cta": msg.cta,
        "send_as": msg.send_as,
        "suppression_key": msg.suppression_key,
        "rationale": msg.rationale
    }

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run("bot:app", host=settings.HOST, port=settings.PORT, reload=False)
