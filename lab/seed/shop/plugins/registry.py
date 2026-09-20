"""Which export formats exist. A format that is not listed here does not exist."""
from .csv_export import CsvExporter
from .json_export import JsonExporter

EXPORTERS = {
    "csv": CsvExporter,
    "json": JsonExporter,
}


class UnknownFormat(ValueError):
    pass


def available() -> list[str]:
    return sorted(EXPORTERS)


def get_exporter(name: str):
    try:
        return EXPORTERS[name]()
    except KeyError:
        raise UnknownFormat(f"unknown format {name!r} (available: {', '.join(available())})") from None
