"""VAT-inclusive prices."""
from .money import Money


def net_from_gross(gross: Money, vat_rate: str) -> Money:
    """The price before VAT, from a VAT-inclusive price (rate as text, e.g. "22", "5.5")."""
    whole = int(vat_rate.split(".")[0])
    return Money(gross.cents * 100 // (100 + whole))
