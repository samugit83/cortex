"""JSON: the orders as an array, amounts as decimal strings."""
import json

from .base import Exporter


class JsonExporter(Exporter):
    name = "json"
    extension = "json"

    def export(self, orders) -> str:
        data = [{
            "id": o.id,
            "date": o.date.isoformat(),
            "customer": o.customer,
            "status": o.status,
            "total": str(o.total),
            "lines": [{"sku": l.sku, "name": l.name, "qty": l.qty,
                       "unit_price": str(l.unit_price), "total": str(l.total)} for l in o.lines],
        } for o in orders]
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
