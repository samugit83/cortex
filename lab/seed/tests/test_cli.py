import unittest

from tests.support import CART, ORDERS, run_cli


class ListTests(unittest.TestCase):
    def test_lists_every_product(self):
        code, out, _ = run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("Ceramic mug", out)
        self.assertIn("Fountain pen", out)
        self.assertIn("SKU", out.splitlines()[0])

    def test_sort_by_name(self):
        code, out, _ = run_cli("list", "--sort", "name")
        self.assertEqual(code, 0)
        self.assertLess(out.index("Canvas tote bag"), out.index("Travel mug"))


class ShowTests(unittest.TestCase):
    def test_show_in_stock(self):
        code, out, _ = run_cli("show", "MUG-001")
        self.assertEqual(code, 0)
        self.assertIn("Ceramic mug", out)
        self.assertIn("€8.50", out)
        self.assertIn("24 left", out)

    def test_unknown_product_fails(self):
        code, _, _ = run_cli("show", "NOPE-000")
        self.assertNotEqual(code, 0)


class CartTotalTests(unittest.TestCase):
    def test_total(self):
        code, out, _ = run_cli("cart", "total", CART)
        self.assertEqual(code, 0)
        self.assertIn("€22.20", out)


class InvoiceTests(unittest.TestCase):
    def test_invoice(self):
        code, out, _ = run_cli("invoice", CART, "--tax", "22")
        self.assertEqual(code, 0)
        self.assertIn("Total: €27.08", out)


class ExportAndReportTests(unittest.TestCase):
    def test_export_csv(self):
        code, out, _ = run_cli("export", ORDERS, "--format", "csv")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("order,date,customer"))

    def test_export_unknown_format(self):
        code, _, err = run_cli("export", ORDERS, "--format", "nope")
        self.assertEqual(code, 2)
        self.assertIn("unknown format", err)

    def test_report(self):
        code, out, _ = run_cli("report", ORDERS)
        self.assertEqual(code, 0)
        self.assertIn("A-1002", out)


if __name__ == "__main__":
    unittest.main()
