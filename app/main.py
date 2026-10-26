import argparse
import json
import logging
import sys
from typing import Dict, Any, Optional

from app.config import OMNIDIM_AGENT_ID
from app.telephony.service import TelephonyService
from app.conversation.parser import ConversationParser
from app.intelligence.understand import extract_lead_data
from app.intelligence.classifier import LeadClassifier
from app.scheduling.callback import detect_and_parse_callback
from app.actions.whatsapp import send_whatsapp_message
from app.followup.service import FollowupService
from app.database.repository import DatabaseRepository
from app.database.models import LeadRecord, CallbackRecord, FollowupRecord

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("elevate_sales_agent")


class SalesAgentPipeline:
    """
    End-to-end execution pipeline for ElevateBox Sales Agent:
    DIAL -> SPEAK -> DISCOVER -> UNDERSTAND -> CLASSIFY -> ACT -> SCHEDULE -> FOLLOW UP
    """

    def __init__(
        self,
        telephony: Optional[TelephonyService] = None,
        db_repo: Optional[DatabaseRepository] = None,
    ):
        self.telephony = telephony or TelephonyService()
        self.db = db_repo or DatabaseRepository()
        self.classifier = LeadClassifier()

    def process_call_data(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the post-call intelligence and action pipeline:
        DISCOVER -> UNDERSTAND -> CLASSIFY -> SCHEDULE -> ACT -> FOLLOW UP -> PERSIST
        """
        call_id = call_data.get("id")
        logger.info(f"=== Starting Sales Agent Pipeline for Call ID: {call_id} ===")

        # 1. DISCOVER: Parse conversation and isolate customer statements
        logger.info("[Step 1: DISCOVER] Parsing conversation and isolating customer statements...")
        ctx = ConversationParser.parse_call_log(call_data)
        customer_phone = ctx.customer_phone
        logger.info(
            f"Extracted {len(ctx.turns)} dialogue turns and {len(ctx.customer_statements)} customer statements. "
            f"Customer Phone: {customer_phone}"
        )

        # 2. UNDERSTAND: Extract structured lead data
        logger.info("[Step 2: UNDERSTAND] Performing deterministic & grounded semantic extraction...")
        lead_data = extract_lead_data(
            conversation=ctx.clean_transcript or ctx.raw_transcript,
            customer_statements=ctx.customer_statements,
        )
        logger.info(f"Extracted Lead: {lead_data}")

        # 3. CLASSIFY: Transparent rule-based qualification
        logger.info("[Step 3: CLASSIFY] Evaluating lead qualification signals...")
        classification = self.classifier.classify(
            lead_data,
            conversation_text=ctx.clean_transcript or ctx.raw_transcript,
        )
        logger.info(
            f"State: {classification.state} | Action: {classification.next_action} | Score: {classification.score}/100"
        )
        if classification.barrier:
            logger.info(f"Barrier Detected: {classification.barrier}")
        for reason in classification.reasons:
            logger.info(f" - {reason}")

        # 4. SCHEDULE: Detect callback intent and schedule
        logger.info("[Step 4: SCHEDULE] Checking for callback requests...")
        callback_schedule = detect_and_parse_callback(ctx.customer_statements)
        callback_dict = None
        if callback_schedule:
            logger.info(
                f"Callback intent detected! Scheduled for: {callback_schedule.iso_scheduled_time} ({callback_schedule.timezone})"
            )
            callback_dict = callback_schedule.to_dict()
            cb_record = CallbackRecord(
                call_id=call_id,
                phone_number=customer_phone,
                raw_request=callback_schedule.raw_request,
                scheduled_time=callback_schedule.iso_scheduled_time or "",
                timezone=callback_schedule.timezone,
                status=callback_schedule.status,
            )
            self.db.save_callback(cb_record)
        else:
            logger.info("No callback request detected in customer statements.")

        # 5. ACT: WhatsApp action for HOT leads
        whatsapp_result = None
        if classification.classification == "HOT" and customer_phone:
            logger.info(f"[Step 5: ACT] Lead is HOT. Triggering WhatsApp touchpoint for {customer_phone}...")
            initial_message = (
                "Hi, this is ElevateBox! Great speaking with you today about your e-commerce website requirements. "
                "Our team has received your details and is putting together tailored options for your project."
            )
            whatsapp_result = send_whatsapp_message(to_number=customer_phone, message=initial_message)
            logger.info(f"WhatsApp Action Status: {whatsapp_result.get('status')}")
        else:
            logger.info("[Step 5: ACT] Lead is not HOT or customer phone missing; skipping immediate WhatsApp trigger.")

        # 6. FOLLOW UP: Generate grounded, personalized follow-up
        logger.info("[Step 6: FOLLOW UP] Generating personalized follow-up message...")
        followup_result = None
        if customer_phone:
            followup_result = FollowupService.dispatch_followup(
                to_number=customer_phone,
                lead=lead_data,
                channel="whatsapp",
            )
            fu_record = FollowupRecord(
                call_id=call_id,
                phone_number=customer_phone,
                message=followup_result.get("message", ""),
                channel=followup_result.get("channel", "whatsapp"),
                status=followup_result.get("status", "logged"),
            )
            self.db.save_followup(fu_record)
            logger.info(f"Follow-up Status: {followup_result.get('status')}")

        # 7. PERSIST: Save structured lead to SQLite
        logger.info("[Step 7: PERSIST] Saving lead and interaction records to SQLite database...")
        lead_record = LeadRecord(
            call_id=call_id,
            phone_number=customer_phone,
            business_type=lead_data.get("business_type"),
            product_count_min=lead_data.get("product_count_min"),
            product_count_max=lead_data.get("product_count_max"),
            payment_gateway=lead_data.get("payment_gateway"),
            customer_accounts=lead_data.get("customer_accounts"),
            guest_checkout=lead_data.get("guest_checkout"),
            timeline_months=lead_data.get("timeline_months"),
            budget_min=lead_data.get("budget_min"),
            budget_max=lead_data.get("budget_max"),
            additional_requirements=lead_data.get("additional_requirements"),
            inferred_business_type=lead_data.get("inferred_business_type"),
            classification=classification.classification,
            score=classification.score,
            reasons=classification.reasons,
            transcript=ctx.clean_transcript or ctx.raw_transcript,
        )
        self.db.save_lead(lead_record)
        logger.info("Pipeline execution successfully completed.")

        return {
            "call_id": call_id,
            "customer_phone": customer_phone,
            "lead": lead_data,
            "classification": classification.to_dict(),
            "callback": callback_dict,
            "whatsapp_action": whatsapp_result,
            "followup": followup_result,
            "transcript_summary": {
                "turns_count": len(ctx.turns),
                "customer_statements_count": len(ctx.customer_statements),
            },
        }

    def process_call(self, call_id: int) -> Dict[str, Any]:
        """Fetches call log from OmniDimension and runs the pipeline."""
        call_data = self.telephony.get_call_data(call_id)
        return self.process_call_data(call_data)

    def dial(self, phone_number: str, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """Initiates an outbound call via OmniDimension."""
        aid = agent_id or int(OMNIDIM_AGENT_ID)
        return self.telephony.dispatch_call(agent_id=aid, to_number=phone_number)


def main():
    parser = argparse.ArgumentParser(description="ElevateBox Sales Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: process (fetch from OmniDimension by call_id)
    cmd_proc = subparsers.add_parser("process", help="Process a completed call from OmniDimension")
    cmd_proc.add_argument("--call-id", type=int, required=True, help="OmniDimension call ID")

    # Command: process-file (process local JSON dump of call data)
    cmd_file = subparsers.add_parser("process-file", help="Process a local call JSON file")
    cmd_file.add_argument("--path", type=str, required=True, help="Path to call JSON file")

    # Command: dial (trigger outbound call)
    cmd_dial = subparsers.add_parser("dial", help="Trigger an outbound voice call")
    cmd_dial.add_argument("--phone", type=str, required=True, help="Target phone number (E.164)")
    cmd_dial.add_argument("--agent-id", type=int, default=None, help="OmniDimension agent ID")

    # Command: list-leads
    subparsers.add_parser("list-leads", help="List all processed leads from SQLite")

    # Command: get-lead
    cmd_get = subparsers.add_parser("get-lead", help="Get a lead from SQLite by call ID")
    cmd_get.add_argument("--call-id", type=int, required=True, help="OmniDimension call ID")

    args = parser.parse_args()

    pipeline = SalesAgentPipeline()

    if args.command == "process":
        result = pipeline.process_call(args.call_id)
        print("\n" + "=" * 50)
        print("PIPELINE RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

    elif args.command == "process-file":
        with open(args.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = pipeline.process_call_data(data)
        print("\n" + "=" * 50)
        print("PIPELINE RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

    elif args.command == "dial":
        res = pipeline.dial(args.phone, args.agent_id)
        print(f"Call dispatch response: {res}")

    elif args.command == "list-leads":
        leads = pipeline.db.list_leads()
        print(f"\nFound {len(leads)} leads in database:")
        for l in leads:
            print(f"- Call {l.call_id} | Phone: {l.phone_number} | Tier: {l.classification} (Score: {l.score}) | Budget: Rs. {l.budget_min}-{l.budget_max} | Products: {l.product_count_min}-{l.product_count_max}")

    elif args.command == "get-lead":
        l = pipeline.db.get_lead_by_call_id(args.call_id)
        if l:
            print(json.dumps(l.to_dict(), indent=2))
        else:
            print(f"No lead found with call ID {args.call_id}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
