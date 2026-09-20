import unittest

from shop.billing.discount import apply_discount
from shop.billing.money import Money


class DiscountTests(unittest.TestCase):
    def test_ten_percent(self):
        self.assertEqual(apply_discount(Money(2000), "10"), Money(1800))

    def test_no_discount(self):
        self.assertEqual(apply_discount(Money(1234), "0"), Money(1234))


if __name__ == "__main__":
    unittest.main()
