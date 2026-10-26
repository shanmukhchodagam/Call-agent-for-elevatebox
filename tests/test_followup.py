import unittest

from app.followup.service import FollowupService


class TestFollowup(unittest.TestCase):

    def test_generate_message_with_full_lead(self):
        lead = {
            "business_type": "handicrafts",
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

        msg = FollowupService.generate_message(lead=lead, recipient_name="Ramesh")

        self.assertIn("Hi Ramesh,", msg)
        self.assertIn("handicrafts business", msg)
        self.assertIn("500 - 600 products", msg)
        self.assertIn("payment gateway integration", msg)
        self.assertIn("guest checkout without forced customer accounts", msg)
        self.assertIn("2-month target timeline", msg)
        self.assertIn("Rs. 50,000 - Rs. 60,000", msg)
        # Section 06 checks
        self.assertIn("reach me at", msg)
        self.assertIn("architecture", msg.lower())

    def test_generate_message_without_invented_facts(self):
        # Key requirement: business_type is None -> do not invent 'clothing'
        lead = {
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

        msg = FollowupService.generate_message(lead=lead)

        self.assertNotIn("clothing", msg.lower())
        self.assertIn("an e-commerce website", msg)
        self.assertIn("500 - 600 products", msg)

    def test_generate_message_sparse_lead(self):
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

        msg = FollowupService.generate_message(lead=sparse_lead)

        self.assertIn("speak with ElevateBox", msg)
        self.assertIn("Our engineering team will review your requirements", msg)

    def test_dispatch_followup_structure(self):
        lead = {"product_count_min": 100, "budget_max": 50000}
        res = FollowupService.dispatch_followup(
            to_number="+919876543210",
            lead=lead,
            channel="whatsapp",
        )

        self.assertEqual(res["recipient"], "+919876543210")
        self.assertEqual(res["channel"], "whatsapp")
        self.assertIn("message", res)
        self.assertIn("status", res)
        self.assertIn("timestamp", res)


if __name__ == "__main__":
    unittest.main()
