import logging
from typing import Dict, Any, Optional
import requests

from app.config import WHATSAPP_API_KEY, WHATSAPP_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Action interface for sending WhatsApp messages.
    Provides a clean integration boundary for WhatsApp Business API / Cloud API.
    If credentials are not configured, it gracefully reports 'provider_not_configured'
    without faking delivery.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        self.api_key = api_key or WHATSAPP_API_KEY
        self.phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID

    def is_configured(self) -> bool:
        return bool(self.api_key and self.phone_number_id)

    def send_message(
        self,
        to_number: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Sends a WhatsApp message to the specified recipient.
        """
        if not self.is_configured():
            logger.info(
                f"[WhatsApp] Provider not configured. Message to {to_number} logged but not dispatched."
            )
            return {
                "status": "provider_not_configured",
                "delivered": False,
                "recipient": to_number,
                "message": message,
                "error": "WhatsApp provider credentials (WHATSAPP_API_KEY / WHATSAPP_PHONE_NUMBER_ID) not configured in environment.",
            }

        # Format number (remove any spaces, dashes, or leading + for Meta API format)
        clean_recipient = to_number.replace("+", "").replace(" ", "").replace("-", "")

        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_recipient,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message,
            },
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                res_data = response.json()
                logger.info(f"[WhatsApp] Message dispatched successfully to {to_number}.")
                return {
                    "status": "delivered",
                    "delivered": True,
                    "recipient": to_number,
                    "message_id": res_data.get("messages", [{}])[0].get("id"),
                    "response": res_data,
                }
            else:
                logger.error(
                    f"[WhatsApp] Delivery failed with code {response.status_code}: {response.text}"
                )
                return {
                    "status": "delivery_failed",
                    "delivered": False,
                    "recipient": to_number,
                    "status_code": response.status_code,
                    "error": response.text,
                }
        except requests.RequestException as exc:
            logger.error(f"[WhatsApp] Network request error: {exc}")
            return {
                "status": "network_error",
                "delivered": False,
                "recipient": to_number,
                "error": str(exc),
            }


def send_whatsapp_message(to_number: str, message: str) -> Dict[str, Any]:
    """Helper function to dispatch a WhatsApp message."""
    service = WhatsAppService()
    return service.send_message(to_number=to_number, message=message)
