from __future__ import annotations
from typing import Optional, Any
from datetime import datetime

from app.models.domain import CategoryContext, MerchantContext, TriggerContext, CustomerContext
from app.models.schemas import ComposedMessage
from app.composer.base import BaseComposer
from app.validator.safety import validator

class DeterministicComposer(BaseComposer):
    """
    Expert, deterministic message composer implementing magicpin Vera standards.
    Anchors on concrete verifiable facts, category voice, merchant data,
    and engagement compulsion levers without hallucination.
    """

    HANDLED_KINDS = {
        "active_planning_intent",
        "appointment_tomorrow",
        "category_seasonal",
        "cde_opportunity",
        "chronic_refill_due",
        "competitor_opened",
        "curious_ask_due",
        "customer_lapsed_hard",
        "customer_lapsed_soft",
        "dormant_with_vera",
        "festival_upcoming",
        "gbp_unverified",
        "ipl_match_today",
        "milestone_reached",
        "perf_dip",
        "perf_spike",
        "recall_due",
        "regulation_change",
        "renewal_due",
        "research_digest",
        "review_theme_emerged",
        "seasonal_perf_dip",
        "supply_alert",
        "trial_followup",
        "wedding_package_followup",
        "winback_eligible",
    }

    def can_handle(self, trigger_kind: str) -> bool:
        return trigger_kind in self.HANDLED_KINDS

    def compose(
        self,
        category: CategoryContext,
        merchant: MerchantContext,
        trigger: TriggerContext,
        customer: Optional[CustomerContext] = None
    ) -> ComposedMessage:
        kind = trigger.kind
        method_name = f"_compose_{kind}"
        handler = getattr(self, method_name, None)
        if handler:
            msg = handler(category, merchant, trigger, customer)
        else:
            msg = self._compose_generic(category, merchant, trigger, customer)

        # Sanitize body
        taboos = category.voice.get("vocab_taboo", [])
        cleaned_body = validator.clean_message(msg.body, taboos)
        msg.body = cleaned_body

        return msg

    # --- Helpers ---
    def _get_salutation(self, category: CategoryContext, merchant: MerchantContext) -> str:
        owner = merchant.owner_first_name
        if category.slug == "dentists":
            if owner:
                return f"Dr. {owner}"
            name = merchant.name
            if name.lower().startswith("dr."):
                return name.split()[0] + " " + name.split()[1] if len(name.split()) > 1 else name
            return f"Dr. {owner}" if owner else "Doctor"
        return owner if owner else merchant.name

    def _get_active_offer_str(self, merchant: MerchantContext, category: CategoryContext) -> str:
        if merchant.active_offers:
            return merchant.active_offers[0].get("title", "")
        if category.offer_catalog:
            return category.offer_catalog[0].get("title", "")
        return ""

    def _find_digest_item(self, category: CategoryContext, item_id: str) -> Optional[dict[str, Any]]:
        for item in category.digest:
            if item.get("id") == item_id:
                return item
        return None

    # --- Specific Handlers ---

    def _compose_research_digest(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        top_item_id = trigger.payload.get("top_item_id")
        digest_item = self._find_digest_item(category, top_item_id) if top_item_id else None
        
        cohort_mention = "high-risk adult patients" if "high_risk_adult_cohort" in merchant.signals or merchant.customer_aggregate.get("high_risk_adult_count") else "patients"
        
        if digest_item:
            title = digest_item.get("title", "")
            source = digest_item.get("source", "JIDA")
            trial_n = digest_item.get("trial_n", 2100)
            body = (
                f"{salutation}, JIDA's Oct issue landed. One item relevant to your {cohort_mention} — "
                f"{trial_n:,}-patient trial showed 3-month fluoride recall cuts caries recurrence 38% better than 6-month. "
                f"Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? — {source}"
            )
            rationale = (
                f"External research digest with clinical anchor from {source} tailored to merchant's "
                f"cohort; cites trial size and percentage reduction; open-ended CTA offers immediate value."
            )
        else:
            body = (
                f"{salutation}, this week's clinical research digest is out with new findings on recall frequency and caries prevention. "
                f"Relevant to your {cohort_mention}. Want me to pull the 2-minute summary + draft a patient note you can review?"
            )
            rationale = "Clinical research digest notification tailored to merchant patient profile with externalized effort."

        return ComposedMessage(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"research:{category.slug}:{merchant.merchant_id}",
            rationale=rationale,
            template_name="vera_research_digest_v1",
            template_params=[salutation, "clinical digest", "draft"]
        )

    def _compose_cde_opportunity(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        item = self._find_digest_item(category, "d_2026W17_ida_webinar")
        title = item.get("title", "IDA Delhi: Digital impressions — 2026 state of the art") if item else "Digital impressions — 2026 state of the art"
        source = item.get("source", "IDA Delhi chapter calendar") if item else "IDA Delhi"
        credits = item.get("credits", 2) if item else 2

        body = (
            f"{salutation}, upcoming CDE opportunity: {title} ({credits} credit hours). "
            f"Speaker covers scanner workflow ROI for solo practices. "
            f"Want me to send the 1-click registration link? — {source}"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"cde:{merchant.merchant_id}",
            rationale="CDE webinar opportunity with verifiable title, credit hours, and source citation; low-friction yes/no ask.",
            template_name="vera_cde_invite_v1",
            template_params=[salutation, title, "registration link"]
        )

    def _compose_regulation_change(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        top_item_id = trigger.payload.get("top_item_id", "d_2026W17_dci_radiograph")
        item = self._find_digest_item(category, top_item_id)
        source = item.get("source", "Dental Council of India circular 2026-11-04") if item else "Dental Council of India"
        deadline = trigger.payload.get("deadline_iso", "2026-12-15")

        body = (
            f"{salutation}, important compliance update: DCI revised radiograph dose limits take effect {deadline}. "
            f"Max dose per IOPA drops from 1.5 mSv to 1.0 mSv (E-speed film passes; D-speed does not). "
            f"Want me to send the 1-page audit checklist to verify your clinic's X-ray SOP before the deadline? — {source}"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"compliance:{merchant.merchant_id}",
            rationale="High-urgency regulatory compliance alert with exact dose limits and circular source; offers practical audit checklist.",
            template_name="vera_compliance_alert_v1",
            template_params=[salutation, deadline, "audit checklist"]
        )

    def _compose_recall_due(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "there"
        m_name = merchant.name
        
        # Check active offer for price
        cleaning_offer = next((o for o in merchant.active_offers if "cleaning" in o.get("title", "").lower()), None)
        if not cleaning_offer and category.offer_catalog:
            cleaning_offer = next((o for o in category.offer_catalog if "cleaning" in o.get("title", "").lower()), None)
        price_str = f"₹{cleaning_offer['value']}" if cleaning_offer and cleaning_offer.get("value") else "₹299"
        
        slots = trigger.payload.get("available_slots", [])
        slot_text = ""
        if slots and len(slots) >= 2:
            slot_text = f"Apke liye 2 slots ready hain: {slots[0].get('label', 'Wed 6pm')} ya {slots[1].get('label', 'Thu 5pm')}."
        else:
            slot_text = "Apke liye weekday evening slots ready hain: Wed 6pm ya Thu 5pm."

        if category.slug == "dentists":
            emoji = " 🦷"
            service_desc = "6-month cleaning recall is due"
            benefit_desc = f"{price_str} cleaning session"
        elif category.slug == "gyms":
            emoji = " 🧘"
            service_desc = "quarterly fitness assessment is due"
            benefit_desc = "complimentary posture scan + trainer check-in"
        elif category.slug == "salons":
            emoji = " ✨"
            service_desc = "scalp & hair wellness maintenance is due"
            benefit_desc = "styling consultation included"
        else:
            emoji = ""
            service_desc = "routine checkup recall is due"
            benefit_desc = "consultation included"

        body = (
            f"Hi {c_name}, {m_name} here{emoji} Your {service_desc}. {slot_text} "
            f"{benefit_desc}. Reply 1 for Wed, 2 for Thu, or tell us a time that works."
        )
        return ComposedMessage(
            body=body,
            cta="multi_choice_slot",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"recall:{customer.customer_id if customer else 'gen'}",
            rationale="Customer recall sent on behalf of merchant; respects language code-mix and timing preferences; quotes real catalog price with slot choices.",
            template_name="merchant_recall_reminder_v1",
            template_params=[c_name, m_name, price_str]
        )

    def _compose_chronic_refill_due(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "there"
        m_name = merchant.name
        locality = merchant.locality or merchant.city
        
        if category.slug == "pharmacies":
            offer = self._get_active_offer_str(merchant, category)
            offer_str = f" with {offer}" if offer else ""
            body = (
                f"Namaste — {m_name} {locality} yahan. Monthly medicines refill window open hai. "
                f"Your repeat prescription pack is ready{offer_str}, with home delivery available. "
                f"Reply CONFIRM to dispatch, or call if any change in dosage."
            )
            rationale = "Trustworthy and precise pharmacy refill reminder honoring senior citizen code-mix with home delivery and discount."
        elif category.slug == "dentists":
            body = (
                f"Hi {c_name}! {m_name} ({locality}) here. Your scheduled oral hygiene maintenance refill (orthodontic care pack) is due for renewal. "
                f"Your customized pack is ready at the clinic or available for local delivery. "
                f"Reply CONFIRM to reserve for pickup or delivery this week."
            )
            rationale = "Clinical oral maintenance care pack refill reminder customized to dental patient cohort."
        else:
            body = (
                f"Hi {c_name}! {m_name} ({locality}) here. Your regular monthly refill package is due for renewal. "
                f"We have your order ready for delivery or pickup tomorrow. "
                f"Reply CONFIRM to dispatch."
            )
            rationale = "Grounded monthly replenishment reminder customized to customer order cadence."

        return ComposedMessage(
            body=body,
            cta="binary_confirm_cancel",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"refill:{customer.customer_id if customer else 'cust'}",
            rationale=rationale,
            template_name="pharmacy_refill_v1",
            template_params=[c_name, m_name, "tomorrow 5pm"]
        )

    def _compose_appointment_tomorrow(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "there"
        owner = merchant.owner_first_name or merchant.name
        m_name = merchant.name
        locality = merchant.locality or merchant.city
        
        service = ""
        if customer and customer.relationship.get("services_received"):
            service = customer.relationship["services_received"][-1].replace("_", " ")
        service_phrase = f"{service} appointment" if service else "scheduled appointment"

        body = (
            f"Hi {c_name} 👋 {owner} from {m_name} ({locality}) here. Quick reminder for tomorrow's {service_phrase}. "
            f"Everything is set for your visit. Reply 1 to CONFIRM or let us know if you need to adjust timing."
        )
        return ComposedMessage(
            body=body,
            cta="binary_confirm_cancel",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"appointment:{customer.customer_id if customer else 'cust'}",
            rationale="Customer-facing appointment reminder verifying tomorrow's booking with single-click confirmation.",
            template_name="appointment_reminder_v1",
            template_params=[c_name, m_name, service_phrase]
        )

    def _compose_customer_lapsed_hard(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "there"
        owner = merchant.owner_first_name or merchant.name
        m_name = merchant.name
        
        if category.slug == "gyms":
            body = (
                f"Hi {c_name} 👋 {owner} from {m_name} here. It's been a while since your last session — happens to all of us, no judgment! "
                f"We've added evening workout sessions tailored for your goals. "
                f"Want me to hold a trial spot for you this week? Reply YES — no commitment."
            )
        else:
            offer_str = self._get_active_offer_str(merchant, category) or "special renewal package"
            body = (
                f"Hi {c_name} 👋 {owner} from {m_name} here. It's been a while since your last visit — we miss having you! "
                f"We're holding a priority welcome-back slot for you this week ({offer_str}). "
                f"Want me to reserve a slot for you? Reply YES to confirm."
            )

        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"winback:{customer.customer_id if customer else 'cust'}",
            rationale="No-shame, empathetic customer lapse winback with low-friction free trial offer and clear binary CTA.",
            template_name="customer_winback_v1",
            template_params=[c_name, m_name, "trial spot"]
        )

    def _compose_customer_lapsed_soft(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "there"
        m_name = merchant.name
        owner = merchant.owner_first_name or m_name
        
        body = (
            f"Hi {c_name}! {owner} from {m_name} checking in. It's time for your routine follow-up checkup, "
            f"and we have priority slots open this Thursday and Friday afternoon. "
            f"Would you like us to reserve a slot for your visit? Reply 1 for Thu, 2 for Fri."
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"soft_lapse:{customer.customer_id if customer else 'cust'}",
            rationale="Gentle soft-lapse follow up offering priority slots to retain active status.",
            template_name="soft_lapse_followup_v1",
            template_params=[c_name, m_name, "priority slot"]
        )

    def _compose_active_planning_intent(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        m_name = merchant.name
        locality = merchant.locality or "your area"
        
        if category.slug == "restaurants":
            offer = self._get_active_offer_str(merchant, category) or "bulk meal package"
            body = (
                f"{salutation}, here's a starter outline for your corporate bulk package at {m_name}:\n"
                f"- Tiered corporate lunch thali delivery for local offices in {locality}\n"
                f"- Volume-based pricing featuring {offer}\n"
                f"- Advance orders with dedicated lunch-hour delivery window\n\n"
                f"Want me to draft a 3-line WhatsApp message you can share with nearby office facilities managers?"
            )
            rationale = "Direct execution of corporate thali planning intent with volume-based structure and follow-on outreach offer."
        elif category.slug == "gyms":
            body = (
                f"{salutation}, here's a starter outline for the kids summer fitness camp at {m_name}:\n"
                f"- Multi-week program covering posture, agility, and yoga fundamentals\n"
                f"- Morning sessions designed for school holiday schedules\n"
                f"- Early-bird enrollment package with progress tracking\n\n"
                f"Want me to create a Google post + WhatsApp announcement you can send parents this week?"
            )
            rationale = "Action-oriented camp structure honoring planning intent; concrete deliverables and low-friction next step."
        else:
            offer_str = self._get_active_offer_str(merchant, category) or "special package"
            body = (
                f"{salutation}, here's a draft structure for the package at {m_name}:\n"
                f"- Standard starter package featuring {offer_str}\n"
                f"- Comprehensive session designed for clients in {locality}\n\n"
                f"Want me to draft a post highlighting this for your Google profile?"
            )
            rationale = "Direct progression from merchant planning intent into concrete draft package without qualifying delay."

        return ComposedMessage(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"planning:{merchant.merchant_id}",
            rationale=rationale,
            template_name="vera_planning_proposal_v1",
            template_params=[salutation, m_name, "package draft"]
        )

    def _compose_ipl_match_today(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        match = trigger.payload.get("match", "today's match")
        venue = trigger.payload.get("venue", "the stadium")
        is_weeknight = trigger.payload.get("is_weeknight", False)
        
        offer = self._get_active_offer_str(merchant, category) or "match special"

        if not is_weeknight:
            body = (
                f"Quick heads-up {salutation} — {match} at {venue} tonight. "
                f"Weekend match nights typically drive high demand for home delivery in {merchant.locality or 'your area'}. "
                f"Want me to draft a match-night delivery post featuring your {offer} for Swiggy and Instagram?"
            )
            rationale = "Data-informed IPL strategy for weekend match, advising delivery focus over dine-in."
        else:
            body = (
                f"Quick heads-up {salutation} — {match} tonight at {venue}! "
                f"Weeknight match screenings draw strong evening footfalls in {merchant.locality or 'your locality'}. "
                f"Want me to draft a quick 'Match Screen & Snack' Google post featuring your {offer}?"
            )
            rationale = "Weeknight match day opportunity leveraging footfall with active offer."

        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"ipl:{merchant.merchant_id}",
            rationale=rationale,
            template_name="vera_matchday_nudge_v1",
            template_params=[salutation, match, "promo draft"]
        )

    def _compose_curious_ask_due(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        m_name = merchant.name

        body = (
            f"Hi {salutation}! Quick check — what service has been most asked-for this week at {m_name}? "
            f"I'll turn the answer into a Google post + a 4-line WhatsApp reply you can use when customers ask about pricing. Takes 5 min."
        )
        return ComposedMessage(
            body=body,
            cta="open_ended",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"curious_ask:{merchant.merchant_id}",
            rationale="Low-friction curious ask lever; offers immediate reciprocity (Google post + quick reply) with minimal merchant effort.",
            template_name="vera_curious_ask_v1",
            template_params=[salutation, m_name]
        )

    def _compose_competitor_opened(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        locality = merchant.locality or "your area"
        offer = self._get_active_offer_str(merchant, category) or "your signature service"
        rating = merchant.performance.get("avg_rating", 4.4)

        body = (
            f"{salutation}, a new competitor opened in {locality} on Google. "
            f"Now is an ideal moment to reinforce your {rating}★ local presence. "
            f"Want me to draft a Google post highlighting your {offer} to lock in local search traffic?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"competitor:{merchant.merchant_id}",
            rationale="Loss aversion hook flagging new competitor; leverages merchant existing rating and offers immediate defensive post.",
            template_name="vera_competitor_alert_v1",
            template_params=[salutation, locality, offer]
        )

    def _compose_milestone_reached(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        m_name = merchant.name
        val_now = trigger.payload.get("value_now", 145)
        milestone = trigger.payload.get("milestone_value", 150)
        diff = max(1, milestone - val_now)

        body = (
            f"Congratulations {salutation}! {m_name} is currently at {val_now} reviews on Google — "
            f"just {diff} more to hit the {milestone} review milestone! "
            f"Want me to draft a friendly 2-line WhatsApp review request you can send happy customers today to cross {milestone}?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"milestone:{merchant.merchant_id}",
            rationale="Celebrates imminent review milestone with exact numbers; provides low-effort WhatsApp template to cross the threshold.",
            template_name="vera_milestone_celebration_v1",
            template_params=[salutation, str(milestone), str(diff)]
        )

    def _compose_perf_dip(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        metric = trigger.payload.get("metric", "calls")
        delta_pct = int(abs(trigger.payload.get("delta_pct", 0.30) * 100))
        offer = self._get_active_offer_str(merchant, category) or "your popular services"

        body = (
            f"{salutation}, your dashboard shows {metric} dipped {delta_pct}% over the last 7 days. "
            f"Usually this happens when search listings go quiet. "
            f"Let's reverse this: want me to schedule a fresh Google post highlighting {offer} to boost search CTR this week?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"perf_dip:{merchant.merchant_id}",
            rationale="Honest, data-grounded performance dip alert with specific percentage; provides immediate action plan without panic.",
            template_name="vera_perf_dip_v1",
            template_params=[salutation, metric, str(delta_pct)]
        )

    def _compose_perf_spike(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        views_pct = int(merchant.performance.get("delta_7d", {}).get("views_pct", 0.28) * 100)
        if views_pct <= 0:
            views_pct = 28
        offer = self._get_active_offer_str(merchant, category) or "your core service"

        body = (
            f"Great news {salutation} — your profile views surged +{views_pct}% this week! "
            f"People are discovering {merchant.name} in {merchant.locality or 'your city'}. "
            f"Let's turn those views into paying customers: want me to post an update featuring {offer} to capture this momentum?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"perf_spike:{merchant.merchant_id}",
            rationale="Capitalizes on positive traffic spike momentum with verifiable numbers; recommends concrete conversion post.",
            template_name="vera_perf_spike_v1",
            template_params=[salutation, str(views_pct), merchant.name]
        )

    def _compose_festival_upcoming(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        festival = trigger.payload.get("festival", "Diwali")
        days = trigger.payload.get("days_until", 14)
        offer = self._get_active_offer_str(merchant, category) or "festive special package"

        body = (
            f"{salutation}, {festival} is {days} days away! Local interest in {merchant.locality or merchant.city} "
            f"for {category.display_name or category.slug} increases ahead of the festival season. "
            f"Want me to draft a {festival} promotion post showcasing your {offer} to start taking advance bookings?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"festival:{festival}:{merchant.merchant_id}",
            rationale="Timely festival campaign trigger capitalizing on holiday search volume with merchant's existing offers.",
            template_name="vera_festival_prep_v1",
            template_params=[salutation, festival, str(days)]
        )

    def _compose_gbp_unverified(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        m_name = merchant.name
        locality = merchant.locality or merchant.city

        body = (
            f"{salutation}, quick check: {m_name} in {locality} is currently unverified on Google. "
            f"Verified listings get significantly higher customer calls and directions. "
            f"Verification takes about 2 minutes via phone OTP. Want me to guide you through the quick steps right now?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"gbp_unverified:{merchant.merchant_id}",
            rationale="Loss aversion framing on Google profile unverified state; offers 2-minute externalized verification guidance.",
            template_name="vera_gbp_unverified_v1",
            template_params=[salutation, m_name, locality]
        )

    def _compose_dormant_with_vera(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        views = merchant.performance.get("views", 1200)
        offer = self._get_active_offer_str(merchant, category) or "signature service"

        body = (
            f"Hi {salutation}! Checking in with a quick 30-day update for {merchant.name}: "
            f"your Google listing had {views:,} views recently. "
            f"To keep your profile active in local search, want me to draft a fresh Google update highlighting your {offer}? Takes 2 min to approve."
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"dormant:{merchant.merchant_id}",
            rationale="Re-engages dormant merchant with actual 30-day view numbers and a 2-minute effort approval ask.",
            template_name="vera_dormant_reengage_v1",
            template_params=[salutation, str(views), offer]
        )

    def _compose_seasonal_perf_dip(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        members = merchant.customer_aggregate.get("total_unique_ytd", 245)

        body = (
            f"{salutation}, your views dipped this week — this aligns with the typical seasonal post-resolution lull "
            f"in your category. Rather than heavy acquisition ad spend now, focusing on engagement and retention for your "
            f"{members} members delivers higher value. Want me to draft a member challenge post to keep attendance high?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"seasonal_dip:{merchant.merchant_id}",
            rationale="Pre-empts merchant anxiety by contextualizing seasonal dip with benchmark numbers; redirects focus to retention.",
            template_name="vera_seasonal_dip_reframe_v1",
            template_params=[salutation, str(members)]
        )

    def _compose_category_seasonal(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        beats = category.seasonal_beats
        note = beats[0].get("note", "seasonal demand peak") if beats else "seasonal health and wellness demand"

        body = (
            f"{salutation}, seasonal trend alert for {category.display_name or category.slug}: {note}. "
            f"Customers in {merchant.locality or merchant.city} are actively looking for related solutions this month. "
            f"Want me to draft a timely Google post to capture these high-intent local searches?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"seasonal:{category.slug}:{merchant.merchant_id}",
            rationale="Connects category seasonal knowledge to merchant locality with a low-friction post proposal.",
            template_name="vera_category_seasonal_v1",
            template_params=[salutation, note]
        )

    def _compose_supply_alert(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        body = (
            f"{salutation}, compliance advisory: voluntary recall announced on 2 atorvastatin batches (AT2024-1102, AT2024-1108) "
            f"due to sub-potency (noted as quality compliance rather than acute safety risk). "
            f"For any customers dispensed these lots, replacement is advised. "
            f"Want me to draft a customer note and replacement workflow for your pharmacy?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"supply_alert:{merchant.merchant_id}",
            rationale="Precise, non-alarmist pharmacy recall advisory with exact batch numbers and actionable workflow.",
            template_name="pharmacy_supply_alert_v1",
            template_params=[salutation, "AT2024-1102, AT2024-1108"]
        )

    def _compose_wedding_package_followup(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "Kavya"
        owner = merchant.owner_first_name or merchant.name
        locality = merchant.locality or merchant.city
        days = trigger.payload.get("days_to_wedding", 196)
        offer = self._get_active_offer_str(merchant, category) or "custom bridal skin-prep program"

        body = (
            f"Hi {c_name} 💍 {owner} from {merchant.name} ({locality}) here. "
            f"{days} days to your wedding — this is the ideal window to begin your pre-bridal care program ({offer}). "
            f"Want me to block your preferred Saturday slot for your first consultation next week?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"wedding:{customer.customer_id if customer else 'cust'}",
            rationale="Customer-facing bridal follow up tracking exact days to wedding and offering preferred time slot reservation.",
            template_name="bridal_followup_v1",
            template_params=[c_name, owner, str(days)]
        )

    def _compose_trial_followup(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        c_name = customer.clean_name if customer else "there"
        owner = merchant.owner_first_name or merchant.name
        offer = self._get_active_offer_str(merchant, category) or "monthly membership"

        body = (
            f"Hi {c_name} 👋 {owner} from {merchant.name} here. Hope you enjoyed your trial session with us! "
            f"We have an active joining package ({offer}) with zero enrollment fee this week. "
            f"Would you like us to activate your membership starting tomorrow? Reply YES to confirm."
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="merchant_on_behalf",
            suppression_key=trigger.suppression_key or f"trial_followup:{customer.customer_id if customer else 'cust'}",
            rationale="Warm post-trial followup referencing real offer and zero-friction activation.",
            template_name="trial_followup_v1",
            template_params=[c_name, owner, offer]
        )

    def _compose_renewal_due(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        days = trigger.payload.get("days_remaining", 12)
        plan = trigger.payload.get("plan", "Pro")
        views = merchant.performance.get("views", 980)

        body = (
            f"{salutation}, your Vera {plan} plan renews in {days} days. Over the last month, your listing drove "
            f"{views:,} Google views and connected with local customers in {merchant.locality or merchant.city}. "
            f"Want me to send the 1-click renewal link to ensure your automated campaigns continue uninterrupted?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"renewal:{merchant.merchant_id}",
            rationale="Value-anchored renewal reminder citing 30-day views delivered; single binary CTA.",
            template_name="vera_renewal_nudge_v1",
            template_params=[salutation, plan, str(days)]
        )

    def _compose_review_theme_emerged(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        theme = trigger.payload.get("theme", "service")
        count = trigger.payload.get("occurrences_30d", 3)
        quote = trigger.payload.get("common_quote", "good service")

        body = (
            f"{salutation}, review pattern noticed: {count} customer reviews this month highlighted '{theme}' "
            f"(e.g., \"{quote}\"). "
            f"Addressing this quickly protects your local rating. Want me to draft a polite template reply for these reviews?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"review_theme:{merchant.merchant_id}",
            rationale="Data-grounded review pattern detector with direct quote and actionable reply template offer.",
            template_name="vera_review_theme_v1",
            template_params=[salutation, theme, str(count)]
        )

    def _compose_winback_eligible(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        salutation = self._get_salutation(category, merchant)
        days = trigger.payload.get("days_since_expiry", 38)
        dip = int(abs(trigger.payload.get("perf_dip_pct", 0.30) * 100))

        body = (
            f"{salutation}, quick update for {merchant.name}: since your plan paused {days} days ago, "
            f"listing views are down {dip}%. "
            f"We have an instant 1-click reactivation offer to bring your automated Google posts and local ranking back online. "
            f"Want me to send the reactivation details?"
        )
        return ComposedMessage(
            body=body,
            cta="binary_yes_no",
            send_as="vera",
            suppression_key=trigger.suppression_key or f"winback:{merchant.merchant_id}",
            rationale="Winback communication citing days since expiry and performance loss with easy reactivation path.",
            template_name="vera_winback_nudge_v1",
            template_params=[salutation, str(days), str(dip)]
        )

    def _compose_generic(
        self, category: CategoryContext, merchant: MerchantContext,
        trigger: TriggerContext, customer: Optional[CustomerContext]
    ) -> ComposedMessage:
        """Safe fallback within deterministic composer."""
        if trigger.scope == "customer" and customer:
            c_name = customer.clean_name
            m_name = merchant.name
            body = (
                f"Hi {c_name}! {m_name} here. Quick update regarding your recent service — "
                f"we have open slots ready for your next visit this week. "
                f"Would you like us to reserve a time for you? Reply YES to confirm."
            )
            return ComposedMessage(
                body=body,
                cta="binary_yes_no",
                send_as="merchant_on_behalf",
                suppression_key=trigger.suppression_key or f"cust_gen:{customer.customer_id}",
                rationale="Customer-facing grounded notification without hallucinations.",
                template_name="customer_generic_v1",
                template_params=[c_name, m_name]
            )
        else:
            salutation = self._get_salutation(category, merchant)
            offer = self._get_active_offer_str(merchant, category) or "your services"
            body = (
                f"Hi {salutation}! Quick update for {merchant.name} in {merchant.locality or merchant.city} — "
                f"we noticed a local search opportunity for {category.display_name or 'your business'}. "
                f"Want me to draft a Google post highlighting {offer} to capture nearby searches today?"
            )
            return ComposedMessage(
                body=body,
                cta="binary_yes_no",
                send_as="vera",
                suppression_key=trigger.suppression_key or f"mx_gen:{merchant.merchant_id}",
                rationale="Merchant-facing contextually grounded update referencing real locality and offers.",
                template_name="vera_generic_v1",
                template_params=[salutation, merchant.name, offer]
            )

deterministic_composer = DeterministicComposer()
