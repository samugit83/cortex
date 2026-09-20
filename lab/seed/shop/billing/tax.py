"""Sales tax."""
from .money import Money


def tax_for(amount: Money, rate: str) -> Money:
    """Tax due on `amount` at `rate` percent, the rate as text ("22", "8.25")."""
    whole = int(rate.split(".")[0])
    return Money(amount.cents * whole // 100)
