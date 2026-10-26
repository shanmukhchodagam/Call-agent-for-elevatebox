import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

from app.actions.whatsapp import send_whatsapp_message
from app.database import DatabaseRepository, LeadRecord, FollowupRecord
from app.config import TIMEZONE

logger = logging.getLogger("midcall_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class MidCallWebhookHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for OmniDimension in-call Custom API integrations.
    Receives triggers mid-call when the caller asks for details, pricing,
    or demonstrates HOT lead buying intent.
    """

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        logger.info(f"[In-Call Webhook] Received mid-call request: {body}")

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # OmniDimension custom API passes parameters in JSON body
        # e.g., phone_number, intent, context, customer_name
        phone_number = data.get("phone_number") or data.get("to_number") or data.get("caller_number")
        intent = data.get("intent", "HOT")
        context_notes = data.get("context") or data.get("message") or "Requested details during call"
        customer_name = data.get("customer_name") or data.get("name")

        dry_run = data.get("dry_run") is True

        if not phone_number and not dry_run:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "error": "Missing phone_number"
            }).encode("utf-8"))
            return

        if dry_run:
            phone_number = phone_number or "DRY_RUN"
        logger.info(f"[In-Call Webhook] Mid-call trigger for phone: {phone_number} (Intent: {intent})")

        # Draft immediate mid-call message
        greeting = f"Hi {customer_name}," if customer_name else "Hi,"
        midcall_message = (
            f"{greeting} this is ElevateBox! While we're speaking on the phone, here is the information "
            f"you requested about our e-commerce packages and portfolio: https://elevatebox.com/packages. "
            f"Note from call: {context_notes}. I'm on the line if you'd like to discuss any of these!"
        )

        # Dispatch via WhatsApp action layer
        if dry_run:
            action_result = {
                "status": "dry_run",
                "delivered": False
            }
            logger.info("[In-Call Webhook] Dry run: WhatsApp dispatch skipped.")
        else:
            action_result = send_whatsapp_message(
                to_number=phone_number,
                message=midcall_message
            )
        logger.info(f"[In-Call Webhook] WhatsApp action result: {action_result.get('status')}")

        # Persist follow-up/action record
        try:
            db = DatabaseRepository()
            db.save_followup(
                FollowupRecord(
                    call_id=data.get("call_id", 0),
                    phone_number=phone_number,
                    message=midcall_message,
                    channel="whatsapp_midcall",
                    status=action_result.get("status", "logged"),
                )
            )
        except Exception as exc:
            logger.warning(f"Could not log mid-call action to DB: {exc}")

        # Return response to OmniDimension bot
        # The bot can speak this response text back to the customer:
        bot_response_text = "I've just sent the details to your WhatsApp right now, you should see them on your screen."
        response_payload = {
            "status": "success",
            "whatsapp_status": action_result.get("status"),
            "delivered": action_result.get("delivered", False),
            "message_for_bot": bot_response_text,
            "reply": bot_response_text,
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_payload).encode("utf-8"))

    def do_GET(self):
        # Health check endpoint
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "active", "service": "ElevateBox Mid-Call Webhook"}).encode("utf-8"))


def run_midcall_server(host: str = "0.0.0.0", port: int = 8000):
    server = HTTPServer((host, port), MidCallWebhookHandler)
    logger.info(f"Starting Mid-Call Webhook Server on {host}:{port}...")
    logger.info(f"Endpoint for OmniDimension Custom API: http://<YOUR_IP_OR_NGROK>:{port}/webhook/in-call-action")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_midcall_server()
