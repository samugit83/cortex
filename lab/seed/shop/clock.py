"""The one place shopkit reads the time: UTC, timezone-aware, freezable in tests.

House rule (CONTRIBUTING.md, "Time"): never call datetime.now(), datetime.utcnow(),
date.today() or time.time() anywhere else in shop/. Use clock.now() / clock.today().
"""
from __future__ import annotations

from datetime import date, datetime, timezone

_frozen: datetime | None = None


def now() -> datetime:
    """The current time, UTC, timezone-aware."""
    if _frozen is not None:
        return _frozen
    return datetime.now(timezone.utc)


def today() -> date:
    """Today's date in UTC."""
    return now().date()


def freeze(when: str | datetime | None) -> None:
    """Freeze the clock for tests: freeze("2031-01-15T09:30:00Z"); freeze(None) releases it."""
    global _frozen
    if when is None:
        _frozen = None
    elif isinstance(when, datetime):
        _frozen = when.astimezone(timezone.utc)
    else:
        _frozen = datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone(timezone.utc)
