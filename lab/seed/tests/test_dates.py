import unittest
from datetime import date

from shop.util.dates import add_business_days, days_between, format_date, parse_date


class DateTests(unittest.TestCase):
    def test_parse_iso(self):
        self.assertEqual(parse_date("2026-09-19"), date(2026, 9, 19))

    def test_format(self):
        self.assertEqual(format_date(date(2026, 9, 4)), "04/09/2026")
        self.assertEqual(format_date(date(2026, 9, 4), "iso"), "2026-09-04")

    def test_business_days_within_the_week(self):
        self.assertEqual(add_business_days(date(2026, 9, 14), 1), date(2026, 9, 15))   # Mon -> Tue

    def test_days_between(self):
        self.assertEqual(days_between(date(2026, 9, 1), date(2026, 9, 19)), 18)


if __name__ == "__main__":
    unittest.main()
