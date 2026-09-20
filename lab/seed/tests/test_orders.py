import unittest
from datetime import date

from shop.billing.money import Money
from shop.orders import load_orders
from tests.support import ORDERS


class OrderTests(unittest.TestCase):
    def test_load(self):
        orders = load_orders(ORDERS)
        self.assertEqual([o.id for o in orders], ["A-1001", "A-1002"])
        self.assertEqual(orders[0].date, date(2026, 9, 2))
        self.assertEqual(orders[0].total, Money(2220))
        self.assertEqual(orders[0].item_count, 3)


if __name__ == "__main__":
    unittest.main()
