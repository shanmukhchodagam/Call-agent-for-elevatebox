import unittest
from datetime import datetime
import zoneinfo

from app.scheduling.callback import (
    detect_and_parse_callback,
    parse_callback_time,
    CallbackSchedule,
)


class TestCallback(unittest.TestCase):

    def setUp(self):
        self.tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        # Fixed base time: Wednesday 2026-09-30 11:30:00 AM IST
        self.base_time = datetime(2026, 9, 30, 11, 30, 0, tzinfo=self.tz)

    def test_tomorrow_morning(self):
        cb = detect_and_parse_callback(
            ["I am in a meeting, can you call me tomorrow morning?"],
            base_time=self.base_time,
            tz_str="Asia/Kolkata",
        )
        self.assertIsNotNone(cb)
        self.assertTrue(cb.intent_detected)
        self.assertEqual(cb.scheduled_time.year, 2026)
        self.assertEqual(cb.scheduled_time.month, 10)
        self.assertEqual(cb.scheduled_time.day, 1)
        self.assertEqual(cb.scheduled_time.hour, 10)
        self.assertEqual(cb.scheduled_time.minute, 0)

    def test_tomorrow_afternoon(self):
        cb = detect_and_parse_callback(
            ["Please call back tomorrow afternoon."],
            base_time=self.base_time,
            tz_str="Asia/Kolkata",
        )
        self.assertIsNotNone(cb)
        self.assertEqual(cb.scheduled_time.hour, 14)

    def test_tomorrow_evening(self):
        cb = detect_and_parse_callback(
            ["Call me tomorrow evening please."],
            base_time=self.base_time,
            tz_str="Asia/Kolkata",
        )
        self.assertIsNotNone(cb)
        self.assertEqual(cb.scheduled_time.hour, 18)

    def test_tomorrow_at_4_pm(self):
        cb = detect_and_parse_callback(
            ["Call me tomorrow at 4 pm"],
            base_time=self.base_time,
            tz_str="Asia/Kolkata",
        )
        self.assertIsNotNone(cb)
        self.assertEqual(cb.scheduled_time.day, 1)
        self.assertEqual(cb.scheduled_time.hour, 16)
        self.assertEqual(cb.scheduled_time.minute, 0)

    def test_relative_hours(self):
        cb = detect_and_parse_callback(
            ["I am driving right now, please call in 2 hours"],
            base_time=self.base_time,
            tz_str="Asia/Kolkata",
        )
        self.assertIsNotNone(cb)
        self.assertEqual(cb.scheduled_time.hour, 13)
        self.assertEqual(cb.scheduled_time.minute, 30)

    def test_relative_minutes(self):
        cb = detect_and_parse_callback(
            ["Reach me in 30 minutes"],
            base_time=self.base_time,
            tz_str="Asia/Kolkata",
        )
        self.assertIsNotNone(cb)
        self.assertEqual(cb.scheduled_time.hour, 12)
        self.assertEqual(cb.scheduled_time.minute, 0)

    def test_no_callback_intent(self):
        cb = detect_and_parse_callback(
            [
                "Yes, I want an e-commerce website.",
                "Around 500 to 600 products.",
                "My budget is 50 thousand.",
            ],
            base_time=self.base_time,
        )
        self.assertIsNone(cb)


if __name__ == "__main__":
    unittest.main()
