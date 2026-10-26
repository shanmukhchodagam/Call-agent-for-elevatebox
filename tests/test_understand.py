import unittest
from unittest.mock import patch

from app.intelligence.understand import (
    extract_product_count,
    extract_budget,
    extract_timeline,
    extract_lead_data,
    empty_lead,
)


class TestUnderstand(unittest.TestCase):

    def test_product_count_ranges(self):
        # Explicit ranges
        self.assertEqual(extract_product_count("Around 500 to 600."), (500, 600))
        self.assertEqual(extract_product_count("We have 500-600 products."), (500, 600))
        self.assertEqual(extract_product_count("between 100 and 200 items"), (100, 200))
        self.assertEqual(extract_product_count("about 300 to 400 skus"), (300, 400))

    def test_product_count_single_values(self):
        self.assertEqual(extract_product_count("Around 500 items"), (500, 500))
        self.assertEqual(extract_product_count("I have about 250 products"), (250, 250))
        self.assertEqual(extract_product_count("around 100"), (100, 100))

    def test_product_count_word_numbers(self):
        self.assertEqual(extract_product_count("around five hundred products"), (500, 500))
        self.assertEqual(extract_product_count("about one thousand items"), (1000, 1000))

    def test_product_count_missing(self):
        self.assertEqual(extract_product_count("We sell handmade crafts online."), (None, None))
        self.assertEqual(extract_product_count(""), (None, None))

    def test_budget_thousand_ranges(self):
        self.assertEqual(extract_budget("50 to 60 thousand"), (50000, 60000))
        self.assertEqual(extract_budget("Around 50-60 thousand rupees"), (50000, 60000))
        self.assertEqual(extract_budget("50 thousand"), (50000, 50000))

    def test_budget_k_expressions(self):
        self.assertEqual(extract_budget("50k to 60k"), (50000, 60000))
        self.assertEqual(extract_budget("50-60k"), (50000, 60000))
        self.assertEqual(extract_budget("around 50k"), (50000, 50000))

    def test_budget_lakh_expressions(self):
        self.assertEqual(extract_budget("1 to 2 lakhs"), (100000, 200000))
        self.assertEqual(extract_budget("around 1 lakh"), (100000, 100000))

    def test_budget_currency_and_digits(self):
        self.assertEqual(extract_budget("Rs. 50,000 to Rs. 60,000"), (50000, 60000))
        self.assertEqual(extract_budget("50000 to 60000"), (50000, 60000))
        self.assertEqual(extract_budget("Rs. 50,000"), (50000, 50000))

    def test_budget_missing(self):
        self.assertEqual(extract_budget("I haven't thought about cost yet."), (None, None))
        self.assertEqual(extract_budget(""), (None, None))

    def test_timeline_months(self):
        self.assertEqual(extract_timeline("In another 2 months."), 2)
        self.assertEqual(extract_timeline("within 3 months"), 3)
        self.assertEqual(extract_timeline("in 6 months"), 6)
        self.assertEqual(extract_timeline("two months"), 2)
        self.assertEqual(extract_timeline("three months"), 3)
        self.assertEqual(extract_timeline("a month"), 1)

    def test_timeline_weeks(self):
        self.assertEqual(extract_timeline("in 8 weeks"), 2)
        self.assertEqual(extract_timeline("within 4 weeks"), 1)

    def test_timeline_missing(self):
        self.assertIsNone(extract_timeline("Whenever it is ready, no hurry."))
        self.assertIsNone(extract_timeline(""))

    @patch("app.intelligence.understand.extract_semantic_lead_data")
    def test_combined_extraction_with_mocked_semantic(self, mock_semantic):
        mock_semantic.return_value = {
            "business_type": None,
            "payment_gateway": True,
            "customer_accounts": False,
            "guest_checkout": True,
            "additional_requirements": None,
            "inferred_business_type": "clothing (unconfirmed)",
        }

        conversation = """
        LLM: About how many products do you have?
        User: Around 500 to 600.
        LLM: When do you want the website ready?
        User: In another 2 months.
        LLM: What is your budget?
        User: 50 to 60 thousand.
        """

        lead = extract_lead_data(conversation)

        self.assertEqual(lead["product_count_min"], 500)
        self.assertEqual(lead["product_count_max"], 600)
        self.assertEqual(lead["timeline_months"], 2)
        self.assertEqual(lead["budget_min"], 50000)
        self.assertEqual(lead["budget_max"], 60000)
        self.assertIsNone(lead["business_type"])
        self.assertTrue(lead["payment_gateway"])
        self.assertFalse(lead["customer_accounts"])
        self.assertTrue(lead["guest_checkout"])
        self.assertIsNone(lead["additional_requirements"])
        self.assertEqual(lead["inferred_business_type"], "clothing (unconfirmed)")


if __name__ == "__main__":
    unittest.main()
