import unittest
from datetime import date, timezone

from shop import clock


class ClockTests(unittest.TestCase):
    def tearDown(self):
        clock.freeze(None)

    def test_now_is_utc_aware(self):
        self.assertEqual(clock.now().tzinfo, timezone.utc)

    def test_freeze(self):
        clock.freeze("2031-01-15T09:30:00Z")
        self.assertEqual(clock.today(), date(2031, 1, 15))
        self.assertEqual(clock.now().hour, 9)


if __name__ == "__main__":
    unittest.main()
