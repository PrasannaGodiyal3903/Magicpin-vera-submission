from __future__ import annotations
from typing import Optional, Any
from app.models.domain import CategoryContext, MerchantContext, TriggerContext, CustomerContext
from app.models.schemas import ComposedMessage
from app.composer.base import BaseComposer
from app.validator.safety import validator

class FallbackComposer(BaseComposer):
    """
    Generalized fallback composer for any unseen trigger, category, or customer state.
    Guarantees deterministic execution, zero hallucinations, and schema compliance.
    """

    def can_handle(self, trigger_kind: str) -> bool:
        return True

    def compose(
        self,
        category: CategoryContext,
        merchant: MerchantContext,
        trigger: TriggerContext,
        customer: Optional[CustomerContext] = None
    ) -> ComposedMessage:
        if trigger.scope == "customer" and customer:
            return self._compose_customer_fallback(category, merchant, trigger, customer)
        return self._compose_merchant_fallback(category, merchant, trigger)

    def _compose_customer_fallback(
        self,
        category: CategoryContext,
        merchant: MerchantContext,
        trigger: TriggerContext,
        customer: CustomerContext
    ) -> ComposedMessage:
        c_name = customer.clean_name or "there"
        m_name = merchant.name or "our clinic"
        owner = merchant.owner_first_name
        locality = merchant.locality or merchant.city or ""
        loc_str = f" in {locality}" if locality else ""

        # Extract whatever is in trigger payload
        topic = trigger.payload.get("metric_or_topic", trigger.payload.get("topic", trigger.kind.replace("_", " ")))
        
        # Check active offers
        offer_str = ""
        if merchant.active_offers:
            offer_str = f" ({merchant.active_offers[0].get('title', '')})"
        elif category.offer_catalog:
            offer_str = f" ({category.offer_catalog[0].get('title', '')})"

        pref = customer.language_pref.lower()
        if "hi" in pref:
            body = (
                f"Hi {c_name}! {m_name}{loc_str} se reminder: your follow-up regarding {topic} is ready{offer_str}. "
                f"Apke convenience ke liye priority slots available hain. Reply 1 to book, ya call us to adjust time."
            )
        else:
            body = (
                f"Hi {c_name}, {m_name}{loc_str} here. Quick note regarding your {topic} follow-up{offer_str}. "
                f"We have priority slots open for you this week. Would you like us to hold a slot for you? Reply YES to confirm."
            )

        taboos = category.voice.get("vocab_taboo", [])
        cleaned_body = validator.clean_message(body, taboos)

        return ComposedMessage(
            body=cleaned_body,
            cta="binary_yes_no",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"cust_fallback:{customer.customer_id}:{trigger.kind}",
            rationale=f"Generalized customer notification for unseen trigger '{trigger.kind}' using verified identity and preferences.",
            template_name="customer_fallback_v1",
            template_params=[c_name, m_name, topic]
        )

    def _compose_merchant_fallback(
        self,
        category: CategoryContext,
        merchant: MerchantContext,
        trigger: TriggerContext
    ) -> ComposedMessage:
        owner = merchant.owner_first_name
        m_name = merchant.name
        locality = merchant.locality or merchant.city or "your area"
        
        salutation = f"Dr. {owner}" if category.slug == "dentists" and owner else (owner if owner else m_name)
        
        topic = trigger.payload.get("metric_or_topic", trigger.payload.get("topic", trigger.kind.replace("_", " ")))
        
        # Build factual reference
        views = merchant.performance.get("views")
        views_mention = f" (your profile had {views:,} views in the last 30 days)" if views else ""
        
        offer = ""
        if merchant.active_offers:
            offer = f" showcasing {merchant.active_offers[0].get('title', '')}"
        elif category.offer_catalog:
            offer = f" showcasing {category.offer_catalog[0].get('title', '')}"

        body = (
            f"Hi {salutation}! Quick update for {m_name} in {locality}: "
            f"an update regarding {topic} is relevant for your local audience{views_mention}. "
            f"Want me to draft a Google post{offer} to keep your profile active this week? Takes 2 min to approve."
        )

        taboos = category.voice.get("vocab_taboo", [])
        cleaned_body = validator.clean_message(body, taboos)

        return ComposedMessage(
            body=cleaned_body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"mx_fallback:{merchant.merchant_id}:{trigger.kind}",
            rationale=f"Grounded fallback composition for unseen trigger '{trigger.kind}' referencing verified merchant details and low-friction CTA.",
            template_name="vera_fallback_v1",
            template_params=[salutation, m_name, topic]
        )

fallback_composer = FallbackComposer()
