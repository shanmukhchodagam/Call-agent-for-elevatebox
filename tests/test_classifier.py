import unittest

from app.intelligence.classifier import (
    LeadClassifier,
    ScoringWeights,
    classify_lead,
)


class TestClassifier(unittest.TestCase):

    def setUp(self):
        self.classifier = LeadClassifier()

    def test_hot_lead(self):
        hot_lead = {
            "business_type": None,
            "product_count_min": 500,
            "product_count_max": 600,
            "payment_gateway": True,
            "customer_accounts": False,
            "guest_checkout": True,
            "timeline_months": 2,
            "budget_min": 50000,
            "budget_max": 60000,
            "additional_requirements": None,
        }

        result = self.classifier.classify(hot_lead)

        self.assertEqual(result.classification, "HOT")
        self.assertEqual(result.state, "HOT")
        self.assertEqual(result.next_action, "fire_whatsapp_midcall")
        self.assertGreaterEqual(result.score, 70)
        self.assertEqual(len(result.reasons), 5)
        self.assertTrue(any("budget" in r.lower() for r in result.reasons))
        self.assertTrue(any("timeline" in r.lower() for r in result.reasons))
        self.assertTrue(any("catalog" in r.lower() or "product" in r.lower() for r in result.reasons))

    def test_warm_lead(self):
        warm_lead = {
            "business_type": "handicrafts",
            "product_count_min": 50,
            "product_count_max": 100,
            "payment_gateway": True,
            "customer_accounts": None,
            "guest_checkout": None,
            "timeline_months": 4,
            "budget_min": 25000,
            "budget_max": 30000,
            "additional_requirements": None,
        }

        result = self.classifier.classify(warm_lead)

        self.assertEqual(result.classification, "WARM")
        self.assertEqual(result.state, "WARM")
        self.assertEqual(result.next_action, "capture_barrier_and_schedule_callback")
        self.assertGreaterEqual(result.score, 40)
        self.assertLess(result.score, 70)

    def test_cold_lead(self):
        cold_lead = {
            "business_type": None,
            "product_count_min": None,
            "product_count_max": None,
            "payment_gateway": None,
            "customer_accounts": None,
            "guest_checkout": None,
            "timeline_months": None,
            "budget_min": None,
            "budget_max": None,
            "additional_requirements": None,
        }

        result = self.classifier.classify(cold_lead)

        self.assertEqual(result.classification, "COLD")
        self.assertEqual(result.state, "COLD")
        self.assertEqual(result.next_action, "log_and_send_overview")
        self.assertEqual(result.score, 0)
        self.assertTrue(len(result.reasons) > 0)

    def test_indirect_barrier_brother_decides(self):
        # "my brother handles this" -> WARM, captures barrier, schedules callback
        conversation = "User: I like it, but my brother handles this business and makes the final call."
        sparse_lead = {
            "business_type": None,
            "product_count_min": None,
            "product_count_max": None,
            "payment_gateway": None,
            "customer_accounts": None,
            "guest_checkout": None,
            "timeline_months": None,
            "budget_min": None,
            "budget_max": None,
            "additional_requirements": None,
        }

        result = self.classifier.classify(sparse_lead, conversation_text=conversation)

        self.assertEqual(result.classification, "WARM")
        self.assertEqual(result.state, "WARM")
        self.assertEqual(result.next_action, "capture_barrier_and_schedule_callback")
        self.assertIsNotNone(result.barrier)
        self.assertIn("brother", result.barrier.lower())

    def test_indirect_buying_intent_send_details(self):
        # "send me the details on whatsapp" -> HOT buying intent
        conversation = "User: How soon can you start? Please send me the details on WhatsApp."
        lead = {
            "business_type": "retail",
            "product_count_min": 50,
            "product_count_max": 50,
            "payment_gateway": True,
            "customer_accounts": False,
            "guest_checkout": True,
            "timeline_months": 1,
            "budget_min": 30000,
            "budget_max": 30000,
            "additional_requirements": None,
        }

        result = self.classifier.classify(lead, conversation_text=conversation)

        self.assertEqual(result.classification, "HOT")
        self.assertEqual(result.state, "HOT")
        self.assertEqual(result.next_action, "fire_whatsapp_midcall")
        self.assertTrue(any("indirect" in r.lower() or "whatsapp" in r.lower() for r in result.reasons))

    def test_custom_scoring_weights(self):
        custom_weights = ScoringWeights(
            hot_threshold=80,
            budget_high_points=40,
            timeline_urgent_points=40,
        )
        classifier = LeadClassifier(weights=custom_weights)

        lead = {
            "business_type": None,
            "product_count_min": None,
            "product_count_max": None,
            "payment_gateway": None,
            "customer_accounts": None,
            "guest_checkout": None,
            "timeline_months": 1,
            "budget_min": 60000,
            "budget_max": 60000,
            "additional_requirements": None,
        }

        res = classifier.classify(lead)
        self.assertEqual(res.score, 80)
        self.assertEqual(res.classification, "HOT")

    def test_classify_lead_helper(self):
        lead = {"budget_max": 100000, "timeline_months": 1}
        res_dict = classify_lead(lead)
        self.assertIn("classification", res_dict)
        self.assertIn("score", res_dict)
        self.assertIn("reasons", res_dict)
        self.assertIn("next_action", res_dict)


if __name__ == "__main__":
    unittest.main()
