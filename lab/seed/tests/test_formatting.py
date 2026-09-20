import unittest

from shop.billing.money import Money
from shop.formatting import format_money, format_table


class FormatMoneyTests(unittest.TestCase):
    def test_euro(self):
        self.assertEqual(format_money(Money(1250)), "€12.50")

    def test_negative(self):
        self.assertEqual(format_money(Money(-500)), "-€5.00")

    def test_other_currency(self):
        self.assertEqual(format_money(Money(399), "USD"), "$3.99")


class FormatTableTests(unittest.TestCase):
    def test_columns_line_up(self):
        out = format_table(["A", "Long header"], [["x", "1"], ["yyyy", "22"]]).splitlines()
        self.assertEqual(out[0], "A     Long header")
        self.assertEqual(out[1], "----  -----------")
        self.assertEqual(out[3], "yyyy  22")


if __name__ == "__main__":
    unittest.main()
