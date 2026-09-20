import unittest

from shop.catalog import find, in_category, load_catalog, search, sort_products
from tests.support import CATALOG


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.products = load_catalog(CATALOG)

    def test_load(self):
        self.assertEqual(len(self.products), 11)
        self.assertEqual(find(self.products, "MUG-001").name, "Ceramic mug")
        self.assertIsNone(find(self.products, "NOPE-000"))

    def test_search_by_name(self):
        self.assertEqual({p.sku for p in search(self.products, "mug")}, {"MUG-001", "MUG-002"})

    def test_sort_by_price(self):
        prices = [p.price for p in sort_products(self.products, "price")]
        self.assertEqual(prices, sorted(prices))

    def test_sort_by_name(self):
        names = [p.name.lower() for p in sort_products(self.products, "name")]
        self.assertEqual(names, sorted(names))

    def test_category(self):
        self.assertEqual({p.sku for p in in_category(self.products, "food")}, {"TEA-001", "TEA-002"})


if __name__ == "__main__":
    unittest.main()
