"""Shelf-label prices."""
from .money import Money


def price_per_kg(pack_price: Money, pack_grams: int) -> Money:
    """Price per kilogram of a pack, for the shelf label."""
    return Money(pack_price.cents // pack_grams * 1000)
