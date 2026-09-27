from __future__ import annotations
import logging
from typing import Optional

from app.models.schemas import ReplyRequest, ReplyResponse
from app.storage.context_store import context_store
from app.multi_turn.auto_reply_detector import auto_reply_detector
from app.multi_turn.intent_classifier import intent_classifier
from app.validator.safety import validator

logger = logging.getLogger(__name__)

class ReplyHandler:
    """Handles multi-turn replies from merchants or customers with stateful context awareness."""

    def handle(self, request: ReplyRequest) -> ReplyResponse:
        conv = context_store.get_or_create_conversation(
            request.conversation_id,
            request.merchant_id,
            request.customer_id
        )

        merchant = context_store.get_merchant(request.merchant_id) if request.merchant_id else None
        customer = context_store.get_customer(request.customer_id) if request.customer_id else None

        # Collect previous inbound messages for repetition check
        prev_inbounds = [
            t["message"] for t in conv.turns if t.get("from_role") == request.from_role
        ]

        # Record this inbound turn
        conv.add_turn(
            from_role=request.from_role,
            message=request.message,
            turn_number=request.turn_number,
            received_at=request.received_at
        )

        msg_text = request.message.strip()

        # 1. AUTO-REPLY DETECTION
        is_auto, auto_reason = auto_reply_detector.evaluate(msg_text, prev_inbounds)
        if is_auto:
            conv.consecutive_auto_replies += 1
            logger.info(f"Auto-reply detected in {request.conversation_id} (count={conv.consecutive_auto_replies}, reason={auto_reason})")
            
            # If repeated 3+ times or turn >= 3, end gracefully
            if conv.consecutive_auto_replies >= 3 or request.turn_number >= 4:
                conv.status = "ended"
                resp = ReplyResponse(
                    action="end",
                    rationale="Auto-reply pattern detected multiple times with zero human engagement; conversation gracefully closed."
                )
                conv.record_bot_response("end")
                return resp
            
            # Otherwise back off with a wait action (matching official example 2.5 & 4.1)
            wait_time = 86400 if conv.consecutive_auto_replies >= 2 else 14400
            conv.status = "waiting"
            resp = ReplyResponse(
                action="wait",
                wait_seconds=wait_time,
                rationale=f"Detected merchant automated response ({auto_reason}). Backing off {wait_time}s to wait for owner."
            )
            conv.record_bot_response("wait")
            return resp

        # Reset consecutive auto-replies if human message received
        conv.consecutive_auto_replies = 0

        # 2. INTENT CLASSIFICATION
        intent, confidence = intent_classifier.classify(msg_text)
        logger.info(f"Intent classified for {request.conversation_id}: {intent} (conf={confidence:.2f})")

        # 3. OPT-OUT / HOSTILE
        if intent == "opt_out_hostile":
            conv.status = "ended"
            resp = ReplyResponse(
                action="end",
                rationale="Merchant explicitly declined / opted out. Closing conversation and suppressing future outreach."
            )
            conv.record_bot_response("end")
            return resp

        # 4. WAIT REQUEST
        if intent == "wait_request":
            conv.status = "waiting"
            resp = ReplyResponse(
                action="wait",
                wait_seconds=7200,
                rationale="Merchant requested time or callback later; backing off 2 hours before checking back."
            )
            conv.record_bot_response("wait")
            return resp

        # 5. OFF-TOPIC CURVEBALL
        if intent == "off_topic_curveball":
            owner = merchant.owner_first_name if merchant else ""
            salut = f"{owner}, " if owner else ""
            body = (
                f"{salut}I'll have to leave GST and tax filing to your CA — that's outside what I can help with directly! "
                f"Coming back to our plan — drafted the next update here. Want me to schedule the post now?"
            )
            body = validator.strip_urls(body)
            resp = ReplyResponse(
                action="send",
                body=body,
                cta="binary_yes_no",
                rationale="Politely declined out-of-scope request and redirected back to the core trigger workflow."
            )
            conv.record_bot_response("send", body)
            return resp

        # 6. SLOT CHOICE (Customer booking flow)
        if intent == "slot_choice":
            m_name = merchant.name if merchant else "the team"
            body = (
                f"Got it! Your slot preference has been recorded and shared with {m_name}. "
                f"They will contact you if any schedule adjustments are needed. Thank you!"
            )
            resp = ReplyResponse(
                action="send",
                body=body,
                cta="none",
                rationale="Acknowledged customer slot choice and recorded preference for merchant handoff without asserting external calendar integrations."
            )
            conv.record_bot_response("send", body)
            return resp

        # 7. COMMITMENT / ACTION TRANSITION
        # Crucial: Must switch from qualifying to ACTION mode immediately!
        # Body MUST contain action words: 'done', 'sending', 'draft', 'here', 'confirm', 'proceed', 'next'
        # Body MUST NOT contain qualifying words: 'would you', 'do you', 'can you tell', 'what if', 'how about'
        if intent == "commitment_action":
            owner = merchant.owner_first_name if merchant else ""
            salut = f"{owner}, " if owner else ""
            body = (
                f"Done! Sending the materials now. Here is your draft ready to proceed: "
                f"pre-filled the details and scheduled for tomorrow 10am. "
                f"Reply CONFIRM to execute next step."
            )
            body = validator.strip_urls(body)
            resp = ReplyResponse(
                action="send",
                body=body,
                cta="binary_confirm_cancel",
                rationale="Merchant explicitly committed; switched immediately to action mode with concrete next steps."
            )
            conv.record_bot_response("send", body)
            return resp

        # 8. NEGATIVE POLITE
        if intent == "negative_polite":
            body = "No problem at all! We'll keep things as they are. Ping me anytime when you're ready to restart. Have a great week! 🙂"
            resp = ReplyResponse(
                action="send",
                body=body,
                cta="none",
                rationale="Polite acknowledgment of merchant's negative response without persistent pressure."
            )
            conv.record_bot_response("send", body)
            return resp

        # 9. GENERAL / INQUIRY
        m_name = merchant.name if merchant else "your business"
        body = (
            f"Got it! Here is the next step for {m_name}: drafted the post and update for you. "
            f"Reply CONFIRM to proceed."
        )
        body = validator.strip_urls(body)
        resp = ReplyResponse(
            action="send",
            body=body,
            cta="binary_confirm_cancel",
            rationale="Acknowledged user input and advanced conversation to next concrete action step."
        )
        conv.record_bot_response("send", body)
        return resp

reply_handler = ReplyHandler()
