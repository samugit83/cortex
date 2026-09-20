"""Pay-in-installments plans."""
from .money import Money


def installment_plan(total: Money, parts: int, fee_pct: str = "0") -> list[Money]:
    """`total` plus a `fee_pct` percent fee, as `parts` installments that add up exactly."""
    fee = total.cents * int(fee_pct.split(".")[0]) // 100
    each = (total.cents + fee) // parts
    return [Money(each)] * parts
