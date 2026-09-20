"""Store credit for returns."""
from .money import Money
from .rates import percent_of

RETURN_CREDIT = "90"   # percent of the price, given back as store credit


def return_credit(price: Money) -> Money:
    """Store credit for a returned item."""
    return percent_of(price, RETURN_CREDIT)
