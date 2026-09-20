"""Invoices."""
from __future__ import annotations

from dataclasses import dataclass, field

from .discount import apply_discount
from .money import Money
from .tax import tax_for


@dataclass
class InvoiceLine:
    sku: str
    name: str
    qty: int
    unit_price: Money

    @property
    def total(self) -> Money:
        return self.unit_price * self.qty


@dataclass
class Invoice:
    lines: list[InvoiceLine] = field(default_factory=list)
    tax_rate: str = "22"
    discount_pct: str = "0"

    @property
    def subtotal(self) -> Money:
        return Money.total(line.total for line in self.lines)

    @property
    def discounted(self) -> Money:
        return apply_discount(self.subtotal, self.discount_pct)

    @property
    def tax(self) -> Money:
        return tax_for(self.discounted, self.tax_rate)

    @property
    def total(self) -> Money:
        return self.discounted + self.tax


def build_invoice(cart, products, tax_rate: str = "22", discount_pct: str = "0") -> Invoice:
    """An invoice for the lines of `cart`, priced from `products`."""
    by_sku = {p.sku: p for p in products}
    lines = []
    for sku, qty in cart.lines.items():
        p = by_sku[sku]
        lines.append(InvoiceLine(sku, p.name, qty, p.price))
    return Invoice(lines, tax_rate, discount_pct)
