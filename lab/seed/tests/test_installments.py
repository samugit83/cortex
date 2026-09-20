import unittest

from shop.billing.installments import installment_plan
from shop.billing.money import Money


class InstallmentTests(unittest.TestCase):
    def test_even_split_without_fee(self):
        self.assertEqual(installment_plan(Money(9000), 3), [Money(3000)] * 3)


if __name__ == "__main__":
    unittest.main()
