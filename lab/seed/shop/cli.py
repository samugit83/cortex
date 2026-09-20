"""The `shop` command line: python3 -m shop <command> ..."""
from __future__ import annotations

import argparse
import sys

from .billing.invoice import build_invoice
from .cart import load_cart
from .catalog import find, load_catalog, sort_products
from .formatting import format_money, format_table
from .orders import load_orders
from .plugins.registry import UnknownFormat, available, get_exporter
from .report import sales_report
from .util.text import pluralize


def cmd_list(args) -> int:
    products = sort_products(load_catalog(args.catalog), args.sort)
    rows = [[p.sku, p.name, p.category, format_money(p.price), f"{p.stock} left"] for p in products]
    print(format_table(["SKU", "Name", "Category", "Price", "Stock"], rows))
    return 0


def cmd_show(args) -> int:
    p = find(load_catalog(args.catalog), args.sku)
    if p is None:
        print(f"no such product: {args.sku}")
        return 1
    print(p.name)
    print(f"  SKU:      {p.sku}")
    print(f"  Category: {p.category}")
    print(f"  Price:    {format_money(p.price)}")
    print(f"  Stock:    {p.stock} left")
    return 0


def cmd_cart_total(args) -> int:
    cart = load_cart(args.cart)
    total = cart.total(load_catalog(args.catalog))
    print(f"Total: {format_money(total)} ({pluralize(cart.count(), 'item')})")
    return 0


def cmd_invoice(args) -> int:
    inv = build_invoice(load_cart(args.cart), load_catalog(args.catalog), args.tax, args.discount)
    rows = [[l.sku, l.name, str(l.qty), format_money(l.unit_price), format_money(l.total)]
            for l in inv.lines]
    print(format_table(["SKU", "Item", "Qty", "Price", "Amount"], rows))
    print(f"Subtotal: {format_money(inv.subtotal)}")
    if inv.discount_pct not in ("0", ""):
        print(f"After {inv.discount_pct}% discount: {format_money(inv.discounted)}")
    print(f"Tax ({inv.tax_rate}%): {format_money(inv.tax)}")
    print(f"Total: {format_money(inv.total)}")
    return 0


def cmd_export(args) -> int:
    try:
        exporter = get_exporter(args.format)
    except UnknownFormat as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 2
    sys.stdout.write(exporter.export(load_orders(args.orders)))
    return 0


def cmd_report(args) -> int:
    print(sales_report(load_orders(args.orders)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shop", description="shopkit command line")
    parser.add_argument("--catalog", help="catalog JSON (default: data/catalog.json)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="list the products")
    p.add_argument("--sort", choices=["name", "price"], default="name")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one product")
    p.add_argument("sku")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("cart", help="work with a cart file")
    cart_sub = p.add_subparsers(dest="cart_command", required=True)
    t = cart_sub.add_parser("total", help="the total of a cart")
    t.add_argument("cart")
    t.set_defaults(func=cmd_cart_total)

    p = sub.add_parser("invoice", help="print an invoice for a cart")
    p.add_argument("cart")
    p.add_argument("--tax", default="22", help="tax rate in percent (default 22)")
    p.add_argument("--discount", default="0", help="discount in percent (default 0)")
    p.set_defaults(func=cmd_invoice)

    p = sub.add_parser("export", help="export orders")
    p.add_argument("orders")
    p.add_argument("--format", required=True, help=f"one of: {', '.join(available())}")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("report", help="sales report for an orders file")
    p.add_argument("orders")
    p.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
