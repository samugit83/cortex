"""An amount of money, in integer cents."""
from __future__ import annotations

import re
from dataclasses import dataclass

_AMOUNT = re.compile(r"^\s*(-)?(\d+)(?:\.(\d{1,2}))?\s*$")


@dataclass(frozen=True, order=True)
class Money:
    cents: int

    def __post_init__(self):
        if not isinstance(self.cents, int) or isinstance(self.cents, bool):
            raise TypeError(f"Money needs integer cents, got {self.cents!r}")

    @classmethod
    def parse(cls, text: str) -> "Money":
        """'12.50' -> Money(1250), '7' -> Money(700). At most two decimals."""
        m = _AMOUNT.match(str(text))
        if not m:
            raise ValueError(f"not an amount: {text!r}")
        sign, whole, frac = m.groups()
        cents = int(whole) * 100 + int((frac or "0").ljust(2, "0"))
        return cls(-cents if sign else cents)

    def __add__(self, other: "Money") -> "Money":
        return Money(self.cents + other.cents)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.cents - other.cents)

    def __neg__(self) -> "Money":
        return Money(-self.cents)

    def __mul__(self, qty: int) -> "Money":
        if not isinstance(qty, int) or isinstance(qty, bool):
            raise TypeError("Money can only be multiplied by a whole quantity")
        return Money(self.cents * qty)

    __rmul__ = __mul__

    @staticmethod
    def total(amounts) -> "Money":
        acc = Money(0)
        for a in amounts:
            acc = acc + a
        return acc

    def __str__(self) -> str:
        sign = "-" if self.cents < 0 else ""
        c = abs(self.cents)
        return f"{sign}{c // 100}.{c % 100:02d}"
