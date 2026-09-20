"""Input validation for customer data."""
import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+$")
_SKU = re.compile(r"^[A-Z]{3}-\d{3}$")


def is_valid_email(address: str) -> bool:
    """A plausible e-mail address: local@domain.tld."""
    return bool(_EMAIL.match(address.strip()))


def normalize_phone(number: str) -> str:
    """'+39 333 123 4567' -> '+393331234567'. Keeps the international prefix."""
    return re.sub(r"\D", "", number)


def is_valid_sku(sku: str) -> bool:
    """SKUs look like 'MUG-001'."""
    return bool(_SKU.match(sku))
