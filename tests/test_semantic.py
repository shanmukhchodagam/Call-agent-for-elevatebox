import unittest
from unittest.mock import patch, MagicMock

from app.intelligence.semantic import (
    extract_semantic_lead_data,
    empty_semantic_lead,
)


class TestSemantic(unittest.TestCase):

    def test_empty_semantic_lead(self):
        lead = empty_semantic_lead()
        self.assertIsNone(lead["business_type"])
        self.assertIsNone(lead["payment_gateway"])
        self.assertIsNone(lead["customer_accounts"])
        self.assertIsNone(lead["guest_checkout"])
        self.assertIsNone(lead["additional_requirements"])

    @patch("google.genai.Client")
    def test_mocked_gemini_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.text = """
        {
          "business_type": null,
          "payment_gateway": true,
          "customer_accounts": false,
          "guest_checkout": true,
          "additional_requirements": null,
          "inferred_business_type": "clothing (unconfirmed)"
        }
        """
        mock_client.models.generate_content.return_value = mock_resp

        result = extract_semantic_lead_data(
            conversation="User: I ran a closing business.\nLLM: Okay, so you sell clothing items.",
            customer_statements=["I ran a closing business."],
        )

        self.assertIsNone(result["business_type"])
        self.assertTrue(result["payment_gateway"])
        self.assertFalse(result["customer_accounts"])
        self.assertTrue(result["guest_checkout"])
        self.assertIsNone(result["additional_requirements"])
        self.assertEqual(result["inferred_business_type"], "clothing (unconfirmed)")

    @patch("google.genai.Client")
    def test_mocked_gemini_with_markdown_fences(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.text = """```json
        {
          "business_type": "furniture",
          "payment_gateway": true,
          "customer_accounts": true,
          "guest_checkout": false,
          "additional_requirements": "3D room preview"
        }
        ```"""
        mock_client.models.generate_content.return_value = mock_resp

        result = extract_semantic_lead_data("Conversation text")

        self.assertEqual(result["business_type"], "furniture")
        self.assertTrue(result["payment_gateway"])
        self.assertTrue(result["customer_accounts"])
        self.assertFalse(result["guest_checkout"])
        self.assertEqual(result["additional_requirements"], "3D room preview")

    @patch("google.genai.Client")
    def test_gemini_invalid_json_fallback(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.text = "Sorry, I cannot process this."
        mock_client.models.generate_content.return_value = mock_resp

        result = extract_semantic_lead_data("Conversation text")

        # Must gracefully return empty semantic lead without crashing
        self.assertEqual(result, empty_semantic_lead())

    @patch("google.genai.Client")
    def test_gemini_api_exception_fallback(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = RuntimeError("API connection timeout")

        result = extract_semantic_lead_data("Conversation text", max_retries=0)

        # Must gracefully return empty semantic lead
        self.assertEqual(result, empty_semantic_lead())


if __name__ == "__main__":
    unittest.main()
