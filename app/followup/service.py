from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import zoneinfo

from app.actions.whatsapp import send_whatsapp_message
from app.config import (
    TIMEZONE,
    CANDIDATE_MOBILE_NUMBER,
    ARCHITECTURE_IMAGE_URL,
    EVALUATOR_PHONE_NUMBER,
)

logger = logging.getLogger(__name__)


class FollowupService:
    """
    Generates personalized, grounded follow-up messages based strictly on
    confirmed customer requirements, compliant with Section 06 requirements:
    1. Context of the call (what was wanted, budget, timeline, features)
    2. Proper human framing (reads like a thoughtful post-call follow-up)
    3. Mobile number clearly visible for callbacks
    4. Image link showing architecture and flow
    """

    @staticmethod
    def generate_message(
        lead: Dict[str, Any],
        recipient_name: Optional[str] = None,
        candidate_phone: Optional[str] = None,
        architecture_url: Optional[str] = None,
    ) -> str:
        """
        Creates a follow-up message strictly referencing confirmed facts and Section 06 items.
        Never hallucinates unconfirmed details (e.g. unconfirmed business types).
        """
        greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
        lines: List[str] = [f"{greeting} thank you for taking the time to speak with ElevateBox today."]

        # 1. Project Scope & Business Type
        b_type = lead.get("business_type")
        p_min = lead.get("product_count_min")
        p_max = lead.get("product_count_max")

        scope_parts: List[str] = []
        if b_type:
            scope_parts.append(f"an e-commerce website for your {b_type} business")
        else:
            scope_parts.append("an e-commerce website")

        if p_min is not None and p_max is not None:
            if p_min == p_max:
                scope_parts.append(f"for approximately {p_min} products")
            else:
                scope_parts.append(f"for approximately {p_min} - {p_max} products")
        elif p_min is not None:
            scope_parts.append(f"for approximately {p_min} products")

        lines.append(f"We noted that you are looking to build {' '.join(scope_parts)}.")

        # 2. Key Features
        feature_parts: List[str] = []
        if lead.get("payment_gateway") is True:
            feature_parts.append("payment gateway integration")

        if lead.get("guest_checkout") is True and lead.get("customer_accounts") is False:
            feature_parts.append("guest checkout without forced customer accounts")
        elif lead.get("guest_checkout") is True:
            feature_parts.append("guest checkout support")
        elif lead.get("customer_accounts") is True:
            feature_parts.append("customer account management")

        if lead.get("additional_requirements"):
            feature_parts.append(f"features: {lead['additional_requirements']}")

        if feature_parts:
            lines.append(f"Key specifications included: {', '.join(feature_parts)}.")

        # 3. Timeline & Budget
        timeline = lead.get("timeline_months")
        b_min = lead.get("budget_min")
        b_max = lead.get("budget_max")

        closing_parts: List[str] = []
        if timeline:
            closing_parts.append(f"your {timeline}-month target timeline")

        if b_min is not None and b_max is not None:
            if b_min == b_max:
                closing_parts.append(f"your budget of Rs. {b_min:,}")
            else:
                closing_parts.append(f"your budget range of Rs. {b_min:,} - Rs. {b_max:,}")
        elif b_max is not None:
            closing_parts.append(f"your budget of up to Rs. {b_max:,}")

        if closing_parts:
            lines.append(
                f"Our engineering team will prepare a proposal aligned with {' and '.join(closing_parts)}."
            )
        else:
            lines.append("Our engineering team will review your requirements and reach out shortly.")

        # 4. Visible Mobile Number & Architecture Image (Section 06 Mandatory)
        phone = candidate_phone or CANDIDATE_MOBILE_NUMBER
        arch_img = architecture_url or ARCHITECTURE_IMAGE_URL
        lines.append(f"\nIf you need anything or wish to discuss directly, you can reach me at {phone}.")
        if arch_img:
            lines.append(f"System architecture & flow reference: {arch_img}")

        lines.append("Best regards, ElevateBox Team.")

        return " ".join(lines)

    @classmethod
    def dispatch_followup(
        cls,
        to_number: str,
        lead: Dict[str, Any],
        recipient_name: Optional[str] = None,
        channel: str = "whatsapp",
    ) -> Dict[str, Any]:
        """
        Generates and dispatches the follow-up message across the specified channel.
        """
        message = cls.generate_message(lead=lead, recipient_name=recipient_name)
        tz = zoneinfo.ZoneInfo(TIMEZONE or "Asia/Kolkata")
        now_iso = datetime.now(tz).isoformat()

        if channel == "whatsapp":
            action_result = send_whatsapp_message(to_number=to_number, message=message)
            return {
                "recipient": to_number,
                "message": message,
                "channel": "whatsapp",
                "status": action_result.get("status", "unknown"),
                "delivered": action_result.get("delivered", False),
                "timestamp": now_iso,
                "action_details": action_result,
            }
        else:
            logger.info(f"[Followup] Followup prepared for {to_number} on channel '{channel}'.")
            return {
                "recipient": to_number,
                "message": message,
                "channel": channel,
                "status": "logged",
                "delivered": False,
                "timestamp": now_iso,
            }
