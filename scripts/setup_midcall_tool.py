import argparse
import logging
from omnidimension import Client
from app.config import OMNIDIM_API_KEY, OMNIDIM_AGENT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup_midcall_tool")


def register_tool(webhook_url: str, agent_id: int):
    client = Client(OMNIDIM_API_KEY)

    logger.info(f"Creating custom API integration on OmniDimension pointing to: {webhook_url}")

    body_params = [
        {
            "key": "intent",
            "description": "Lead classification intent: HOT (asking price/timeline/details), WARM (barrier/needs callback), or COLD",
            "type": "string",
            "required": True,
            "isLLMGenerated": True,
        },
        {
            "key": "context",
            "description": "Specific requirements or items the user requested during the conversation",
            "type": "string",
            "required": True,
            "isLLMGenerated": True,
        },
        {
            "key": "phone_number",
            "description": "Customer phone number to dispatch WhatsApp to",
            "type": "string",
            "required": False,
            "isLLMGenerated": True,
        },
    ]

    response = client.integrations.create_custom_api_integration(
        name="send_whatsapp_details",
        description=(
            "Use this tool DURING THE CALL when the customer asks for details, asks about pricing, "
            "asks how soon we can start, or shows high buying interest (HOT lead). "
            "It immediately dispatches our e-commerce packages and portfolio to their WhatsApp while you are talking."
        ),
        url=webhook_url,
        method="POST",
        headers=[{"key": "Content-Type", "value": "application/json"}],
        body_type="json",
        body_params=body_params,
        stop_listening=False,
        request_timeout=8,
    )

    logger.info(f"Integration created response: {response}")

    integration_id = None
    if isinstance(response, dict):
        if "json" in response and isinstance(response["json"], dict):
            integration_id = (
                response["json"].get("integration_id")
                or response["json"].get("id")
            )
        elif "integration_id" in response:
            integration_id = response.get("integration_id")
        elif "id" in response:
            integration_id = response.get("id")

    if integration_id:
        logger.info(f"Adding integration ID {integration_id} to Agent {agent_id}...")
        add_resp = client.integrations.add_integration_to_agent(
            agent_id=int(agent_id),
            integration_id=int(integration_id),
        )
        logger.info(f"Integration attached to agent successfully: {add_resp}")
    else:
        logger.warning(
            "Could not parse integration_id automatically. Check OmniDimension dashboard or API response."
        )


def main():
    parser = argparse.ArgumentParser(description="Attach Mid-Call WhatsApp Tool to OmniDimension Agent")
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Public Webhook URL (e.g. https://your-ngrok-url.app/webhook/in-call-action)",
    )
    parser.add_argument(
        "--agent-id",
        type=int,
        default=int(OMNIDIM_AGENT_ID),
        help="OmniDimension Agent ID",
    )
    args = parser.parse_args()

    register_tool(webhook_url=args.url, agent_id=args.agent_id)


if __name__ == "__main__":
    main()
