import unittest
import os

from app.database import (
    DatabaseRepository,
    LeadRecord,
    CallbackRecord,
    FollowupRecord,
)

TEST_DB = "test_sales_repo.db"


class TestDatabaseRepository(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass
        self.repo = DatabaseRepository(db_path=TEST_DB)

    def tearDown(self):
        del self.repo
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass

    def test_save_and_get_lead(self):
        lead = LeadRecord(
            call_id=101,
            phone_number="+919876543210",
            business_type="clothing",
            product_count_min=100,
            product_count_max=200,
            payment_gateway=True,
            customer_accounts=False,
            guest_checkout=True,
            timeline_months=3,
            budget_min=40000,
            budget_max=50000,
            additional_requirements="Custom size chart",
            classification="HOT",
            score=85,
            reasons=["Strong budget", "Defined timeline"],
            transcript="Agent: Hi\nCustomer: Hello",
        )

        self.repo.save_lead(lead)
        fetched = self.repo.get_lead_by_call_id(101)

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.call_id, 101)
        self.assertEqual(fetched.phone_number, "+919876543210")
        self.assertEqual(fetched.business_type, "clothing")
        self.assertEqual(fetched.product_count_min, 100)
        self.assertEqual(fetched.product_count_max, 200)
        self.assertTrue(fetched.payment_gateway)
        self.assertFalse(fetched.customer_accounts)
        self.assertTrue(fetched.guest_checkout)
        self.assertEqual(fetched.timeline_months, 3)
        self.assertEqual(fetched.budget_min, 40000)
        self.assertEqual(fetched.budget_max, 50000)
        self.assertEqual(fetched.classification, "HOT")
        self.assertEqual(fetched.score, 85)
        self.assertEqual(len(fetched.reasons), 2)

    def test_lead_upsert(self):
        lead = LeadRecord(
            call_id=102,
            phone_number="+919876543210",
            business_type=None,
            product_count_min=50,
            product_count_max=50,
            payment_gateway=None,
            customer_accounts=None,
            guest_checkout=None,
            timeline_months=None,
            budget_min=None,
            budget_max=None,
            additional_requirements=None,
            classification="COLD",
            score=10,
        )
        self.repo.save_lead(lead)

        # Update with new data
        lead.business_type = "electronics"
        lead.classification = "WARM"
        lead.score = 55
        self.repo.save_lead(lead)

        fetched = self.repo.get_lead_by_call_id(102)
        self.assertEqual(fetched.business_type, "electronics")
        self.assertEqual(fetched.classification, "WARM")
        self.assertEqual(fetched.score, 55)

    def test_callbacks_persistence(self):
        cb = CallbackRecord(
            call_id=103,
            phone_number="+919876543210",
            raw_request="Call me tomorrow morning",
            scheduled_time="2026-10-01T10:00:00+05:30",
            timezone="Asia/Kolkata",
            status="scheduled",
        )
        self.repo.save_callback(cb)

        callbacks = self.repo.get_callbacks_by_call_id(103)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(callbacks[0].raw_request, "Call me tomorrow morning")
        self.assertEqual(callbacks[0].scheduled_time, "2026-10-01T10:00:00+05:30")

    def test_followups_persistence(self):
        fu = FollowupRecord(
            call_id=104,
            phone_number="+919876543210",
            message="Hi, thank you for speaking with us.",
            channel="whatsapp",
            status="delivered",
        )
        self.repo.save_followup(fu)

        followups = self.repo.get_followups_by_call_id(104)
        self.assertEqual(len(followups), 1)
        self.assertEqual(followups[0].message, "Hi, thank you for speaking with us.")
        self.assertEqual(followups[0].status, "delivered")

    def test_list_leads(self):
        for i in range(3):
            self.repo.save_lead(
                LeadRecord(
                    call_id=200 + i,
                    phone_number=f"+91980000000{i}",
                    business_type="books",
                    product_count_min=10,
                    product_count_max=20,
                    payment_gateway=True,
                    customer_accounts=True,
                    guest_checkout=False,
                    timeline_months=1,
                    budget_min=10000,
                    budget_max=15000,
                    additional_requirements=None,
                    classification="WARM",
                    score=50,
                )
            )

        leads = self.repo.list_leads(limit=10)
        self.assertEqual(len(leads), 3)


if __name__ == "__main__":
    unittest.main()
