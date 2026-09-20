import unittest

from shop.billing.fx import RATES, convert, to_currency
from shop.billing.money import Money


class FxTests(unittest.TestCase):
    def test_whole_rate(self):
        self.assertEqual(to_currency(Money(100), "JPY"), Money(16100))

    def test_euro_is_unchanged(self):
        self.assertEqual(to_currency(Money(100), "EUR"), Money(100))

    def test_published_rates_are_text(self):
        self.assertTrue(all(isinstance(r, str) for r in RATES.values()))


if __name__ == "__main__":
    unittest.main()
