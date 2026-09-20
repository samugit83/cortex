import unittest

from shop.billing.money import Money
from shop.billing.tax import tax_for


class TaxTests(unittest.TestCase):
    def test_standard_rate(self):
        self.assertEqual(tax_for(Money(1000), "22"), Money(220))

    def test_reduced_rate(self):
        self.assertEqual(tax_for(Money(500), "10"), Money(50))

    def test_zero_amount(self):
        self.assertEqual(tax_for(Money(0), "22"), Money(0))


if __name__ == "__main__":
    unittest.main()
