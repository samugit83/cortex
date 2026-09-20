import unittest

from shop.billing.money import Money
from shop.cart import Cart, load_cart
from shop.catalog import load_catalog
from tests.support import CART, CATALOG


class CartTests(unittest.TestCase):
    def test_add_and_count(self):
        cart = Cart()
        cart.add("MUG-001", 2)
        cart.add("MUG-001")
        self.assertEqual(cart.lines, {"MUG-001": 3})
        self.assertEqual(cart.count(), 3)

    def test_remove_some(self):
        cart = Cart({"MUG-001": 3})
        cart.remove("MUG-001", 1)
        self.assertEqual(cart.lines, {"MUG-001": 2})

    def test_add_needs_a_positive_quantity(self):
        with self.assertRaises(ValueError):
            Cart().add("MUG-001", 0)

    def test_total(self):
        self.assertEqual(load_cart(CART).total(load_catalog(CATALOG)), Money(2220))


if __name__ == "__main__":
    unittest.main()
