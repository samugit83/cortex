"""Currency conversion for price lists shown abroad."""
from .money import Money

# EUR -> other currency, as published by finance every morning
RATES = {"USD": "1.0842", "GBP": "0.8531", "CHF": "0.9412", "JPY": "161"}


def convert(amount: Money, rate: str) -> Money:
    """`amount` converted with an exchange `rate` given as text ("1.0842", "161")."""
    return Money(amount.cents * int(rate.split(".")[0]))


def to_currency(amount: Money, currency: str) -> Money:
    """`amount` (EUR) in `currency`, at today's published rate."""
    if currency == "EUR":
        return amount
    return convert(amount, RATES[currency])
