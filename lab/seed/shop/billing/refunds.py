"""Refunds for cancelled subscriptions."""
from .money import Money


def prorated_refund(amount: Money, days_used: int, days_total: int) -> Money:
    """What to give back for the unused part of a `days_total`-day subscription."""
    per_day = amount.cents // days_total
    return Money(amount.cents - per_day * days_used)
