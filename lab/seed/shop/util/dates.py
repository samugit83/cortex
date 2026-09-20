"""Date helpers. Dates only — for the current time use shop.clock."""
from datetime import date, datetime, timedelta


def parse_date(text: str) -> date:
    """Accepts ISO '2026-09-19' and the European '19/09/2026'."""
    text = text.strip()
    if "/" in text:
        a, b, year = text.split("/")
        return date(int(year), int(a), int(b))
    return datetime.strptime(text, "%Y-%m-%d").date()


def format_date(d: date, style: str = "eu") -> str:
    """'19/09/2026' (style 'eu') or '2026-09-19' (style 'iso')."""
    if style == "iso":
        return d.isoformat()
    return d.strftime("%d/%m/%Y")


def add_business_days(start: date, days: int) -> date:
    """The date `days` working days after `start` (Saturdays and Sundays skipped)."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 6:
            added += 1
    return current


def days_between(a: date, b: date) -> int:
    """Whole days from a to b (negative when b is earlier)."""
    return (b - a).days
