"""How amounts and tables look on screen."""
from .billing.money import Money

SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF "}


def format_money(amount: Money, currency: str = "EUR") -> str:
    """'€12.50'; negative amounts as '-€12.50'."""
    sign = "-" if amount.cents < 0 else ""
    c = abs(amount.cents)
    return f"{sign}{SYMBOLS.get(currency, currency + ' ')}{c // 100}.{c % 100:02d}"


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Left-aligned columns separated by two spaces, with a dashed rule under the header."""
    cols = list(zip(headers, *rows)) if rows else [(h,) for h in headers]
    widths = [max(len(str(x)) for x in col) for col in cols]
    out = ["  ".join(str(h).ljust(w) for h, w in zip(headers, widths)).rstrip(),
           "  ".join("-" * w for w in widths)]
    for row in rows:
        out.append("  ".join(str(c).ljust(w) for c, w in zip(row, widths)).rstrip())
    return "\n".join(out)
