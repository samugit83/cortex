import unittest

from shop.billing.money import Money


class ParseTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(Money.parse("12.50"), Money(1250))
        self.assertEqual(Money.parse("7"), Money(700))
        self.assertEqual(Money.parse("0.5"), Money(50))
        self.assertEqual(Money.parse("-3.05"), Money(-305))
        with self.assertRaises(ValueError):
            Money.parse("1.234")

    def test_integer_cents_only(self):
        with self.assertRaises(TypeError):
            Money(12.5)


class ArithmeticTests(unittest.TestCase):
    def test_add_sub_mul(self):
        self.assertEqual(Money(150) + Money(250), Money(400))
        self.assertEqual(Money(150) - Money(250), Money(-100))
        self.assertEqual(Money(150) * 3, Money(450))
        with self.assertRaises(TypeError):
            Money(150) * 1.5

    def test_total(self):
        self.assertEqual(Money.total([Money(1), Money(2), Money(3)]), Money(6))

    def test_str(self):
        self.assertEqual(str(Money(1250)), "12.50")
        self.assertEqual(str(Money(-5)), "-0.05")


if __name__ == "__main__":
    unittest.main()
