import unittest

from shop.billing.money import Money
from shop.billing.rates import parse_rate, percent_of, scale, split, times


class RateTests(unittest.TestCase):
    def test_parse_rate(self):
        self.assertEqual(parse_rate("22"), (22, 1))
        self.assertEqual(parse_rate("0.5"), (5, 10))

    def test_percent_of(self):
        self.assertEqual(percent_of(Money(1000), "22"), Money(220))
        self.assertEqual(percent_of(Money(-1000), "10"), Money(-100))

    def test_times_and_scale(self):
        self.assertEqual(times(Money(1000), "1.5"), Money(1500))
        self.assertEqual(scale(Money(1000), 1, 4), Money(250))

    def test_split_adds_up(self):
        self.assertEqual(split(Money(100), 3), [Money(34), Money(33), Money(33)])
        self.assertEqual(Money.total(split(Money(1001), 4)), Money(1001))


if __name__ == "__main__":
    unittest.main()
