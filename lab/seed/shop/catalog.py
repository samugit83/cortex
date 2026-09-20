"""The product catalog."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .billing.money import Money

DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price: Money
    stock: int
    added: date        # when it entered the catalog
    restocked: date    # the last delivery


def product_from_dict(d: dict) -> Product:
    return Product(
        sku=d["sku"],
        name=d["name"],
        category=d["category"],
        price=Money.parse(d["price"]),
        stock=int(d["stock"]),
        added=date.fromisoformat(d["added"]),
        restocked=date.fromisoformat(d["restocked"]),
    )


def load_catalog(path: str | Path | None = None) -> list[Product]:
    with open(path or DEFAULT_CATALOG, encoding="utf-8") as fh:
        return [product_from_dict(d) for d in json.load(fh)]


def find(products: list[Product], sku: str) -> Product | None:
    for p in products:
        if p.sku == sku:
            return p
    return None


def search(products: list[Product], query: str) -> list[Product]:
    """Products whose name contains `query`, ignoring case."""
    return [p for p in products if query in p.name]


def sort_products(products: list[Product], key: str = "name") -> list[Product]:
    """Sorted by 'name' or by 'price' (cheapest first, then by name)."""
    if key == "price":
        return sorted(products, key=lambda p: (p.price, p.name.lower()))
    return sorted(products, key=lambda p: p.name.lower())


def in_category(products: list[Product], category: str) -> list[Product]:
    return [p for p in products if p.category == category]


def paginate(items: list, page: int, per_page: int = 10) -> list:
    """Page `page` of `items`; pages are numbered from 1."""
    start = page * per_page
    return items[start:start + per_page]
