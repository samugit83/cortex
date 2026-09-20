import unittest

from shop.billing.loyalty import points_value
from shop.billing.money import Money


class LoyaltyTests(unittest.TestCase):
    def test_one_cent_points(self):
        self.assertEqual(points_value(500, "1"), Money(500))


if __name__ == "__main__":
    unittest.main()
