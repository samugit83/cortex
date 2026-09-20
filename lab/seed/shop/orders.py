"""Orders, as exported by the shop front-end."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

from .billing.money import Money


@dataclass
class OrderLine:
    sku: str
    name: str
    qty: int
    unit_price: Money

    @property
    def total(self) -> Money:
        return self.unit_price * self.qty


@dataclass
class Order:
    id: str
    date: date
    customer: str
    lines: list[OrderLine] = field(default_factory=list)
    status: str = "paid"

    @property
    def total(self) -> Money:
        return Money.total(line.total for line in self.lines)

    @property
    def item_count(self) -> int:
        return sum(line.qty for line in self.lines)


def order_from_dict(d: dict) -> Order:
    return Order(
        id=d["id"],
        date=date.fromisoformat(d["date"]),
        customer=d["customer"],
        lines=[OrderLine(x["sku"], x["name"], int(x["qty"]), Money.parse(x["unit_price"]))
               for x in d["lines"]],
        status=d.get("status", "paid"),
    )


def load_orders(path) -> list[Order]:
    with open(path, encoding="utf-8") as fh:
        return [order_from_dict(d) for d in json.load(fh)]
