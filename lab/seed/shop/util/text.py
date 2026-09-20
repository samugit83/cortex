"""Text helpers for labels, slugs and messages."""
import re


def slugify(text: str) -> str:
    """'Blue Mug (Large)' -> 'blue-mug-large'. Used for URLs and file names."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def truncate(text: str, width: int, ellipsis: str = "…") -> str:
    """Cut `text` to at most `width` characters, ending with `ellipsis` when cut."""
    if len(text) <= width:
        return text
    return text[:width] + ellipsis


def pluralize(count: int, noun: str, plural: str | None = None) -> str:
    """'1 item', '3 items'."""
    word = (plural or noun + "s") if count > 1 else noun
    return f"{count} {word}"


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to one space and trim the ends."""
    return " ".join(text.split())
