import unittest
from unittest.mock import patch, MagicMock

from app.actions.whatsapp import WhatsAppService, send_whatsapp_message


class TestWhatsAppAction(unittest.TestCase):

    def test_provider_not_configured_returns_clean_fallback(self):
        # Service with no credentials
        svc = WhatsAppService(api_key=None, phone_number_id=None)
        self.assertFalse(svc.is_configured())

        res = svc.send_message(to_number="+919381758441", message="Hello!")

        self.assertEqual(res["status"], "provider_not_configured")
        self.assertFalse(res["delivered"])
        self.assertEqual(res["recipient"], "+919381758441")
        self.assertIn("error", res)

    @patch("requests.post")
    def test_provider_configured_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.HBgL..."}],
        }
        mock_post.return_value = mock_resp

        svc = WhatsAppService(api_key="fake_key", phone_number_id="123456")
        self.assertTrue(svc.is_configured())

        res = svc.send_message(to_number="+919381758441", message="Hello!")

        self.assertEqual(res["status"], "delivered")
        self.assertTrue(res["delivered"])
        self.assertEqual(res["message_id"], "wamid.HBgL...")

    @patch("requests.post")
    def test_provider_delivery_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        svc = WhatsAppService(api_key="bad_key", phone_number_id="123456")
        res = svc.send_message(to_number="+919381758441", message="Hello!")

        self.assertEqual(res["status"], "delivery_failed")
        self.assertFalse(res["delivered"])
        self.assertEqual(res["status_code"], 401)


if __name__ == "__main__":
    unittest.main()
