import unittest
from unittest.mock import patch
import os

from app.main import SalesAgentPipeline
from app.database import DatabaseRepository

TEST_E2E_DB = "test_e2e_sales.db"


class TestE2EPipeline(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_E2E_DB):
            try:
                os.remove(TEST_E2E_DB)
            except OSError:
                pass
        self.db = DatabaseRepository(db_path=TEST_E2E_DB)

    def tearDown(self):
        del self.db
        if os.path.exists(TEST_E2E_DB):
            try:
                os.remove(TEST_E2E_DB)
            except OSError:
                pass

    @patch("app.intelligence.understand.extract_semantic_lead_data")
    @patch("app.telephony.service.TelephonyService.get_call_data")
    def test_full_pipeline_mocked_omnidimension_call(self, mock_get_call_data, mock_semantic):
        # 1. Mock OmniDimension call log response for 8605274
        mock_get_call_data.return_value = {
            "id": 8605274,
            "to_number": "+919381758441",
            "from_number": "+918048799598",
            "call_direction": "outbound",
            "call_duration_in_seconds": 42.0,
            "call_status": "completed",
            "call_conversation": (
                "LLM: Hi, I'm calling from ElevateBox.<br/>"
                "User: Yes.<br/>"
                "LLM: Could you tell me a bit about your business?<br/>"
                "User: I ran a closing business and products are almost closed.<br/>"
                "LLM: Okay, so you sell clothing items. About how many products do you have?<br/>"
                "User: Around 500 to 600.<br/>"
                "LLM: Do you need a payment gateway?<br/>"
                "User: Yes, I want the payment gateway.<br/>"
                "LLM: Do you want customer accounts or guest checkout?<br/>"
                "User: Guest checkout, no customer accounts.<br/>"
                "LLM: When do you want the website ready?<br/>"
                "User: In another 2 months.<br/>"
                "LLM: What is your budget?<br/>"
                "User: 50 to 60 thousand.<br/>"
                "LLM: Anything else?<br/>"
                "User: No, that's it.<br/>"
            ),
            "interactions": [
                {"interaction_sequence": 1, "user_query": "", "bot_response": "Hi, I'm calling from ElevateBox."},
                {"interaction_sequence": 2, "user_query": "Yes.", "bot_response": "Could you tell me a bit about your business?"},
                {"interaction_sequence": 3, "user_query": "I ran a closing business and products are almost closed.", "bot_response": "Okay, so you sell clothing items. About how many products do you have?"},
                {"interaction_sequence": 4, "user_query": "Around 500 to 600.", "bot_response": "Do you need a payment gateway?"},
                {"interaction_sequence": 5, "user_query": "Yes, I want the payment gateway.", "bot_response": "Do you want customer accounts or guest checkout?"},
                {"interaction_sequence": 6, "user_query": "Guest checkout, no customer accounts.", "bot_response": "When do you want the website ready?"},
                {"interaction_sequence": 7, "user_query": "In another 2 months.", "bot_response": "What is your budget?"},
                {"interaction_sequence": 8, "user_query": "50 to 60 thousand.", "bot_response": "Anything else?"},
                {"interaction_sequence": 9, "user_query": "No, that's it.", "bot_response": "Have a great day!"},
            ],
        }

        # 2. Mock grounded semantic extraction
        mock_semantic.return_value = {
            "business_type": None,
            "payment_gateway": True,
            "customer_accounts": False,
            "guest_checkout": True,
            "additional_requirements": None,
            "inferred_business_type": "clothing (unconfirmed)",
        }

        pipeline = SalesAgentPipeline(db_repo=self.db)
        result = pipeline.process_call(8605274)

        # 3. Assert pipeline outputs
        self.assertEqual(result["call_id"], 8605274)
        self.assertEqual(result["customer_phone"], "+919381758441")

        lead = result["lead"]
        self.assertIsNone(lead["business_type"])
        self.assertEqual(lead["product_count_min"], 500)
        self.assertEqual(lead["product_count_max"], 600)
        self.assertTrue(lead["payment_gateway"])
        self.assertFalse(lead["customer_accounts"])
        self.assertTrue(lead["guest_checkout"])
        self.assertEqual(lead["timeline_months"], 2)
        self.assertEqual(lead["budget_min"], 50000)
        self.assertEqual(lead["budget_max"], 60000)
        self.assertIsNone(lead["additional_requirements"])

        # Classification
        classification = result["classification"]
        self.assertEqual(classification["classification"], "HOT")
        self.assertGreaterEqual(classification["score"], 70)

        # WhatsApp Action
        whatsapp = result["whatsapp_action"]
        self.assertIsNotNone(whatsapp)
        self.assertEqual(whatsapp["status"], "provider_not_configured")
        self.assertFalse(whatsapp["delivered"])

        # Follow-up
        followup = result["followup"]
        self.assertIsNotNone(followup)
        self.assertIn("500 - 600 products", followup["message"])
        self.assertNotIn("clothing", followup["message"].lower())

        # Persistence verification in SQLite
        persisted_lead = self.db.get_lead_by_call_id(8605274)
        self.assertIsNotNone(persisted_lead)
        self.assertEqual(persisted_lead.classification, "HOT")
        self.assertEqual(persisted_lead.budget_max, 60000)

    @patch("app.intelligence.understand.extract_semantic_lead_data")
    @patch("app.telephony.service.TelephonyService.get_call_data")
    def test_pipeline_with_callback_intent(self, mock_get_call_data, mock_semantic):
        mock_get_call_data.return_value = {
            "id": 8609999,
            "to_number": "+919876543210",
            "from_number": "+918048799598",
            "call_direction": "outbound",
            "call_duration_in_seconds": 15.0,
            "call_status": "completed",
            "interactions": [
                {"interaction_sequence": 1, "user_query": "", "bot_response": "Hi, I'm calling from ElevateBox."},
                {"interaction_sequence": 2, "user_query": "I am driving right now, please call me tomorrow morning.", "bot_response": "Sure, I will schedule that."},
            ],
        }

        mock_semantic.return_value = {
            "business_type": None,
            "payment_gateway": None,
            "customer_accounts": None,
            "guest_checkout": None,
            "additional_requirements": None,
        }

        pipeline = SalesAgentPipeline(db_repo=self.db)
        result = pipeline.process_call(8609999)

        # Callback asserted
        cb = result["callback"]
        self.assertIsNotNone(cb)
        self.assertTrue(cb["intent_detected"])
        self.assertIn("tomorrow morning", cb["raw_request"])
        self.assertIsNotNone(cb["scheduled_time"])

        # Persisted in DB
        callbacks = self.db.get_callbacks_by_call_id(8609999)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(callbacks[0].status, "scheduled")


if __name__ == "__main__":
    unittest.main()
