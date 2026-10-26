import logging
from typing import Optional, Dict, Any
from omnidimension import Client

from app.config import OMNIDIM_API_KEY

logger = logging.getLogger(__name__)


class TelephonyService:
    """
    Service wrapper around OmniDimension client for outbound call dispatch,
    agent behavioral configuration, and post-call log retrieval.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OMNIDIM_API_KEY
        if not self.api_key:
            logger.warning("OMNIDIM_API_KEY is not configured.")
        self.client = Client(self.api_key) if self.api_key else None

    def dispatch_call(
        self,
        agent_id: int,
        to_number: str,
        call_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches an outbound AI sales call to the given phone number.
        """
        if not self.client:
            raise ValueError("OmniDimension client is not initialized. Check OMNIDIM_API_KEY.")

        if call_context is None:
            call_context = {}

        logger.info(f"[Telephony] Dispatching outbound call to {to_number} using agent_id {agent_id}...")
        try:
            response = self.client.call.dispatch_call(
                agent_id,
                to_number,
                call_context=call_context,
            )
            logger.info(f"[Telephony] Call dispatched successfully: {response}")
            return response
        except Exception as exc:
            logger.error(f"[Telephony] Error dispatching call to {to_number}: {exc}")
            raise

    def get_call_log(self, call_id: int) -> Dict[str, Any]:
        """
        Retrieves completed call logs, interactions, transcript, and metadata.
        """
        if not self.client:
            raise ValueError("OmniDimension client is not initialized. Check OMNIDIM_API_KEY.")

        logger.info(f"[Telephony] Fetching call log for call_id={call_id}...")
        try:
            response = self.client.call.get_call_log(call_id)
            return response
        except Exception as exc:
            logger.error(f"[Telephony] Error fetching call log {call_id}: {exc}")
            raise

    def get_call_data(self, call_id: int) -> Dict[str, Any]:
        """
        Convenience method to retrieve the primary call data dictionary for a call_id.
        """
        resp = self.get_call_log(call_id)
        if (
            isinstance(resp, dict)
            and "json" in resp
            and "call_log_data" in resp["json"]
            and len(resp["json"]["call_log_data"]) > 0
        ):
            return resp["json"]["call_log_data"][0]
        raise ValueError(f"No call_log_data found in response for call_id={call_id}")

    def get_agent(self, agent_id: int) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("OmniDimension client is not initialized.")
        return self.client.agent.get(agent_id)

    def update_discovery_behavior(self, agent_id: int) -> Dict[str, Any]:
        """
        Configures the voice agent prompt for natural discovery rather than rigid questionnaires.
        """
        if not self.client:
            raise ValueError("OmniDimension client is not initialized.")

        return self.client.agent.update(
            agent_id,
            {
                "context_breakdown": [
                    {
                        "title": "Role",
                        "body": (
                            "You are a sales representative for ElevateBox, "
                            "an e-commerce website development company."
                        ),
                    },
                    {
                        "title": "Conversation",
                        "body": (
                            "Your goal is to have a natural sales conversation "
                            "with a potential customer who may need an "
                            "e-commerce website.\n\n"
                            "Start by introducing ElevateBox and briefly explain "
                            "that we build e-commerce websites.\n\n"
                            "Do not sound like a scripted questionnaire.\n\n"
                            "First understand the customer's business and what "
                            "they want to build.\n\n"
                            "During the conversation, naturally discover:\n"
                            "- what products or services they sell\n"
                            "- approximately how many products they have\n"
                            "- what features they need in the website\n"
                            "- when they want the website\n"
                            "- their approximate budget\n\n"
                            "Do not ask all of these questions one after another mechanically.\n\n"
                            "Use the customer's previous answers to decide what to ask next. "
                            "If the customer has already answered something, do not ask for it again.\n\n"
                            "If an answer is vague, ask a short natural follow-up question.\n\n"
                            "Keep the conversation focused on their requirements and explain "
                            "relevant e-commerce capabilities when useful.\n\n"
                            "Do not pressure the customer. Do not invent information about their business.\n\n"
                            "Before ending the conversation, make sure you have tried to understand "
                            "the important requirements above."
                        ),
                    },
                ],
                "welcome_message": (
                    "Hi, I'm calling from ElevateBox. "
                    "We help businesses build e-commerce websites. "
                    "Is this a good time to talk?"
                ),
            },
        )

    def configure_extraction(self, agent_id: int) -> Dict[str, Any]:
        """
        Configures post-call extraction variables on OmniDimension.
        """
        if not self.client:
            raise ValueError("OmniDimension client is not initialized.")

        post_call_actions = {
            "email": {
                "enabled": False,
                "include": ["extracted_variables"],
                "extracted_variables": [
                    {
                        "key": "business",
                        "prompt": "What type of business does the customer run or what business are they planning to start?",
                    },
                    {
                        "key": "products",
                        "prompt": "What products or services does the customer sell or want to sell online?",
                    },
                    {
                        "key": "product_count",
                        "prompt": "Approximately how many products does the customer have or expect to sell?",
                    },
                    {
                        "key": "features",
                        "prompt": "What website features did the customer mention wanting?",
                    },
                    {
                        "key": "timeline",
                        "prompt": "When does the customer want the website or online store to be ready?",
                    },
                    {
                        "key": "budget",
                        "prompt": "What budget did the customer mention for the website?",
                    },
                ],
            }
        }

        return self.client.agent.update(
            agent_id,
            {
                "post_call_actions": post_call_actions,
            },
        )