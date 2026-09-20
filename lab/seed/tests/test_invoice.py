import unittest

from shop.billing.invoice import build_invoice
from shop.billing.money import Money
from shop.cart import load_cart
from shop.catalog import load_catalog
from tests.support import CART, CATALOG


class InvoiceTests(unittest.TestCase):
    def setUp(self):
        self.cart = load_cart(CART)
        self.products = load_catalog(CATALOG)

    def test_totals(self):
        inv = build_invoice(self.cart, self.products, tax_rate="22")
        self.assertEqual(inv.subtotal, Money(2220))
        self.assertEqual(inv.tax, Money(488))
        self.assertEqual(inv.total, Money(2708))

    def test_half_price_discount(self):
        inv = build_invoice(self.cart, self.products, tax_rate="22", discount_pct="50")
        self.assertEqual(inv.discounted, Money(1110))
        self.assertEqual(inv.tax, Money(244))


if __name__ == "__main__":
    unittest.main()
