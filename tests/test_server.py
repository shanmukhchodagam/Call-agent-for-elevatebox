import io
import json
import unittest
from unittest.mock import patch, MagicMock

from app.server import MidCallWebhookHandler


class MockServer:
    pass


class TestMidCallWebhookHandler(unittest.TestCase):
    def _create_handler(self, method: str, path: str, body: dict = None, headers: dict = None):
        if headers is None:
            headers = {}
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        headers["Content-Length"] = str(len(body_bytes))
        headers["Content-Type"] = "application/json"

        rfile = io.BytesIO(body_bytes)
        wfile = io.BytesIO()

        # Build dummy handler instance without running network socket
        handler = MidCallWebhookHandler.__new__(MidCallWebhookHandler)
        handler.rfile = rfile
        handler.wfile = wfile
        handler.headers = headers
        handler.path = path
        handler.command = method
        handler.request_version = "HTTP/1.1"
        handler.close_connection = True

        responses = []

        def mock_send_response(code, message=None):
            responses.append(code)

        handler.send_response = mock_send_response

        response_headers = {}

        def mock_send_header(keyword, value):
            response_headers[keyword] = value

        handler.send_header = mock_send_header
        handler.end_headers = lambda: None

        return handler, responses, response_headers, wfile

    def test_get_health_check(self):
        handler, responses, headers, wfile = self._create_handler("GET", "/")
        handler.do_GET()

        self.assertEqual(responses[0], 200)
        self.assertEqual(headers.get("Content-Type"), "application/json")
        body = json.loads(wfile.getvalue().decode("utf-8"))
        self.assertEqual(body.get("status"), "active")
        self.assertIn("ElevateBox", body.get("service", ""))

    @patch("app.server.DatabaseRepository")
    def test_post_midcall_action_dry_run(self, mock_repo):
        mock_db_instance = MagicMock()
        mock_repo.return_value = mock_db_instance

        payload = {
            "intent": "HOT",
            "context": "Customer asked for portfolio and packages",
            "phone_number": "+919381758441",
            "customer_name": "Shanmukha",
            "dry_run": True,
        }
        handler, responses, headers, wfile = self._create_handler("POST", "/webhook/in-call-action", body=payload)
        handler.do_POST()

        self.assertEqual(responses[0], 200)
        response_body = json.loads(wfile.getvalue().decode("utf-8"))
        self.assertEqual(response_body.get("status"), "success")
        self.assertIn("reply", response_body)
        self.assertIn("message_for_bot", response_body)
        self.assertTrue(mock_db_instance.save_followup.called)

    def test_post_midcall_missing_phone_non_dry_run(self):
        payload = {
            "intent": "HOT",
            "context": "Customer asked for details",
        }
        handler, responses, headers, wfile = self._create_handler("POST", "/webhook/in-call-action", body=payload)
        handler.do_POST()

        self.assertEqual(responses[0], 400)
        response_body = json.loads(wfile.getvalue().decode("utf-8"))
        self.assertEqual(response_body.get("status"), "error")
        self.assertIn("Missing phone_number", response_body.get("error", ""))


if __name__ == "__main__":
    unittest.main()
