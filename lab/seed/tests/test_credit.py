import unittest

from shop.billing.credit import return_credit
from shop.billing.money import Money


class ReturnCreditTests(unittest.TestCase):
    def test_ninety_percent(self):
        self.assertEqual(return_credit(Money(2000)), Money(1800))


if __name__ == "__main__":
    unittest.main()
