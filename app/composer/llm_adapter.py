from __future__ import annotations
import json
import logging
import urllib.request
from typing import Optional

from app.config import settings
from app.models.domain import CategoryContext, MerchantContext, TriggerContext, CustomerContext
from app.models.schemas import ComposedMessage
from app.validator.safety import validator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Vera, magicpin's expert AI assistant for local merchants in India.
Your goal is to compose highly contextual, compelling WhatsApp messages to merchants or customers.
RULES:
1. NEVER invent/hallucinate facts, offers, discounts, customer names, dates, or citations not provided in context.
2. WhatsApp 24h template style: keep it concise, natural, professional.
3. Include specific verifiable numbers and citations from context when present.
4. Voice: Match category tone (Dentists: clinical peer, Salons: warm operator, Restaurants: operator, etc.).
5. Single clear CTA at the very end.
6. NO URLs in the body.
7. Return strictly valid JSON with keys: body, cta, send_as, suppression_key, rationale.
"""

class LLMAdapter:
    """Isolated LLM composer with zero-hallucination guardrails and instant fallback."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        self.enabled = settings.USE_LLM and bool(self.api_key)

    def compose(
        self,
        category: CategoryContext,
        merchant: MerchantContext,
        trigger: TriggerContext,
        customer: Optional[CustomerContext] = None
    ) -> Optional[ComposedMessage]:
        if not self.enabled:
            return None

        prompt = f"""Compose a WhatsApp message for this context:
CATEGORY: {category.slug} (Tone: {category.voice.get('tone', '')}, Taboos: {category.voice.get('vocab_taboo', [])})
MERCHANT: {merchant.name}, Locality: {merchant.locality}, Owner: {merchant.owner_first_name}, Active Offers: {[o.get('title') for o in merchant.active_offers]}
TRIGGER: Kind: {trigger.kind}, Scope: {trigger.scope}, Payload: {json.dumps(trigger.payload)}, SuppressionKey: {trigger.suppression_key}
CUSTOMER: {json.dumps(customer.identity) if customer else 'None (merchant-facing)'}

Return JSON with format:
{{
  "body": "...",
  "cta": "...",
  "send_as": "{ 'merchant_on_behalf' if trigger.scope == 'customer' else 'vera' }",
  "suppression_key": "{ trigger.suppression_key }",
  "rationale": "..."
}}"""

        try:
            req_data = json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "max_tokens": 500
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                body = validator.clean_message(parsed.get("body", ""), category.voice.get("vocab_taboo", []))
                return ComposedMessage(
                    body=body,
                    cta=parsed.get("cta", "binary_yes_no"),
                    send_as=parsed.get("send_as", "merchant_on_behalf" if trigger.scope == "customer" else "vera"),
                    suppression_key=parsed.get("suppression_key", trigger.suppression_key),
                    rationale=parsed.get("rationale", "LLM-assisted composition adhering to 4-context facts.")
                )
        except Exception as e:
            logger.warning(f"LLM composition failed/skipped ({e}), falling back to deterministic engine.")
            return None

llm_adapter = LLMAdapter()
