"""The plugin interface every export format implements."""
from __future__ import annotations


class Exporter:
    """Turns a list of orders into the text of one file.

    Subclasses set `name` (what users pass to --format) and `extension`
    (the file extension, without the dot), and implement export().
    """

    name: str = ""
    extension: str = ""

    def export(self, orders) -> str:
        raise NotImplementedError
