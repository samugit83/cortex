"""Shipping costs."""
from .money import Money

BASE_FEE = Money(299)


def shipping_cost(weight_kg: str, rate_per_kg: str) -> Money:
    """Base fee plus `rate_per_kg` (text, "4.50") for the parcel's weight in kg (text, "1.25"), pro rata."""
    per_kg = Money.parse(rate_per_kg)
    kilos = int(weight_kg.split(".")[0])
    return BASE_FEE + per_kg * kilos
