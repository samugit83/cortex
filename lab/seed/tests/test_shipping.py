import unittest

from shop.billing.money import Money
from shop.billing.shipping import BASE_FEE, shipping_cost


class ShippingTests(unittest.TestCase):
    def test_whole_kilos(self):
        self.assertEqual(shipping_cost("2", "4.50"), Money(299 + 900))

    def test_base_fee_only(self):
        self.assertEqual(shipping_cost("0", "4.50"), BASE_FEE)


if __name__ == "__main__":
    unittest.main()
