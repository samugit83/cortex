import unittest

from shop.billing.money import Money
from shop.billing.pricing import price_per_kg


class PricePerKgTests(unittest.TestCase):
    def test_one_kilo_pack(self):
        self.assertEqual(price_per_kg(Money(1000), 1000), Money(1000))

    def test_half_kilo_pack(self):
        self.assertEqual(price_per_kg(Money(2000), 500), Money(4000))


if __name__ == "__main__":
    unittest.main()
