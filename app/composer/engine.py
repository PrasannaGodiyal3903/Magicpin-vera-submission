from __future__ import annotations
from typing import Optional, Union, Any

from app.models.domain import CategoryContext, MerchantContext, TriggerContext, CustomerContext
from app.models.schemas import ComposedMessage
from app.composer.deterministic import deterministic_composer
from app.composer.fallback import fallback_composer
from app.composer.llm_adapter import llm_adapter
from app.validator.safety import validator

class EngagementComposer:
    """Master composition engine coordinating deterministic rules, fallback, and LLM adapters."""

    def compose(
        self,
        category: Union[CategoryContext, dict[str, Any]],
        merchant: Union[MerchantContext, dict[str, Any]],
        trigger: Union[TriggerContext, dict[str, Any]],
        customer: Optional[Union[CustomerContext, dict[str, Any]]] = None
    ) -> ComposedMessage:
        # Normalize inputs
        cat_ctx = category if isinstance(category, CategoryContext) else CategoryContext.from_dict(category)
        m_ctx = merchant if isinstance(merchant, MerchantContext) else MerchantContext.from_dict(merchant)
        trg_ctx = trigger if isinstance(trigger, TriggerContext) else TriggerContext.from_dict(trigger)
        cust_ctx = None
        if customer:
            cust_ctx = customer if isinstance(customer, CustomerContext) else CustomerContext.from_dict(customer)

        # 1. Try LLM if enabled
        composed = llm_adapter.compose(cat_ctx, m_ctx, trg_ctx, cust_ctx)

        # 2. Try deterministic composer
        if not composed:
            if deterministic_composer.can_handle(trg_ctx.kind):
                composed = deterministic_composer.compose(cat_ctx, m_ctx, trg_ctx, cust_ctx)
            else:
                composed = fallback_composer.compose(cat_ctx, m_ctx, trg_ctx, cust_ctx)

        # 3. Final safety and quality validation
        taboos = cat_ctx.voice.get("vocab_taboo", [])
        composed.body = validator.clean_message(composed.body, taboos)

        # Ensure correct send_as attribution
        expected_send_as = "merchant_on_behalf" if trg_ctx.scope == "customer" else "vera"
        if composed.send_as != expected_send_as:
            composed.send_as = expected_send_as

        return composed

engagement_composer = EngagementComposer()
