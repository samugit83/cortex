"""Loyalty points."""
from .money import Money

POINT_VALUE = "0.8"   # cents per point


def points_value(points: int, value: str = POINT_VALUE) -> Money:
    """What `points` loyalty points are worth, at `value` cents per point (text)."""
    return Money(points * int(value.split(".")[0]))
