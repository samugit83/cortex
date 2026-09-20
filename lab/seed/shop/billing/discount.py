"""Percentage discounts."""
from .money import Money


def apply_discount(amount: Money, percent: str) -> Money:
    """`amount` after a `percent` discount, the percentage as text ("10", "12.5")."""
    whole = int(percent.split(".")[0])
    off = amount.cents * whole // 100
    return Money(amount.cents - off)
