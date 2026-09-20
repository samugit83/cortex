"""CSV: one row per order line."""
import csv
import io

from .base import Exporter


class CsvExporter(Exporter):
    name = "csv"
    extension = "csv"

    def export(self, orders) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["order", "date", "customer", "sku", "qty", "unit_price", "line_total"])
        for o in orders:
            for line in o.lines:
                w.writerow([o.id, o.date.isoformat(), o.customer, line.sku, line.qty,
                            str(line.unit_price), str(line.total)])
        return buf.getvalue()
