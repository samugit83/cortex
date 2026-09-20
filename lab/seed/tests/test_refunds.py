import unittest

from shop.billing.money import Money
from shop.billing.refunds import prorated_refund


class RefundTests(unittest.TestCase):
    def test_a_third_used(self):
        self.assertEqual(prorated_refund(Money(3000), 10, 30), Money(2000))

    def test_unused(self):
        self.assertEqual(prorated_refund(Money(3000), 0, 30), Money(3000))


if __name__ == "__main__":
    unittest.main()
