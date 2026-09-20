import unittest

from shop.billing.money import Money
from shop.billing.vat import net_from_gross


class VatTests(unittest.TestCase):
    def test_standard_rate(self):
        self.assertEqual(net_from_gross(Money(1220), "22"), Money(1000))


if __name__ == "__main__":
    unittest.main()
