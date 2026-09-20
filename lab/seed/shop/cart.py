"""Shopping carts, stored as JSON files: {"lines": {"MUG-001": 2}}."""
from __future__ import annotations

import json

from .billing.money import Money


class Cart:
    def __init__(self, lines: dict[str, int] | None = None):
        self.lines: dict[str, int] = dict(lines or {})

    def add(self, sku: str, qty: int = 1) -> None:
        if qty <= 0:
            raise ValueError("quantity must be positive")
        self.lines[sku] = self.lines.get(sku, 0) + qty

    def remove(self, sku: str, qty: int = 1) -> None:
        """Take `qty` of `sku` out of the cart; the line disappears when none is left."""
        if sku not in self.lines:
            raise KeyError(sku)
        self.lines[sku] -= qty

    def count(self) -> int:
        """How many items, all lines together."""
        return sum(self.lines.values())

    def total(self, products) -> Money:
        by_sku = {p.sku: p for p in products}
        return Money.total(by_sku[sku].price * qty for sku, qty in self.lines.items())

    def to_dict(self) -> dict:
        return {"lines": dict(self.lines)}

    @classmethod
    def from_dict(cls, d: dict) -> "Cart":
        return cls({k: int(v) for k, v in d.get("lines", {}).items()})


def load_cart(path) -> Cart:
    with open(path, encoding="utf-8") as fh:
        return Cart.from_dict(json.load(fh))
