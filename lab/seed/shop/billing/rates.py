"""Exact arithmetic on Money: the only way billing code scales an amount.

Rates, percentages and factors arrive as text ("8.25", "1.0842") and are parsed
exactly; results are rounded half away from zero. See CONTRIBUTING.md, "Money".
"""
from __future__ import annotations

import re

from .money import Money

_DECIMAL = re.compile(r"^\s*(-)?(\d+)(?:\.(\d+))?\s*$")


def parse_rate(text: str) -> tuple[int, int]:
    """'8.25' -> (825, 100), '1.0842' -> (10842, 10000), '3' -> (3, 1)."""
    m = _DECIMAL.match(str(text))
    if not m:
        raise ValueError(f"not a decimal number: {text!r}")
    sign, whole, frac = m.groups()
    frac = frac or ""
    num = int(whole + frac)
    return (-num if sign else num), 10 ** len(frac)


def _div_half_up(num: int, den: int) -> int:
    q, r = divmod(abs(num), den)
    if 2 * r >= den:
        q += 1
    return q if num >= 0 else -q


def scale(amount: Money, num: int, den: int) -> Money:
    """amount * num / den."""
    if den <= 0:
        raise ValueError("den must be positive")
    return Money(_div_half_up(amount.cents * num, den))


def times(amount: Money, factor: str) -> Money:
    """amount times a decimal factor given as text."""
    num, den = parse_rate(factor)
    return scale(amount, num, den)


def percent_of(amount: Money, pct: str) -> Money:
    """pct percent of amount, pct given as text."""
    num, den = parse_rate(pct)
    return scale(amount, num, den * 100)


def split(amount: Money, parts: int) -> list[Money]:
    """`parts` amounts that add up exactly to `amount`; the first ones carry the extra cents."""
    if parts <= 0:
        raise ValueError("parts must be positive")
    q, r = divmod(amount.cents, parts)
    return [Money(q + (1 if i < r else 0)) for i in range(parts)]
