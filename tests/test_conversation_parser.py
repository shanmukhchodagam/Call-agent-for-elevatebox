import unittest

from app.conversation.parser import ConversationParser


class TestConversationParser(unittest.TestCase):

    def test_parse_interactions(self):
        call_data = {
            "id": 12345,
            "to_number": "+919876543210",
            "from_number": "+918048799598",
            "call_direction": "outbound",
            "call_duration_in_seconds": 45.0,
            "call_status": "completed",
            "interactions": [
                {
                    "interaction_sequence": 1,
                    "user_query": "",
                    "bot_response": "Hi, I am calling from ElevateBox. Is this a good time to talk?",
                },
                {
                    "interaction_sequence": 2,
                    "user_query": "Yes, I am looking for a website.",
                    "bot_response": "What kind of business do you run?",
                },
                {
                    "interaction_sequence": 3,
                    "user_query": "I run a furniture store with about 200 items.",
                    "bot_response": "Got it. Do you need a payment gateway?",
                },
            ],
        }

        ctx = ConversationParser.parse_call_log(call_data)

        self.assertEqual(ctx.call_id, 12345)
        self.assertEqual(ctx.customer_phone, "+919876543210")
        self.assertEqual(ctx.call_status, "completed")
        self.assertEqual(ctx.duration_seconds, 45.0)

        # Ensure only customer statements are in customer_statements
        self.assertEqual(len(ctx.customer_statements), 2)
        self.assertEqual(ctx.customer_statements[0], "Yes, I am looking for a website.")
        self.assertEqual(ctx.customer_statements[1], "I run a furniture store with about 200 items.")

        # Ensure dialogue turns maintain speaker separation
        self.assertEqual(len(ctx.turns), 5)
        self.assertEqual(ctx.turns[0].speaker, "Agent")
        self.assertEqual(ctx.turns[1].speaker, "Customer")

    def test_parse_raw_transcript_with_html_breaks(self):
        raw = (
            "LLM: Hi, I'm calling from ElevateBox.<br/>"
            "User: Hello.<br/>"
            "LLM: Tell me about your requirements.<br/>"
            "User: We need an online store for 500 products.<br/>"
        )

        ctx = ConversationParser.parse_raw_transcript(raw, call_id=999, customer_phone="+919999999999")

        self.assertEqual(ctx.call_id, 999)
        self.assertEqual(ctx.customer_phone, "+919999999999")
        self.assertEqual(len(ctx.customer_statements), 2)
        self.assertIn("Hello.", ctx.customer_statements)
        self.assertIn("We need an online store for 500 products.", ctx.customer_statements)

    def test_ai_interpretation_isolated_from_customer_facts(self):
        # The key Level 4 requirement: AI statement "so you sell clothing" must not become customer statement
        raw = (
            "User: I ran a closing business and products are closed.<br/>"
            "LLM: Okay, so you sell clothing items. About how many products do you have?<br/>"
            "User: Around 500 to 600.<br/>"
        )

        ctx = ConversationParser.parse_raw_transcript(raw)

        # Customer statements must NOT contain "Okay, so you sell clothing items"
        self.assertNotIn("clothing", " ".join(ctx.customer_statements).lower())
        self.assertEqual(len(ctx.customer_statements), 2)
        self.assertEqual(ctx.customer_statements[0], "I ran a closing business and products are closed.")
        self.assertEqual(ctx.customer_statements[1], "Around 500 to 600.")


if __name__ == "__main__":
    unittest.main()
