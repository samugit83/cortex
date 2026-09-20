import json
import unittest

from shop.orders import load_orders
from shop.plugins.registry import UnknownFormat, available, get_exporter
from tests.support import ORDERS


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.orders = load_orders(ORDERS)

    def test_csv(self):
        lines = get_exporter("csv").export(self.orders).splitlines()
        self.assertEqual(lines[0], "order,date,customer,sku,qty,unit_price,line_total")
        self.assertEqual(lines[1], "A-1001,2026-09-02,Rossi SRL,MUG-001,2,8.50,17.00")

    def test_json(self):
        data = json.loads(get_exporter("json").export(self.orders))
        self.assertEqual(data[0]["total"], "22.20")
        self.assertEqual(data[1]["lines"][0]["sku"], "LMP-001")

    def test_registry(self):
        self.assertTrue({"csv", "json"} <= set(available()))
        with self.assertRaises(UnknownFormat):
            get_exporter("nope")


if __name__ == "__main__":
    unittest.main()
