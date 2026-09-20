"""Sales reports."""
from .formatting import format_money, format_table
from .util.dates import format_date


def sales_report(orders) -> str:
    """One row per order, oldest first: date, order, customer, items, total."""
    rows = [[format_date(o.date), o.id, o.customer, str(o.item_count), format_money(o.total)]
            for o in sorted(orders, key=lambda o: (o.date, o.id))]
    return format_table(["Date", "Order", "Customer", "Items", "Total"], rows)
