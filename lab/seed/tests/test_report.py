import unittest

from shop.orders import load_orders
from shop.report import sales_report
from tests.support import ORDERS


class SalesReportTests(unittest.TestCase):
    def setUp(self):
        self.report = sales_report(load_orders(ORDERS))

    def test_headers(self):
        for header in ("Date", "Order", "Customer", "Items", "Total"):
            self.assertIn(header, self.report.splitlines()[0])

    def test_one_row_per_order(self):
        self.assertIn("A-1001", self.report)
        self.assertIn("A-1002", self.report)
        self.assertIn("€22.20", self.report)


if __name__ == "__main__":
    unittest.main()
