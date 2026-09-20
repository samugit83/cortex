#!/usr/bin/env python3
"""Regenerate tests/golden/order.<extension> for every registered exporter (`make golden`).

A golden file is what an exporter produces for tests/fixtures/orders.json. Commit it with
the exporter: `make lint` fails when one is missing or out of date.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shop.orders import load_orders                 # noqa: E402
from shop.plugins.registry import EXPORTERS         # noqa: E402


def main():
    orders = load_orders(ROOT / "tests" / "fixtures" / "orders.json")
    out = ROOT / "tests" / "golden"
    out.mkdir(parents=True, exist_ok=True)
    for name, cls in sorted(EXPORTERS.items()):
        exporter = cls()
        path = out / f"order.{exporter.extension}"
        path.write_text(exporter.export(orders), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  ({name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
