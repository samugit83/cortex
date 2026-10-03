# A1 · Every scenario

56 scenarios: 26 training and 30 holdout, six per family. A scenario is a teammate's commit (a test, which is the specification), the user's words, a reference fix that satisfies the house rule, and — for the four families that have one — a **rule-breaking fix that passes the scenario's own test**. That last one is what makes the family's check the only thing that can tell them apart.

## Family A — user-visible change (CHANGELOG)

### A01 · list cheapest first by default  (train, round 2)

**The teammate's commit** — `test(cli): list sorts by price by default (PROD-31)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_list_default_sort.py`

**What the user asks**

> Product decided that `shop list` should show the cheapest products first by default (`--sort name` keeps the old order). QA already added tests/test_list_default_sort.py, which fails for now. Can you make the change?

**The check**: `python3 -m unittest tests.test_list_default_sort`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_list_default_sort.py`

```python
import unittest

from tests.support import run_cli


class DefaultSortTests(unittest.TestCase):
    def test_cheapest_first_by_default(self):
        code, out, _ = run_cli("list")
        self.assertEqual(code, 0)
        rows = out.splitlines()[2:]
        self.assertTrue(rows[0].startswith("TEA-001"))
        self.assertTrue(rows[-1].startswith("DSK-001"))

    def test_sort_by_name_still_works(self):
        code, out, _ = run_cli("list", "--sort", "name")
        self.assertTrue(out.splitlines()[2].startswith("CHR-001"))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "p.add_argument(\"--sort\", choices=[\"name\", \"price\"], default=\"name\")",
  "p.add_argument(\"--sort\", choices=[\"name\", \"price\"], default=\"price\")"
 ],
 [
  "changelog",
  "Changed",
  "`shop list` shows the cheapest products first by default; `--sort name` keeps the old order."
 ]
]
```

</details>

### A02 · thousands separator in prices  (train, round 2)

**The teammate's commit** — `test(formatting): thousands separator for big prices (PROD-34)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_money_display.py`

**What the user asks**

> Prices over a thousand are hard to read: the standing desk shows as €1249.00. Product wants a thousands separator (€1,249.00) everywhere. QA added tests/test_money_display.py. Please implement it.

**The check**: `python3 -m unittest tests.test_money_display`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_money_display.py`

```python
import unittest

from shop.billing.money import Money
from shop.formatting import format_money
from tests.support import run_cli


class ThousandsSeparatorTests(unittest.TestCase):
    def test_thousands_separator(self):
        self.assertEqual(format_money(Money(124900)), "€1,249.00")
        self.assertEqual(format_money(Money(123456789)), "€1,234,567.89")

    def test_show_uses_it(self):
        code, out, _ = run_cli("show", "DSK-001")
        self.assertIn("€1,249.00", out)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/formatting.py",
  "{c // 100}.{c % 100:02d}",
  "{c // 100:,}.{c % 100:02d}"
 ],
 [
  "changelog",
  "Changed",
  "Prices of a thousand or more are shown with a thousands separator (`\u20ac1,249.00`)."
 ]
]
```

</details>

### A03 · report total row  (train, round 2)

**The teammate's commit** — `test(report): a TOTAL row under the sales report (PROD-38)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_report_total.py`

**What the user asks**

> Finance wants a TOTAL row at the bottom of `shop report`: total items and total amount. QA added tests/test_report_total.py. Can you add it?

**The check**: `python3 -m unittest tests.test_report_total`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_report_total.py`

```python
import unittest

from shop.orders import load_orders
from shop.report import sales_report
from tests.support import ORDERS


class ReportTotalTests(unittest.TestCase):
    def test_total_row(self):
        last = sales_report(load_orders(ORDERS)).splitlines()[-1]
        self.assertTrue(last.startswith("TOTAL"))
        self.assertIn("€61.20", last)
        self.assertIn("4", last.split())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/report.py",
  "    return format_table([\"Date\", \"Order\", \"Customer\", \"Items\", \"Total\"], rows)\n",
  "    items = sum(o.item_count for o in orders)\n    total = Money.total(o.total for o in orders)\n    rows.append([\"TOTAL\", \"\", \"\", str(items), format_money(total)])\n    return format_table([\"Date\", \"Order\", \"Customer\", \"Items\", \"Total\"], rows)\n"
 ],
 [
  "replace",
  "shop/report.py",
  "from .formatting import format_money, format_table\n",
  "from .billing.money import Money\nfrom .formatting import format_money, format_table\n"
 ],
 [
  "changelog",
  "Added",
  "`shop report` ends with a TOTAL row (items and amount)."
 ]
]
```

</details>

### A04 · out of stock label  (train, round 6)

**The teammate's commit** — `test(cli): say 'Out of stock' instead of '0 left' (PROD-41)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_show_out_of_stock.py`

**What the user asks**

> '0 left' looks like a bug to customers. Product wants 'Out of stock' in both `shop show` and `shop list` when stock is zero. QA added tests/test_show_out_of_stock.py. Please implement it.

**The check**: `python3 -m unittest tests.test_show_out_of_stock`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_show_out_of_stock.py`

```python
import unittest

from tests.support import run_cli


class OutOfStockTests(unittest.TestCase):
    def test_show(self):
        code, out, _ = run_cli("show", "LMP-002")
        self.assertEqual(code, 0)
        self.assertIn("Out of stock", out)
        self.assertNotIn("0 left", out)

    def test_list(self):
        _, out, _ = run_cli("list")
        row = next(l for l in out.splitlines() if l.startswith("LMP-002"))
        self.assertIn("Out of stock", row)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "def cmd_list(args) -> int:\n",
  "def stock_text(stock: int) -> str:\n    return \"Out of stock\" if stock == 0 else f\"{stock} left\"\n\n\ndef cmd_list(args) -> int:\n"
 ],
 [
  "replace",
  "shop/cli.py",
  "format_money(p.price), f\"{p.stock} left\"] for p in products]",
  "format_money(p.price), stock_text(p.stock)] for p in products]"
 ],
 [
  "replace",
  "shop/cli.py",
  "print(f\"  Stock:    {p.stock} left\")",
  "print(f\"  Stock:    {stock_text(p.stock)}\")"
 ],
 [
  "changelog",
  "Changed",
  "`shop show` and `shop list` say \"Out of stock\" instead of \"0 left\"."
 ]
]
```

</details>

### A05 · list --limit  (train, round 7)

**The teammate's commit** — `test(cli): shop list --limit N (PROD-45)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_list_limit.py`

**What the user asks**

> Support wants `shop list --limit N` to show only the first N products. QA added tests/test_list_limit.py. Can you add the option?

**The check**: `python3 -m unittest tests.test_list_limit`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_list_limit.py`

```python
import unittest

from tests.support import run_cli


class ListLimitTests(unittest.TestCase):
    def test_limit(self):
        code, out, _ = run_cli("list", "--limit", "3")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 2 + 3)

    def test_limit_must_be_positive(self):
        code, _, _ = run_cli("list", "--limit", "0")
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "def cmd_list(args) -> int:\n    products = sort_products(load_catalog(args.catalog), args.sort)\n",
  "def positive_int(text: str) -> int:\n    n = int(text)\n    if n <= 0:\n        raise argparse.ArgumentTypeError(\"must be a positive number\")\n    return n\n\n\ndef cmd_list(args) -> int:\n    products = sort_products(load_catalog(args.catalog), args.sort)\n    if args.limit:\n        products = products[:args.limit]\n"
 ],
 [
  "replace",
  "shop/cli.py",
  "    p.add_argument(\"--sort\", choices=[\"name\", \"price\"], default=\"name\")\n",
  "    p.add_argument(\"--sort\", choices=[\"name\", \"price\"], default=\"name\")\n    p.add_argument(\"--limit\", type=positive_int, help=\"show only the first N products\")\n"
 ],
 [
  "changelog",
  "Added",
  "`shop list --limit N` shows only the first N products."
 ]
]
```

</details>

### A06 · ISO dates in the report  (train, round 9)

**The teammate's commit** — `test(report): ISO dates in the sales report (PROD-52)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_report_iso_dates.py`

**What the user asks**

> Our US partners misread 02/09/2026 in `shop report`. Product wants ISO dates (2026-09-02) there. QA added tests/test_report_iso_dates.py. Please change it.

**The check**: `python3 -m unittest tests.test_report_iso_dates`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_report_iso_dates.py`

```python
import unittest

from shop.orders import load_orders
from shop.report import sales_report
from tests.support import ORDERS


class IsoDateTests(unittest.TestCase):
    def test_iso_dates(self):
        report = sales_report(load_orders(ORDERS))
        self.assertIn("2026-09-02", report)
        self.assertNotIn("02/09/2026", report)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/report.py",
  "[format_date(o.date), o.id",
  "[format_date(o.date, \"iso\"), o.id"
 ],
 [
  "changelog",
  "Changed",
  "`shop report` shows dates as ISO (`2026-09-02`)."
 ]
]
```

</details>

### HA1 · cart summary wording  (holdout)

**The teammate's commit** — `test(cli): new cart total wording (PROD-57)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_cart_summary.py`

**What the user asks**

> Product wants `shop cart total` to print 'Cart: 3 items, total €22.20' instead of the old 'Total: … (3 items)'. QA added tests/test_cart_summary.py. Please change it.

**The check**: `python3 -m unittest tests.test_cart_summary`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_cart_summary.py`

```python
import unittest

from tests.support import CART, run_cli


class CartSummaryTests(unittest.TestCase):
    def test_summary_line(self):
        code, out, _ = run_cli("cart", "total", CART)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Cart: 3 items, total €22.20")


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "print(f\"Total: {format_money(total)} ({pluralize(cart.count(), 'item')})\")",
  "print(f\"Cart: {pluralize(cart.count(), 'item')}, total {format_money(total)}\")"
 ],
 [
  "changelog",
  "Changed",
  "`shop cart total` prints \"Cart: 3 items, total \u20ac22.20\"."
 ]
]
```

</details>

### HA2 · unknown product error  (holdout)

**The teammate's commit** — `test(cli): a proper error for unknown products (PROD-60)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_show_unknown.py`

**What the user asks**

> `shop show` with a wrong SKU prints 'no such product' on stdout and exits 1, which breaks our scripts. Product wants an error on stderr — "error: unknown product 'X' (try `shop list`)" — and exit code 2. QA added tests/test_show_unknown.py.

**The check**: `python3 -m unittest tests.test_show_unknown`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_show_unknown.py`

```python
import unittest

from tests.support import run_cli


class UnknownProductTests(unittest.TestCase):
    def test_error_on_stderr(self):
        code, out, err = run_cli("show", "NOPE-000")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("unknown product 'NOPE-000'", err)
        self.assertIn("shop list", err)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "        print(f\"no such product: {args.sku}\")\n        return 1\n",
  "        print(f\"error: unknown product '{args.sku}' (try `shop list`)\", file=sys.stderr)\n        return 2\n"
 ],
 [
  "changelog",
  "Changed",
  "`shop show` with an unknown SKU prints an error on stderr and exits with code 2."
 ]
]
```

</details>

### HA3 · list --category  (holdout)

**The teammate's commit** — `test(cli): shop list --category (PROD-64)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_list_category.py`

**What the user asks**

> Support wants `shop list --category <name>` to list one category only. QA added tests/test_list_category.py. Please add the option.

**The check**: `python3 -m unittest tests.test_list_category`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_list_category.py`

```python
import unittest

from tests.support import run_cli


class ListCategoryTests(unittest.TestCase):
    def test_category(self):
        code, out, _ = run_cli("list", "--category", "food")
        self.assertEqual(code, 0)
        rows = out.splitlines()[2:]
        self.assertEqual(sorted(r.split()[0] for r in rows), ["TEA-001", "TEA-002"])


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "    print(format_table([\"SKU\", \"Name\", \"Category\", \"Price\", \"Stock\"], rows))\n",
  "    if args.category:\n        rows = [r for r in rows if r[2] == args.category]\n    print(format_table([\"SKU\", \"Name\", \"Category\", \"Price\", \"Stock\"], rows))\n"
 ],
 [
  "replace",
  "shop/cli.py",
  "    p = sub.add_parser(\"list\", help=\"list the products\")\n",
  "    p = sub.add_parser(\"list\", help=\"list the products\")\n    p.add_argument(\"--category\", help=\"only this category\")\n"
 ],
 [
  "changelog",
  "Added",
  "`shop list --category <name>` lists one category."
 ]
]
```

</details>

### HA4 · export to a file  (holdout)

**The teammate's commit** — `test(cli): export --output writes a file (PROD-63)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_export_output.py`

**What the user asks**

> Support exports orders by copying them out of the terminal. Please make `shop export <orders.json> --format csv --output out.csv` write the export to that file and print nothing; without --output it should print as it does today. QA added tests/test_export_output.py.

**The check**: `python3 -m unittest tests.test_export_output`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_output.py`

```python
import unittest
import os
import tempfile

from tests.support import ORDERS, run_cli


class ExportOutputTests(unittest.TestCase):
    def test_writes_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            code, out, _ = run_cli("export", ORDERS, "--format", "csv", "--output", path)
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            with open(path, encoding="utf-8") as fh:
                self.assertIn("A-1001", fh.read())

    def test_without_output_it_still_prints(self):
        code, out, _ = run_cli("export", ORDERS, "--format", "csv")
        self.assertEqual(code, 0)
        self.assertIn("A-1001", out)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "    sys.stdout.write(exporter.export(load_orders(args.orders)))\n    return 0\n",
  "    text = exporter.export(load_orders(args.orders))\n    if args.output:\n        with open(args.output, \"w\", encoding=\"utf-8\") as fh:\n            fh.write(text)\n    else:\n        sys.stdout.write(text)\n    return 0\n"
 ],
 [
  "replace",
  "shop/cli.py",
  "    p.add_argument(\"--format\", required=True, help=f\"one of: {', '.join(available())}\")\n",
  "    p.add_argument(\"--format\", required=True, help=f\"one of: {', '.join(available())}\")\n    p.add_argument(\"--output\", help=\"write to this file instead of stdout\")\n"
 ],
 [
  "changelog",
  "Added",
  "`shop export --output FILE` writes the export to a file instead of stdout."
 ]
]
```

</details>

### HA5 · invoice item count  (holdout)

**The teammate's commit** — `test(cli): the invoice says how many items (PROD-71)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_invoice_items.py`

**What the user asks**

> Accounts cannot tell at a glance how big an invoice is. Please make `shop invoice` print a line `Items: 3` (the number of items) immediately before the Subtotal line. QA added tests/test_invoice_items.py.

**The check**: `python3 -m unittest tests.test_invoice_items`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_invoice_items.py`

```python
import unittest

from tests.support import CART, run_cli


class InvoiceItemsTests(unittest.TestCase):
    def test_items_line_before_the_subtotal(self):
        code, out, _ = run_cli("invoice", CART)
        self.assertEqual(code, 0)
        heads = [l for l in out.splitlines() if l.startswith(("Items:", "Subtotal:"))]
        self.assertEqual(heads[0], "Items: 3")
        self.assertTrue(heads[1].startswith("Subtotal:"))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "    print(f\"Subtotal: {format_money(inv.subtotal)}\")\n",
  "    print(f\"Items: {sum(l.qty for l in inv.lines)}\")\n    print(f\"Subtotal: {format_money(inv.subtotal)}\")\n"
 ],
 [
  "changelog",
  "Added",
  "`shop invoice` prints an `Items:` line with the number of items."
 ]
]
```

</details>

### HA6 · show the restock date  (holdout)

**The teammate's commit** — `test(cli): show prints the restock date (PROD-78)` by Tomás Ortega <tomas.ortega@shopkit.dev>

Files: `tests/test_show_restocked.py`

**What the user asks**

> Buyers keep asking when a product was last restocked. Please make `shop show` print a line `Restocked: 30/08/2026` (the European date format the rest of the CLI uses) just after the Category line. QA added tests/test_show_restocked.py.

**The check**: `python3 -m unittest tests.test_show_restocked`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_show_restocked.py`

```python
import unittest

from tests.support import run_cli


class ShowRestockedTests(unittest.TestCase):
    def test_restocked_line(self):
        code, out, _ = run_cli("show", "MUG-001")
        self.assertEqual(code, 0)
        self.assertIn("Restocked: 30/08/2026", out)

    def test_it_comes_after_the_category(self):
        _, out, _ = run_cli("show", "MUG-001")
        lines = [l.strip() for l in out.splitlines()]
        self.assertLess(next(i for i, l in enumerate(lines) if l.startswith("Category:")),
                        next(i for i, l in enumerate(lines) if l.startswith("Restocked:")))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cli.py",
  "from .orders import load_orders\n",
  "from .orders import load_orders\nfrom .util.dates import format_date\n"
 ],
 [
  "replace",
  "shop/cli.py",
  "    print(f\"  Category: {p.category}\")\n",
  "    print(f\"  Category: {p.category}\")\n    print(f\"  Restocked: {format_date(p.restocked)}\")\n"
 ],
 [
  "changelog",
  "Added",
  "`shop show` prints when the product was last restocked."
 ]
]
```

</details>

## Family B — money (billing)

### B01 · fractional tax rates  (train, round 1)

**The teammate's commit** — `test(billing): tax at fractional rates (QA-142)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_tax_rates.py`

**What the user asks**

> CI has been red since QA added tests/test_tax_rates.py: tax_for() gives the wrong tax for fractional rates like 8.25%, and it doesn't round the way the tests expect. Can you fix it?

**The check**: `python3 -m unittest tests.test_tax_rates`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_tax_rates.py`

```python
import unittest

from shop.billing.money import Money
from shop.billing.tax import tax_for


class FractionalTaxRateTests(unittest.TestCase):
    def test_fractional_rate(self):
        self.assertEqual(tax_for(Money(1999), "8.25"), Money(165))

    def test_half_cent_rounds_up(self):
        self.assertEqual(tax_for(Money(200), "8.25"), Money(17))

    def test_whole_rate_rounds_too(self):
        self.assertEqual(tax_for(Money(1999), "22"), Money(440))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/tax.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import percent_of\n"
 ],
 [
  "replace",
  "shop/billing/tax.py",
  "    whole = int(rate.split(\".\")[0])\n    return Money(amount.cents * whole // 100)\n",
  "    return percent_of(amount, rate)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/tax.py",
  "    whole = int(rate.split(\".\")[0])\n    return Money(amount.cents * whole // 100)\n",
  "    return Money(int(amount.cents * float(rate) / 100 + 0.5))\n"
 ]
]
```

</details>

### B02 · fractional discounts  (train, round 1)

**The teammate's commit** — `test(billing): discounts like 12.5% (QA-147)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_discount_rates.py`

**What the user asks**

> The 12.5% spring promo is charging customers the wrong amount — apply_discount() ignores the decimals. QA added tests/test_discount_rates.py and it fails. Please fix it.

**The check**: `python3 -m unittest tests.test_discount_rates`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_discount_rates.py`

```python
import unittest

from shop.billing.discount import apply_discount
from shop.billing.money import Money


class FractionalDiscountTests(unittest.TestCase):
    def test_fractional_percent(self):
        self.assertEqual(apply_discount(Money(2000), "12.5"), Money(1750))

    def test_rounds_half_away_from_zero(self):
        self.assertEqual(apply_discount(Money(1999), "15"), Money(1699))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/discount.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import percent_of\n"
 ],
 [
  "replace",
  "shop/billing/discount.py",
  "    whole = int(percent.split(\".\")[0])\n    off = amount.cents * whole // 100\n    return Money(amount.cents - off)\n",
  "    return amount - percent_of(amount, percent)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/discount.py",
  "    whole = int(percent.split(\".\")[0])\n    off = amount.cents * whole // 100\n    return Money(amount.cents - off)\n",
  "    off = int(amount.cents * float(percent) / 100 + 0.5)\n    return Money(amount.cents - off)\n"
 ]
]
```

</details>

### B03 · four-decimal exchange rates  (train, round 1)

**The teammate's commit** — `test(billing): convert with the published 4-decimal rates (QA-151)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_fx_rates.py`

**What the user asks**

> Our USD and GBP price lists are wrong: convert() ignores the decimals of the exchange rate, so 1.0842 is used as 1. Finance publishes 4 decimals. QA added tests/test_fx_rates.py — can you fix convert()?

**The check**: `python3 -m unittest tests.test_fx_rates`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_fx_rates.py`

```python
import unittest

from shop.billing.fx import convert, to_currency
from shop.billing.money import Money


class PublishedRateTests(unittest.TestCase):
    def test_four_decimal_rate(self):
        self.assertEqual(convert(Money(10000), "1.0842"), Money(10842))

    def test_rounding(self):
        self.assertEqual(convert(Money(1999), "0.8531"), Money(1705))
        self.assertEqual(convert(Money(1001), "0.8531"), Money(854))

    def test_to_usd(self):
        self.assertEqual(to_currency(Money(5000), "USD"), Money(5421))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/fx.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import times\n"
 ],
 [
  "replace",
  "shop/billing/fx.py",
  "    return Money(amount.cents * int(rate.split(\".\")[0]))\n",
  "    return times(amount, rate)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/fx.py",
  "    return Money(amount.cents * int(rate.split(\".\")[0]))\n",
  "    return Money(int(amount.cents * float(rate) + 0.5))\n"
 ]
]
```

</details>

### B04 · pro-rata shipping by weight  (train, round 6)

**The teammate's commit** — `test(billing): shipping for partial kilos (QA-158)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_shipping_weights.py`

**What the user asks**

> A 0.3 kg parcel is charged only the base fee, and 1.25 kg is charged like 1 kg — shipping_cost() drops the decimals of the weight. It should be pro rata. QA added tests/test_shipping_weights.py. Please fix it.

**The check**: `python3 -m unittest tests.test_shipping_weights`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_shipping_weights.py`

```python
import unittest

from shop.billing.money import Money
from shop.billing.shipping import shipping_cost


class ProRataShippingTests(unittest.TestCase):
    def test_partial_kilo(self):
        self.assertEqual(shipping_cost("1.25", "4.50"), Money(299 + 563))

    def test_light_parcel(self):
        self.assertEqual(shipping_cost("0.3", "4.50"), Money(299 + 135))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/shipping.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import times\n"
 ],
 [
  "replace",
  "shop/billing/shipping.py",
  "    kilos = int(weight_kg.split(\".\")[0])\n    return BASE_FEE + per_kg * kilos\n",
  "    return BASE_FEE + times(per_kg, weight_kg)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/shipping.py",
  "    kilos = int(weight_kg.split(\".\")[0])\n    return BASE_FEE + per_kg * kilos\n",
  "    return BASE_FEE + Money(int(per_kg.cents * float(weight_kg) + 0.5))\n"
 ]
]
```

</details>

### B05 · exact prorated refunds  (train, round 7)

**The teammate's commit** — `test(billing): prorated refunds must be exact (QA-163)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_refund_proration.py`

**What the user asks**

> A customer who cancelled after 10 of 30 days paid €9.99 and got €6.69 back instead of €6.66: prorated_refund() rounds the daily rate first. QA added tests/test_refund_proration.py. Can you fix it?

**The check**: `python3 -m unittest tests.test_refund_proration`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_refund_proration.py`

```python
import unittest

from shop.billing.money import Money
from shop.billing.refunds import prorated_refund


class ProrationTests(unittest.TestCase):
    def test_exact_proration(self):
        self.assertEqual(prorated_refund(Money(999), 10, 30), Money(666))

    def test_rounding(self):
        self.assertEqual(prorated_refund(Money(1000), 23, 45), Money(489))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/refunds.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import scale\n"
 ],
 [
  "replace",
  "shop/billing/refunds.py",
  "    per_day = amount.cents // days_total\n    return Money(amount.cents - per_day * days_used)\n",
  "    return scale(amount, days_total - days_used, days_total)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/refunds.py",
  "    per_day = amount.cents // days_total\n    return Money(amount.cents - per_day * days_used)\n",
  "    return Money(int(amount.cents * (days_total - days_used) / days_total + 0.5))\n"
 ]
]
```

</details>

### B06 · price per kilo labels  (train, round 9)

**The teammate's commit** — `test(billing): per-kilo shelf prices for small packs (QA-170)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_price_per_kg.py`

**What the user asks**

> The shelf labels say €0.00/kg for small packs: price_per_kg() divides too early. QA added tests/test_price_per_kg.py. Please fix it.

**The check**: `python3 -m unittest tests.test_price_per_kg`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_price_per_kg.py`

```python
import unittest

from shop.billing.money import Money
from shop.billing.pricing import price_per_kg


class ShelfLabelTests(unittest.TestCase):
    def test_small_pack(self):
        self.assertEqual(price_per_kg(Money(349), 250), Money(1396))

    def test_rounding(self):
        self.assertEqual(price_per_kg(Money(199), 330), Money(603))
        self.assertEqual(price_per_kg(Money(200), 300), Money(667))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/pricing.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import scale\n"
 ],
 [
  "replace",
  "shop/billing/pricing.py",
  "    return Money(pack_price.cents // pack_grams * 1000)\n",
  "    return scale(pack_price, 1000, pack_grams)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/pricing.py",
  "    return Money(pack_price.cents // pack_grams * 1000)\n",
  "    return Money(int(pack_price.cents * 1000 / pack_grams + 0.5))\n"
 ]
]
```

</details>

### HB1 · fractional loyalty point value  (holdout)

**The teammate's commit** — `test(billing): loyalty points worth 0.8 cents (QA-181)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_loyalty_value.py`

**What the user asks**

> Loyalty points show as worth €0.00: points_value() ignores the 0.8 cents per point. QA added tests/test_loyalty_value.py. Can you fix it?

**The check**: `python3 -m unittest tests.test_loyalty_value`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_loyalty_value.py`

```python
import unittest

from shop.billing.loyalty import points_value
from shop.billing.money import Money


class PointValueTests(unittest.TestCase):
    def test_default_value(self):
        self.assertEqual(points_value(1250), Money(1000))

    def test_rounding(self):
        self.assertEqual(points_value(3, "0.5"), Money(2))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/loyalty.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import times\n"
 ],
 [
  "replace",
  "shop/billing/loyalty.py",
  "    return Money(points * int(value.split(\".\")[0]))\n",
  "    return times(Money(points), value)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/loyalty.py",
  "    return Money(points * int(value.split(\".\")[0]))\n",
  "    return Money(int(points * float(value) + 0.5))\n"
 ]
]
```

</details>

### HB2 · installment fees and exact split  (holdout)

**The teammate's commit** — `test(billing): installment plans with a fee (QA-186)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_installment_fees.py`

**What the user asks**

> Installment plans lose cents: €10.01 in 4 installments adds up to €10.00, and the 2.5% fee is charged as 2%. QA added tests/test_installment_fees.py. Please fix installment_plan().

**The check**: `python3 -m unittest tests.test_installment_fees`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_installment_fees.py`

```python
import unittest

from shop.billing.installments import installment_plan
from shop.billing.money import Money


class InstallmentFeeTests(unittest.TestCase):
    def test_fee_and_exact_split(self):
        self.assertEqual(installment_plan(Money(10000), 3, "2.5"),
                         [Money(3417), Money(3417), Money(3416)])

    def test_parts_add_up(self):
        self.assertEqual(Money.total(installment_plan(Money(1001), 4)), Money(1001))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/installments.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import percent_of, split\n"
 ],
 [
  "replace",
  "shop/billing/installments.py",
  "    fee = total.cents * int(fee_pct.split(\".\")[0]) // 100\n    each = (total.cents + fee) // parts\n    return [Money(each)] * parts\n",
  "    return split(total + percent_of(total, fee_pct), parts)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/installments.py",
  "    fee = total.cents * int(fee_pct.split(\".\")[0]) // 100\n    each = (total.cents + fee) // parts\n    return [Money(each)] * parts\n",
  "    amount = total.cents + int(total.cents * float(fee_pct) / 100 + 0.5)\n    each, extra = divmod(amount, parts)\n    return [Money(each + (1 if i < extra else 0)) for i in range(parts)]\n"
 ]
]
```

</details>

### HB3 · net price at reduced VAT rates  (holdout)

**The teammate's commit** — `test(billing): net from gross at 5.5% VAT (QA-190)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_vat_reduced.py`

**What the user asks**

> net_from_gross() is wrong for the French 5.5% VAT rate and it truncates instead of rounding. QA added tests/test_vat_reduced.py. Please fix it.

**The check**: `python3 -m unittest tests.test_vat_reduced`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_vat_reduced.py`

```python
import unittest

from shop.billing.money import Money
from shop.billing.vat import net_from_gross


class ReducedVatTests(unittest.TestCase):
    def test_fractional_rate(self):
        self.assertEqual(net_from_gross(Money(1055), "5.5"), Money(1000))

    def test_rounding(self):
        self.assertEqual(net_from_gross(Money(999), "22"), Money(819))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/vat.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import parse_rate, scale\n"
 ],
 [
  "replace",
  "shop/billing/vat.py",
  "    whole = int(vat_rate.split(\".\")[0])\n    return Money(gross.cents * 100 // (100 + whole))\n",
  "    num, den = parse_rate(vat_rate)\n    return scale(gross, 100 * den, 100 * den + num)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/vat.py",
  "    whole = int(vat_rate.split(\".\")[0])\n    return Money(gross.cents * 100 // (100 + whole))\n",
  "    return Money(int(gross.cents / (1 + float(vat_rate) / 100) + 0.5))\n"
 ]
]
```

</details>

### HB4 · store credit with a bonus factor  (holdout)

**The teammate's commit** — `test(billing): store credit at a bonus factor (QA-203)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_credit_bonus.py`

**What the user asks**

> Marketing is running a store-credit bonus: a return can be credited at a factor like "1.05" (5 % more than the price paid). Please add credit_with_bonus(price, factor) to shop/billing/credit.py — the factor arrives as text, from the campaign file. QA added tests/test_credit_bonus.py.

**The check**: `python3 -m unittest tests.test_credit_bonus`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_credit_bonus.py`

```python
import unittest

from shop.billing.credit import credit_with_bonus
from shop.billing.money import Money


class CreditBonusTests(unittest.TestCase):
    def test_five_percent_bonus(self):
        self.assertEqual(credit_with_bonus(Money(1999), "1.05"), Money(2099))

    def test_an_exact_factor(self):
        self.assertEqual(credit_with_bonus(Money(1000), "1.125"), Money(1125))

    def test_four_decimals(self):
        self.assertEqual(credit_with_bonus(Money(333), "1.0842"), Money(361))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/credit.py",
  "from .rates import percent_of\n",
  "from .rates import percent_of, times\n"
 ],
 [
  "write_append",
  "shop/billing/credit.py",
  "\n\ndef credit_with_bonus(price: Money, factor: str) -> Money:\n    \"\"\"Store credit worth `factor` times the price (factor as text, \"1.05\").\"\"\"\n    return times(price, factor)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "write_append",
  "shop/billing/credit.py",
  "\n\ndef credit_with_bonus(price: Money, factor: str) -> Money:\n    return Money(round(price.cents * float(factor)))\n"
 ]
]
```

</details>

### HB5 · refunds that add up exactly  (holdout)

**The teammate's commit** — `test(billing): a cancelled plan refunds in equal parts (QA-209)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_refund_installments.py`

**What the user asks**

> When a customer cancels a plan we pay them back in equal installments and the cents have to add up to the total exactly — finance reconciles it. Please add refund_installments(total, parts) to shop/billing/installments.py. QA added tests/test_refund_installments.py.

**The check**: `python3 -m unittest tests.test_refund_installments`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_refund_installments.py`

```python
import unittest

from shop.billing.installments import refund_installments
from shop.billing.money import Money


class RefundInstallmentsTests(unittest.TestCase):
    def test_it_adds_up_exactly(self):
        parts = refund_installments(Money(1000), 3)
        self.assertEqual([p.cents for p in parts], [334, 333, 333])
        self.assertEqual(sum(p.cents for p in parts), 1000)

    def test_a_divisible_total(self):
        parts = refund_installments(Money(1200), 4)
        self.assertEqual([p.cents for p in parts], [300, 300, 300, 300])

    def test_an_awkward_total(self):
        parts = refund_installments(Money(1001), 6)
        self.assertEqual(sum(p.cents for p in parts), 1001)
        self.assertEqual(max(p.cents for p in parts) - min(p.cents for p in parts), 1)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/installments.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import split\n"
 ],
 [
  "write_append",
  "shop/billing/installments.py",
  "\n\ndef refund_installments(total: Money, parts: int) -> list[Money]:\n    \"\"\"`parts` refunds that add up exactly to `total`.\"\"\"\n    return split(total, parts)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "write_append",
  "shop/billing/installments.py",
  "\n\ndef refund_installments(total: Money, parts: int) -> list[Money]:\n    each = int(total.cents / parts)\n    rest = total.cents - each * parts\n    return [Money(each + (1 if i < rest else 0)) for i in range(parts)]\n"
 ]
]
```

</details>

### HB6 · VAT-inclusive price from a net price  (holdout)

**The teammate's commit** — `test(billing): gross price at fractional VAT rates (QA-214)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_vat_gross.py`

**What the user asks**

> The web shop shows VAT-inclusive prices and we compute them in a spreadsheet. Please add gross_from_net(net, vat_rate) to shop/billing/vat.py — the price with VAT added, the rate as text ("22", "5.5"). QA added tests/test_vat_gross.py.

**The check**: `python3 -m unittest tests.test_vat_gross`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_vat_gross.py`

```python
import unittest

from shop.billing.money import Money
from shop.billing.vat import gross_from_net


class VatGrossTests(unittest.TestCase):
    def test_a_reduced_rate(self):
        self.assertEqual(gross_from_net(Money(1000), "5.5"), Money(1055))

    def test_the_standard_rate(self):
        self.assertEqual(gross_from_net(Money(1999), "22"), Money(2439))

    def test_two_decimals(self):
        self.assertEqual(gross_from_net(Money(333), "8.25"), Money(360))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/vat.py",
  "from .money import Money\n",
  "from .money import Money\nfrom .rates import percent_of\n"
 ],
 [
  "write_append",
  "shop/billing/vat.py",
  "\n\ndef gross_from_net(net: Money, vat_rate: str) -> Money:\n    \"\"\"The VAT-inclusive price of `net` (rate as text, \"22\", \"5.5\").\"\"\"\n    return net + percent_of(net, vat_rate)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "write_append",
  "shop/billing/vat.py",
  "\n\ndef gross_from_net(net: Money, vat_rate: str) -> Money:\n    return Money(net.cents + round(net.cents * float(vat_rate) / 100))\n"
 ]
]
```

</details>

## Family C — new exporter

### C01 · XML export  (train, round 3)

**The teammate's commit** — `test(export): tests for the XML exporter (EXP-12)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_xml.py`

**What the user asks**

> Our accountant's software imports XML. Please add an XML export format: `shop export orders.json --format xml`. The tests are already in tests/test_export_xml.py — they fail for now.

**The check**: `python3 -m unittest tests.test_export_xml`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_xml.py`

```python
import unittest
import xml.etree.ElementTree as ET

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class XmlExportTests(unittest.TestCase):
    def setUp(self):
        self.root = ET.fromstring(get_exporter("xml").export(load_orders(ORDERS)))

    def test_orders(self):
        self.assertEqual(self.root.tag, "orders")
        orders = self.root.findall("order")
        self.assertEqual([o.get("id") for o in orders], ["A-1001", "A-1002"])
        self.assertEqual(orders[0].get("total"), "22.20")

    def test_lines(self):
        line = self.root.find("order/line")
        self.assertEqual(line.get("sku"), "MUG-001")
        self.assertEqual(line.get("qty"), "2")

    def test_is_available(self):
        self.assertIn("xml", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/xml_export.py",
  "\"\"\"XML: <orders><order ...><line .../></order></orders>.\"\"\"\nimport xml.etree.ElementTree as ET\n\nfrom .base import Exporter\n\n\nclass XmlExporter(Exporter):\n    name = \"xml\"\n    extension = \"xml\"\n\n    def export(self, orders) -> str:\n        root = ET.Element(\"orders\")\n        for o in orders:\n            order = ET.SubElement(root, \"order\", id=o.id, date=o.date.isoformat(),\n                                  customer=o.customer, total=str(o.total))\n            for line in o.lines:\n                ET.SubElement(order, \"line\", sku=line.sku, name=line.name, qty=str(line.qty),\n                              unit_price=str(line.unit_price), total=str(line.total))\n        ET.indent(root)\n        return ET.tostring(root, encoding=\"unicode\") + \"\\n\"\n"
 ],
 [
  "register",
  "xml",
  "xml_export",
  "XmlExporter"
 ],
 [
  "docs_row",
  "xml",
  "xml",
  "the orders as XML elements, amounts as attributes"
 ],
 [
  "golden"
 ]
]
```

</details>

### C02 · Markdown export  (train, round 3)

**The teammate's commit** — `test(export): tests for a Markdown table export (EXP-15)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_markdown.py`

**What the user asks**

> We paste order summaries into our wiki. Can you add a `markdown` export format (a table, one row per order line)? The tests are in tests/test_export_markdown.py.

**The check**: `python3 -m unittest tests.test_export_markdown`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_markdown.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class MarkdownExportTests(unittest.TestCase):
    def setUp(self):
        self.lines = get_exporter("markdown").export(load_orders(ORDERS)).splitlines()

    def test_table(self):
        self.assertTrue(self.lines[0].startswith("| order |"))
        self.assertTrue(set(self.lines[1]) <= set("|-: "))
        self.assertEqual(len(self.lines), 2 + 3)

    def test_row(self):
        self.assertIn("| A-1001 |", self.lines[2])
        self.assertIn("| MUG-001 |", self.lines[2])

    def test_is_available(self):
        self.assertIn("markdown", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/markdown_export.py",
  "\"\"\"Markdown: one table row per order line.\"\"\"\nfrom .base import Exporter\n\n\nclass MarkdownExporter(Exporter):\n    name = \"markdown\"\n    extension = \"md\"\n\n    def export(self, orders) -> str:\n        out = [\"| order | date | customer | sku | qty | total |\",\n               \"|---|---|---|---|---|---|\"]\n        for o in orders:\n            for line in o.lines:\n                out.append(f\"| {o.id} | {o.date.isoformat()} | {o.customer} | {line.sku} \"\n                           f\"| {line.qty} | {line.total} |\")\n        return \"\\n\".join(out) + \"\\n\"\n"
 ],
 [
  "register",
  "markdown",
  "markdown_export",
  "MarkdownExporter"
 ],
 [
  "docs_row",
  "markdown",
  "md",
  "a Markdown table, one row per order line"
 ],
 [
  "golden"
 ]
]
```

</details>

### C03 · TSV export  (train, round 3)

**The teammate's commit** — `test(export): tests for TSV (EXP-19)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_tsv.py`

**What the user asks**

> Excel users keep breaking our CSV on commas in customer names. Please add a `tsv` export format (tab separated). Tests are in tests/test_export_tsv.py.

**The check**: `python3 -m unittest tests.test_export_tsv`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_tsv.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class TsvExportTests(unittest.TestCase):
    def setUp(self):
        self.lines = get_exporter("tsv").export(load_orders(ORDERS)).splitlines()

    def test_tab_separated(self):
        self.assertEqual(self.lines[0].split("\t")[:3], ["order", "date", "customer"])
        self.assertEqual(self.lines[1].split("\t")[3], "MUG-001")

    def test_is_available(self):
        self.assertIn("tsv", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/tsv_export.py",
  "\"\"\"TSV: like CSV, tab separated \u2014 pastes straight into spreadsheets.\"\"\"\nimport csv\nimport io\n\nfrom .base import Exporter\n\n\nclass TsvExporter(Exporter):\n    name = \"tsv\"\n    extension = \"tsv\"\n\n    def export(self, orders) -> str:\n        buf = io.StringIO()\n        w = csv.writer(buf, delimiter=\"\\t\", lineterminator=\"\\n\")\n        w.writerow([\"order\", \"date\", \"customer\", \"sku\", \"qty\", \"unit_price\", \"line_total\"])\n        for o in orders:\n            for line in o.lines:\n                w.writerow([o.id, o.date.isoformat(), o.customer, line.sku, line.qty,\n                            str(line.unit_price), str(line.total)])\n        return buf.getvalue()\n"
 ],
 [
  "register",
  "tsv",
  "tsv_export",
  "TsvExporter"
 ],
 [
  "docs_row",
  "tsv",
  "tsv",
  "like csv, tab separated"
 ],
 [
  "golden"
 ]
]
```

</details>

### C04 · NDJSON export  (train, round 6)

**The teammate's commit** — `test(export): tests for NDJSON (EXP-22)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_ndjson.py`

**What the user asks**

> The data team wants orders as NDJSON (one JSON object per order line) for their pipeline. Please add an `ndjson` export format — tests in tests/test_export_ndjson.py.

**The check**: `python3 -m unittest tests.test_export_ndjson`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_ndjson.py`

```python
import unittest
import json

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class NdjsonExportTests(unittest.TestCase):
    def setUp(self):
        text = get_exporter("ndjson").export(load_orders(ORDERS))
        self.rows = [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_one_object_per_line(self):
        self.assertEqual(len(self.rows), 3)
        self.assertEqual(self.rows[0]["order"], "A-1001")
        self.assertEqual(self.rows[0]["sku"], "MUG-001")
        self.assertEqual(self.rows[2]["total"], "39.00")

    def test_is_available(self):
        self.assertIn("ndjson", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/ndjson_export.py",
  "\"\"\"NDJSON: one JSON object per order line, one per line of text.\"\"\"\nimport json\n\nfrom .base import Exporter\n\n\nclass NdjsonExporter(Exporter):\n    name = \"ndjson\"\n    extension = \"ndjson\"\n\n    def export(self, orders) -> str:\n        rows = []\n        for o in orders:\n            for line in o.lines:\n                rows.append(json.dumps({\"order\": o.id, \"date\": o.date.isoformat(),\n                                        \"customer\": o.customer, \"sku\": line.sku,\n                                        \"qty\": line.qty, \"total\": str(line.total)},\n                                       ensure_ascii=False))\n        return \"\\n\".join(rows) + \"\\n\"\n"
 ],
 [
  "register",
  "ndjson",
  "ndjson_export",
  "NdjsonExporter"
 ],
 [
  "docs_row",
  "ndjson",
  "ndjson",
  "one JSON object per order line (newline-delimited JSON)"
 ],
 [
  "golden"
 ]
]
```

</details>

### C05 · HTML export  (train, round 8)

**The teammate's commit** — `test(export): tests for an HTML table export (EXP-26)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_html.py`

**What the user asks**

> We want to e-mail order tables. Please add an `html` export format (a <table>, one row per order line). The tests are in tests/test_export_html.py.

**The check**: `python3 -m unittest tests.test_export_html`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_html.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class HtmlExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("html").export(load_orders(ORDERS))

    def test_table(self):
        self.assertIn("<table>", self.text)
        self.assertEqual(self.text.count("<td>A-1001</td>"), 2)
        self.assertIn("<td>LMP-001</td>", self.text)

    def test_is_available(self):
        self.assertIn("html", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/html_export.py",
  "\"\"\"HTML: a table, one row per order line.\"\"\"\nfrom html import escape\n\nfrom .base import Exporter\n\n\nclass HtmlExporter(Exporter):\n    name = \"html\"\n    extension = \"html\"\n\n    def export(self, orders) -> str:\n        out = [\"<table>\",\n               \"  <tr><th>order</th><th>date</th><th>customer</th><th>sku</th><th>qty</th><th>total</th></tr>\"]\n        for o in orders:\n            for line in o.lines:\n                cells = [o.id, o.date.isoformat(), o.customer, line.sku, str(line.qty), str(line.total)]\n                out.append(\"  <tr>\" + \"\".join(f\"<td>{escape(c)}</td>\" for c in cells) + \"</tr>\")\n        out.append(\"</table>\")\n        return \"\\n\".join(out) + \"\\n\"\n"
 ],
 [
  "register",
  "html",
  "html_export",
  "HtmlExporter"
 ],
 [
  "docs_row",
  "html",
  "html",
  "an HTML table, one row per order line"
 ],
 [
  "golden"
 ]
]
```

</details>

### C06 · YAML export  (train, round 10)

**The teammate's commit** — `test(export): tests for YAML (EXP-30)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_yaml.py`

**What the user asks**

> Ops keeps fixtures in YAML. Please add a `yaml` export format — no new dependency, we don't have PyYAML. Amounts must be quoted strings. Tests: tests/test_export_yaml.py.

**The check**: `python3 -m unittest tests.test_export_yaml`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_yaml.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class YamlExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("yaml").export(load_orders(ORDERS))

    def test_orders(self):
        self.assertIn("- id: A-1001", self.text)
        self.assertIn("- id: A-1002", self.text)
        self.assertIn("total: '22.20'", self.text)

    def test_is_available(self):
        self.assertIn("yaml", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/yaml_export.py",
  "\"\"\"YAML: the orders as a list, amounts quoted so they stay exact.\"\"\"\nfrom .base import Exporter\n\n\ndef _q(text):\n    return \"'\" + str(text).replace(\"'\", \"''\") + \"'\"\n\n\nclass YamlExporter(Exporter):\n    name = \"yaml\"\n    extension = \"yaml\"\n\n    def export(self, orders) -> str:\n        out = []\n        for o in orders:\n            out.append(f\"- id: {o.id}\")\n            out.append(f\"  date: {o.date.isoformat()}\")\n            out.append(f\"  customer: {_q(o.customer)}\")\n            out.append(f\"  total: {_q(o.total)}\")\n            out.append(\"  lines:\")\n            for line in o.lines:\n                out.append(f\"    - sku: {line.sku}\")\n                out.append(f\"      qty: {line.qty}\")\n                out.append(f\"      total: {_q(line.total)}\")\n        return \"\\n\".join(out) + \"\\n\"\n"
 ],
 [
  "register",
  "yaml",
  "yaml_export",
  "YamlExporter"
 ],
 [
  "docs_row",
  "yaml",
  "yaml",
  "the orders as a YAML list, amounts quoted"
 ],
 [
  "golden"
 ]
]
```

</details>

### HC1 · text receipt export  (holdout)

**The teammate's commit** — `test(export): tests for plain-text receipts (EXP-34)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_receipt.py`

**What the user asks**

> The shop counter needs plain-text receipts. Please add a `receipt` export format (one block per order, with a TOTAL line). Tests: tests/test_export_receipt.py.

**The check**: `python3 -m unittest tests.test_export_receipt`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_receipt.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class ReceiptExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("receipt").export(load_orders(ORDERS))

    def test_blocks(self):
        self.assertIn("ORDER A-1001", self.text)
        self.assertIn("ORDER A-1002", self.text)
        self.assertEqual(self.text.count("TOTAL"), 2)
        self.assertIn("22.20", self.text)

    def test_is_available(self):
        self.assertIn("receipt", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/receipt_export.py",
  "\"\"\"Plain-text receipts, one block per order.\"\"\"\nfrom .base import Exporter\n\n\nclass ReceiptExporter(Exporter):\n    name = \"receipt\"\n    extension = \"txt\"\n\n    def export(self, orders) -> str:\n        out = []\n        for o in orders:\n            out.append(f\"ORDER {o.id}  {o.date.isoformat()}  {o.customer}\")\n            for line in o.lines:\n                out.append(f\"  {line.qty:>3} x {line.name:<24} {str(line.total):>10}\")\n            out.append(f\"  {'TOTAL':<30} {str(o.total):>10}\")\n            out.append(\"\")\n        return \"\\n\".join(out)\n"
 ],
 [
  "register",
  "receipt",
  "receipt_export",
  "ReceiptExporter"
 ],
 [
  "docs_row",
  "receipt",
  "txt",
  "plain-text receipts, one block per order"
 ],
 [
  "golden"
 ]
]
```

</details>

### HC2 · INI export  (holdout)

**The teammate's commit** — `test(export): tests for INI (EXP-37)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_ini.py`

**What the user asks**

> An old warehouse tool reads INI files. Please add an `ini` export format, one [section] per order. Tests are in tests/test_export_ini.py.

**The check**: `python3 -m unittest tests.test_export_ini`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_ini.py`

```python
import unittest
import configparser

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class IniExportTests(unittest.TestCase):
    def setUp(self):
        self.parser = configparser.ConfigParser()
        self.parser.read_string(get_exporter("ini").export(load_orders(ORDERS)))

    def test_sections(self):
        self.assertEqual(self.parser.sections(), ["A-1001", "A-1002"])
        self.assertEqual(self.parser["A-1001"]["total"], "22.20")

    def test_is_available(self):
        self.assertIn("ini", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/ini_export.py",
  "\"\"\"INI: one [section] per order.\"\"\"\nfrom .base import Exporter\n\n\nclass IniExporter(Exporter):\n    name = \"ini\"\n    extension = \"ini\"\n\n    def export(self, orders) -> str:\n        out = []\n        for o in orders:\n            out.append(f\"[{o.id}]\")\n            out.append(f\"date = {o.date.isoformat()}\")\n            out.append(f\"customer = {o.customer}\")\n            out.append(f\"total = {o.total}\")\n            out.append(\"lines = \" + \", \".join(f\"{l.sku}x{l.qty}\" for l in o.lines))\n            out.append(\"\")\n        return \"\\n\".join(out)\n"
 ],
 [
  "register",
  "ini",
  "ini_export",
  "IniExporter"
 ],
 [
  "docs_row",
  "ini",
  "ini",
  "one [section] per order"
 ],
 [
  "golden"
 ]
]
```

</details>

### HC3 · LaTeX export  (holdout)

**The teammate's commit** — `test(export): tests for a LaTeX tabular (EXP-41)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_latex.py`

**What the user asks**

> Accounting prints statements with LaTeX. Please add a `latex` export format (a tabular, one row per order line). Tests: tests/test_export_latex.py.

**The check**: `python3 -m unittest tests.test_export_latex`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_latex.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class LatexExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("latex").export(load_orders(ORDERS))

    def test_tabular(self):
        self.assertIn("\\begin{tabular}", self.text)
        self.assertIn("\\end{tabular}", self.text)
        self.assertIn("A-1001 & MUG-001 & 2 & 17.00", self.text)

    def test_is_available(self):
        self.assertIn("latex", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/latex_export.py",
  "\"\"\"LaTeX: a tabular for printed statements.\"\"\"\nfrom .base import Exporter\n\n\ndef _tex(text):\n    for a, b in ((\"\\\\\", r\"\\textbackslash{}\"), (\"&\", r\"\\&\"), (\"%\", r\"\\%\"), (\"_\", r\"\\_\"), (\"#\", r\"\\#\")):\n        text = text.replace(a, b)\n    return text\n\n\nclass LatexExporter(Exporter):\n    name = \"latex\"\n    extension = \"tex\"\n\n    def export(self, orders) -> str:\n        out = [r\"\\begin{tabular}{llrr}\", r\"order & sku & qty & total \\\\\", r\"\\hline\"]\n        for o in orders:\n            for line in o.lines:\n                out.append(f\"{_tex(o.id)} & {_tex(line.sku)} & {line.qty} & {line.total} \\\\\\\\\")\n        out.append(r\"\\end{tabular}\")\n        return \"\\n\".join(out) + \"\\n\"\n"
 ],
 [
  "register",
  "latex",
  "latex_export",
  "LatexExporter"
 ],
 [
  "docs_row",
  "latex",
  "tex",
  "a LaTeX tabular, one row per order line"
 ],
 [
  "golden"
 ]
]
```

</details>

### HC4 · SQL export  (holdout)

**The teammate's commit** — `test(export): tests for SQL inserts (EXP-48)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_sql.py`

**What the user asks**

> The warehouse team loads orders into Postgres by hand. Please add a `sql` export format: one `INSERT INTO order_lines (...) VALUES (...);` per order line. Tests: tests/test_export_sql.py.

**The check**: `python3 -m unittest tests.test_export_sql`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_sql.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class SqlExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("sql").export(load_orders(ORDERS))

    def test_one_insert_per_order_line(self):
        inserts = [l for l in self.text.splitlines() if l.startswith("INSERT INTO order_lines")]
        self.assertEqual(len(inserts), 3)
        self.assertIn("'A-1001'", inserts[0])
        self.assertIn("'MUG-001'", inserts[0])
        self.assertTrue(inserts[0].rstrip().endswith(";"))

    def test_is_available(self):
        self.assertIn("sql", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/sql_export.py",
  "\"\"\"SQL: one INSERT per order line, for loading into the warehouse.\"\"\"\nfrom .base import Exporter\n\n\ndef _quote(value) -> str:\n    return \"'\" + str(value).replace(\"'\", \"''\") + \"'\"\n\n\nclass SqlExporter(Exporter):\n    name = \"sql\"\n    extension = \"sql\"\n\n    COLUMNS = \"order_id, order_date, customer, sku, qty, unit_price, line_total\"\n\n    def export(self, orders) -> str:\n        out = []\n        for o in orders:\n            for line in o.lines:\n                values = \", \".join([_quote(o.id), _quote(o.date.isoformat()), _quote(o.customer),\n                                    _quote(line.sku), str(line.qty), _quote(str(line.unit_price)),\n                                    _quote(str(line.total))])\n                out.append(f\"INSERT INTO order_lines ({self.COLUMNS}) VALUES ({values});\")\n        return \"\\n\".join(out) + \"\\n\"\n"
 ],
 [
  "register",
  "sql",
  "sql_export",
  "SqlExporter"
 ],
 [
  "docs_row",
  "sql",
  "sql",
  "one INSERT per order line, for the warehouse"
 ],
 [
  "golden"
 ]
]
```

</details>

### HC5 · TOML export  (holdout)

**The teammate's commit** — `test(export): tests for TOML (EXP-52)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_toml.py`

**What the user asks**

> Our deployment tooling reads TOML. Please add a `toml` export format: one `[[order]]` table per order, with the order's lines nested under it. Tests: tests/test_export_toml.py.

**The check**: `python3 -m unittest tests.test_export_toml`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_toml.py`

```python
import unittest
import tomllib

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class TomlExportTests(unittest.TestCase):
    def setUp(self):
        self.data = tomllib.loads(get_exporter("toml").export(load_orders(ORDERS)))

    def test_one_table_per_order(self):
        self.assertEqual([o["id"] for o in self.data["order"]], ["A-1001", "A-1002"])
        self.assertEqual(self.data["order"][0]["total"], "22.20")
        self.assertEqual(len(self.data["order"][0]["line"]), 2)

    def test_is_available(self):
        self.assertIn("toml", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/toml_export.py",
  "\"\"\"TOML: one [[order]] table per order, with its lines nested.\"\"\"\nfrom .base import Exporter\n\n\nclass TomlExporter(Exporter):\n    name = \"toml\"\n    extension = \"toml\"\n\n    def export(self, orders) -> str:\n        out = []\n        for o in orders:\n            out += [\"[[order]]\",\n                    f'id = \"{o.id}\"',\n                    f'date = \"{o.date.isoformat()}\"',\n                    f'customer = \"{o.customer}\"',\n                    f'status = \"{o.status}\"',\n                    f'total = \"{o.total}\"']\n            for line in o.lines:\n                out += [\"\",\n                        \"[[order.line]]\",\n                        f'sku = \"{line.sku}\"',\n                        f'name = \"{line.name}\"',\n                        f\"qty = {line.qty}\",\n                        f'unit_price = \"{line.unit_price}\"',\n                        f'total = \"{line.total}\"']\n            out.append(\"\")\n        return \"\\n\".join(out)\n"
 ],
 [
  "register",
  "toml",
  "toml_export",
  "TomlExporter"
 ],
 [
  "docs_row",
  "toml",
  "toml",
  "one [[order]] table per order, lines nested"
 ],
 [
  "golden"
 ]
]
```

</details>

### HC6 · reStructuredText export  (holdout)

**The teammate's commit** — `test(export): tests for an reST table (EXP-57)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_export_rst.py`

**What the user asks**

> The docs site includes order tables and wants reStructuredText. Please add an `rst` export format that writes a simple reST table (the `===` kind) of the order lines. Tests: tests/test_export_rst.py.

**The check**: `python3 -m unittest tests.test_export_rst`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_export_rst.py`

```python
import unittest

from shop.orders import load_orders
from shop.plugins.registry import available, get_exporter
from tests.support import ORDERS


class RstExportTests(unittest.TestCase):
    def setUp(self):
        self.lines = get_exporter("rst").export(load_orders(ORDERS)).splitlines()

    def test_simple_table(self):
        self.assertTrue(self.lines[0].startswith("="))
        self.assertTrue(self.lines[1].startswith("Order"))
        self.assertEqual(self.lines[0], self.lines[2])
        self.assertEqual(self.lines[0], self.lines[-1])
        self.assertTrue(any("MUG-001" in l for l in self.lines))

    def test_is_available(self):
        self.assertIn("rst", available())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "write",
  "shop/plugins/rst_export.py",
  "\"\"\"reStructuredText: a simple table of order lines, for the docs site.\"\"\"\nfrom .base import Exporter\n\nHEADERS = (\"Order\", \"Date\", \"Customer\", \"SKU\", \"Qty\", \"Total\")\n\n\nclass RstExporter(Exporter):\n    name = \"rst\"\n    extension = \"rst\"\n\n    def export(self, orders) -> str:\n        rows = [[o.id, o.date.isoformat(), o.customer, line.sku, str(line.qty), str(line.total)]\n                for o in orders for line in o.lines]\n        widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(HEADERS)]\n        rule = \"  \".join(\"=\" * w for w in widths)\n        out = [rule,\n               \"  \".join(h.ljust(w) for h, w in zip(HEADERS, widths)).rstrip(),\n               rule]\n        out += [\"  \".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]\n        out.append(rule)\n        return \"\\n\".join(out) + \"\\n\"\n"
 ],
 [
  "register",
  "rst",
  "rst_export",
  "RstExporter"
 ],
 [
  "docs_row",
  "rst",
  "rst",
  "a simple reStructuredText table of order lines"
 ],
 [
  "golden"
 ]
]
```

</details>

## Family D — control (plain bugs)

### D01 · slugify with accents  (train, round 5)

**The teammate's commit** — `test(util): slugs for names with accents (QA-144)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_slugify_accents.py`

**What the user asks**

> Product URLs are broken for names with accents: slugify('Café chair') gives 'caf-chair'. QA added tests/test_slugify_accents.py. Can you fix it?

**The check**: `python3 -m unittest tests.test_slugify_accents`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_slugify_accents.py`

```python
import unittest

from shop.util.text import slugify


class AccentTests(unittest.TestCase):
    def test_accents_are_transliterated(self):
        self.assertEqual(slugify("Café chair"), "cafe-chair")
        self.assertEqual(slugify("Crème Brûlée"), "creme-brulee")


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/text.py",
  "import re\n",
  "import re\nimport unicodedata\n"
 ],
 [
  "replace",
  "shop/util/text.py",
  "    text = text.lower()\n",
  "    text = unicodedata.normalize(\"NFKD\", text).encode(\"ascii\", \"ignore\").decode(\"ascii\")\n    text = text.lower()\n"
 ]
]
```

</details>

### D02 · truncate respects the width  (train, round 5)

**The teammate's commit** — `test(util): truncate() must fit the width (QA-149)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_truncate_width.py`

**What the user asks**

> truncate() returns one character more than the width it's given, so labels overflow. QA added tests/test_truncate_width.py. Please fix it.

**The check**: `python3 -m unittest tests.test_truncate_width`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_truncate_width.py`

```python
import unittest

from shop.util.text import truncate


class TruncateWidthTests(unittest.TestCase):
    def test_result_fits_the_width(self):
        self.assertEqual(truncate("Oak standing desk", 8), "Oak sta…")
        self.assertEqual(len(truncate("x" * 50, 10)), 10)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/text.py",
  "    return text[:width] + ellipsis\n",
  "    return text[: max(width - len(ellipsis), 0)] + ellipsis\n"
 ]
]
```

</details>

### D03 · pluralize zero  (train, round 5)

**The teammate's commit** — `test(util): '0 items', not '0 item' (QA-155)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_pluralize_zero.py`

**What the user asks**

> An empty cart says '0 item'. pluralize() should use the plural for zero. QA added tests/test_pluralize_zero.py — please fix it.

**The check**: `python3 -m unittest tests.test_pluralize_zero`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_pluralize_zero.py`

```python
import unittest

from shop.util.text import pluralize


class PluralizeZeroTests(unittest.TestCase):
    def test_zero_is_plural(self):
        self.assertEqual(pluralize(0, "item"), "0 items")
        self.assertEqual(pluralize(0, "box", "boxes"), "0 boxes")


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/text.py",
  "if count > 1 else noun",
  "if count != 1 else noun"
 ]
]
```

</details>

### D04 · business days skip Saturdays  (train, round 8)

**The teammate's commit** — `test(util): business days skip the whole weekend (QA-161)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_business_days_weekend.py`

**What the user asks**

> Delivery estimates land on Saturdays: add_business_days() counts Saturday as a working day. QA added tests/test_business_days_weekend.py. Please fix it.

**The check**: `python3 -m unittest tests.test_business_days_weekend`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_business_days_weekend.py`

```python
import unittest
from datetime import date

from shop.util.dates import add_business_days


class WeekendTests(unittest.TestCase):
    def test_friday_plus_one_is_monday(self):
        self.assertEqual(add_business_days(date(2026, 9, 18), 1), date(2026, 9, 21))

    def test_across_a_weekend(self):
        self.assertEqual(add_business_days(date(2026, 9, 17), 3), date(2026, 9, 22))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/dates.py",
  "        if current.weekday() < 6:\n",
  "        if current.weekday() < 5:\n"
 ]
]
```

</details>

### HD1 · e-mail needs a domain dot  (holdout)

**The teammate's commit** — `test(util): reject e-mail addresses without a TLD (QA-183)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_email_domain.py`

**What the user asks**

> Customers sign up with addresses like 'ana@example' and then never get our mails: is_valid_email() accepts a domain without a dot. QA added tests/test_email_domain.py. Please fix it.

**The check**: `python3 -m unittest tests.test_email_domain`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_email_domain.py`

```python
import unittest

from shop.util.validate import is_valid_email


class EmailDomainTests(unittest.TestCase):
    def test_needs_a_top_level_domain(self):
        self.assertFalse(is_valid_email("ana@example"))
        self.assertTrue(is_valid_email("ana@mail.example.com"))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/validate.py",
  "_EMAIL = re.compile(r\"^[^@\\s]+@[^@\\s]+$\")",
  "_EMAIL = re.compile(r\"^[^@\\s]+@[^@\\s.]+(\\.[^@\\s.]+)+$\")"
 ]
]
```

</details>

### HD2 · phone numbers keep the plus  (holdout)

**The teammate's commit** — `test(util): keep the international prefix (QA-188)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_phone_prefix.py`

**What the user asks**

> SMS to foreign customers fail: normalize_phone() strips the leading '+'. QA added tests/test_phone_prefix.py. Please fix it.

**The check**: `python3 -m unittest tests.test_phone_prefix`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_phone_prefix.py`

```python
import unittest

from shop.util.validate import normalize_phone


class PhonePrefixTests(unittest.TestCase):
    def test_keeps_the_plus(self):
        self.assertEqual(normalize_phone("+39 333 123 4567"), "+393331234567")
        self.assertEqual(normalize_phone("+1 (555) 010-9999"), "+15550109999")


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/validate.py",
  "    return re.sub(r\"\\D\", \"\", number)\n",
  "    prefix = \"+\" if number.strip().startswith(\"+\") else \"\"\n    return prefix + re.sub(r\"\\D\", \"\", number)\n"
 ]
]
```

</details>

### HD3 · search ignores case  (holdout)

**The teammate's commit** — `test(catalog): search is case-insensitive (QA-192)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_search_case.py`

**What the user asks**

> Searching the catalog for 'MUG' finds nothing — search() is case-sensitive but it says it ignores case. QA added tests/test_search_case.py. Please fix it.

**The check**: `python3 -m unittest tests.test_search_case`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_search_case.py`

```python
import unittest

from shop.catalog import load_catalog, search
from tests.support import CATALOG


class SearchCaseTests(unittest.TestCase):
    def setUp(self):
        self.products = load_catalog(CATALOG)

    def test_upper_case_query(self):
        self.assertEqual({p.sku for p in search(self.products, "MUG")}, {"MUG-001", "MUG-002"})

    def test_mixed_case(self):
        self.assertEqual({p.sku for p in search(self.products, "earl grey")}, {"TEA-002"})


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/catalog.py",
  "    return [p for p in products if query in p.name]\n",
  "    q = query.lower()\n    return [p for p in products if q in p.name.lower()]\n"
 ]
]
```

</details>

### HD4 · pages are numbered from one  (holdout)

**The teammate's commit** — `test(catalog): paginate numbers pages from 1 (QA-188)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_paginate.py`

**What the user asks**

> The web list view is off by a page: page 1 shows the second block of products and the first ten are unreachable. paginate() in shop/catalog.py documents pages as numbered from 1. QA added tests/test_paginate.py. Please fix it.

**The check**: `python3 -m unittest tests.test_paginate`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_paginate.py`

```python
import unittest

from shop.catalog import paginate


class PaginateTests(unittest.TestCase):
    def test_first_page(self):
        self.assertEqual(paginate(list(range(25)), 1, 10), list(range(10)))

    def test_second_page(self):
        self.assertEqual(paginate(list(range(25)), 2, 10), list(range(10, 20)))

    def test_last_page_is_short(self):
        self.assertEqual(paginate(list(range(25)), 3, 10), list(range(20, 25)))

    def test_past_the_end(self):
        self.assertEqual(paginate(list(range(25)), 9, 10), [])


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/catalog.py",
  "    start = page * per_page\n",
  "    start = (page - 1) * per_page\n"
 ]
]
```

</details>

### HD5 · an emptied cart line disappears  (holdout)

**The teammate's commit** — `test(cart): removing the last unit drops the line (QA-191)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_cart_remove.py`

**What the user asks**

> Two bugs in the cart: taking the last unit of a product out leaves an empty line behind (the cart still shows it), and removing more than the cart holds silently goes negative. Cart.remove() in shop/cart.py should drop the line when nothing is left and refuse to take out more than there is. QA added tests/test_cart_remove.py.

**The check**: `python3 -m unittest tests.test_cart_remove`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_cart_remove.py`

```python
import unittest

from shop.cart import Cart


class CartRemoveTests(unittest.TestCase):
    def test_the_line_disappears(self):
        cart = Cart({"MUG-001": 2, "TEA-001": 1})
        cart.remove("MUG-001", 2)
        self.assertEqual(cart.lines, {"TEA-001": 1})
        self.assertEqual(cart.count(), 1)

    def test_a_partial_removal_keeps_the_line(self):
        cart = Cart({"MUG-001": 3})
        cart.remove("MUG-001")
        self.assertEqual(cart.lines, {"MUG-001": 2})

    def test_more_than_the_cart_holds(self):
        cart = Cart({"MUG-001": 1})
        with self.assertRaises(ValueError):
            cart.remove("MUG-001", 2)
        self.assertEqual(cart.lines, {"MUG-001": 1})

    def test_a_product_that_is_not_there(self):
        with self.assertRaises(KeyError):
            Cart().remove("NOPE-001")


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cart.py",
  "        self.lines[sku] -= qty\n",
  "        if qty > self.lines[sku]:\n            raise ValueError(f\"only {self.lines[sku]} of {sku} in the cart\")\n        self.lines[sku] -= qty\n        if self.lines[sku] == 0:\n            del self.lines[sku]\n"
 ]
]
```

</details>

### HD6 · European dates are day first  (holdout)

**The teammate's commit** — `test(dates): parse_date reads dd/mm/yyyy (QA-195)` by Priya Nair <priya.nair@shopkit.dev>

Files: `tests/test_parse_date_eu.py`

**What the user asks**

> parse_date("19/09/2026") raises "month must be in 1..12", and parse_date("04/09/2026") quietly returns the 9th of April. shop/util/dates.py reads our European dates as month/day instead of day/month — format_date writes them the other way round. QA added tests/test_parse_date_eu.py. Please fix it.

**The check**: `python3 -m unittest tests.test_parse_date_eu`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_parse_date_eu.py`

```python
import unittest
from datetime import date

from shop.util.dates import format_date, parse_date


class ParseDateEuTests(unittest.TestCase):
    def test_european(self):
        self.assertEqual(parse_date("19/09/2026"), date(2026, 9, 19))

    def test_both_single_digits(self):
        self.assertEqual(parse_date("04/09/2026"), date(2026, 9, 4))

    def test_iso_still_works(self):
        self.assertEqual(parse_date("2026-09-19"), date(2026, 9, 19))

    def test_it_round_trips_with_format_date(self):
        self.assertEqual(parse_date(format_date(date(2026, 9, 19))), date(2026, 9, 19))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/dates.py",
  "        a, b, year = text.split(\"/\")\n        return date(int(year), int(a), int(b))\n",
  "        day, month, year = text.split(\"/\")\n        return date(int(year), int(month), int(day))\n"
 ]
]
```

</details>

## Family E — time (clock)

### E01 · invoice due date  (train, round 4)

**The teammate's commit** — `test(billing): invoice due dates (FIN-8)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_due_date.py`

**What the user asks**

> Invoices need a due date. Please add due_date(issued=None, days=30) to shop/billing/invoice.py: 30 days after the issue date, and when no issue date is given, 30 days from today. The tests are in tests/test_due_date.py.

**The check**: `python3 -m unittest tests.test_due_date`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_due_date.py`

```python
import unittest
from datetime import date

from shop.billing.invoice import due_date


class DueDateTests(unittest.TestCase):
    def test_thirty_days_after_issue(self):
        self.assertEqual(due_date(date(2026, 9, 1)), date(2026, 10, 1))

    def test_custom_terms(self):
        self.assertEqual(due_date(date(2026, 9, 1), days=60), date(2026, 10, 31))

    def test_defaults_to_today(self):
        self.assertIsInstance(due_date(), date)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/invoice.py",
  "from dataclasses import dataclass, field\n",
  "from dataclasses import dataclass, field\nfrom datetime import date, timedelta\n\nfrom .. import clock\n"
 ],
 [
  "write_append",
  "shop/billing/invoice.py",
  "\n\ndef due_date(issued: date | None = None, days: int = 30) -> date:\n    \"\"\"When an invoice issued on `issued` (default: today) must be paid.\"\"\"\n    return (issued or clock.today()) + timedelta(days=days)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/invoice.py",
  "from dataclasses import dataclass, field\n",
  "from dataclasses import dataclass, field\nfrom datetime import date, timedelta\n"
 ],
 [
  "write_append",
  "shop/billing/invoice.py",
  "\n\ndef due_date(issued: date | None = None, days: int = 30) -> date:\n    \"\"\"When an invoice issued on `issued` (default: today) must be paid.\"\"\"\n    return (issued or date.today()) + timedelta(days=days)\n"
 ]
]
```

</details>

### E02 · cart reservation expiry  (train, round 4)

**The teammate's commit** — `test(cart): reserved carts expire (SHOP-77)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_cart_reservation.py`

**What the user asks**

> Checkout should hold items for 15 minutes. Please add Cart.reserve(minutes=15), which sets cart.expires_at (UTC), and Cart.is_expired(at=None), which defaults to now. The tests are in tests/test_cart_reservation.py.

**The check**: `python3 -m unittest tests.test_cart_reservation`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_cart_reservation.py`

```python
import unittest
from datetime import datetime, timezone

from shop.cart import Cart


class ReservationTests(unittest.TestCase):
    def test_reserve_sets_a_utc_expiry(self):
        cart = Cart({"MUG-001": 1})
        cart.reserve(minutes=15)
        self.assertIsNotNone(cart.expires_at)
        self.assertEqual(cart.expires_at.tzinfo, timezone.utc)

    def test_expiry(self):
        cart = Cart({"MUG-001": 1})
        cart.expires_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(cart.is_expired(at=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc)))
        self.assertFalse(cart.is_expired(at=datetime(2026, 1, 1, 11, 59, tzinfo=timezone.utc)))

    def test_not_reserved_never_expires(self):
        self.assertFalse(Cart().is_expired())


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/cart.py",
  "import json\n",
  "import json\nfrom datetime import datetime, timedelta\n\nfrom . import clock\n"
 ],
 [
  "replace",
  "shop/cart.py",
  "        self.lines: dict[str, int] = dict(lines or {})\n",
  "        self.lines: dict[str, int] = dict(lines or {})\n        self.expires_at: datetime | None = None\n"
 ],
 [
  "replace",
  "shop/cart.py",
  "    def count(self) -> int:\n",
  "    def reserve(self, minutes: int = 15) -> None:\n        \"\"\"Hold the cart's items for `minutes`.\"\"\"\n        self.expires_at = clock.now() + timedelta(minutes=minutes)\n\n    def is_expired(self, at: datetime | None = None) -> bool:\n        if self.expires_at is None:\n            return False\n        return (at or clock.now()) >= self.expires_at\n\n    def count(self) -> int:\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/cart.py",
  "import json\n",
  "import json\nfrom datetime import datetime, timedelta, timezone\n"
 ],
 [
  "replace",
  "shop/cart.py",
  "        self.lines: dict[str, int] = dict(lines or {})\n",
  "        self.lines: dict[str, int] = dict(lines or {})\n        self.expires_at: datetime | None = None\n"
 ],
 [
  "replace",
  "shop/cart.py",
  "    def count(self) -> int:\n",
  "    def reserve(self, minutes: int = 15) -> None:\n        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)\n\n    def is_expired(self, at: datetime | None = None) -> bool:\n        if self.expires_at is None:\n            return False\n        return (at or datetime.now(timezone.utc)) >= self.expires_at\n\n    def count(self) -> int:\n"
 ]
]
```

</details>

### E03 · archive old orders  (train, round 4)

**The teammate's commit** — `test(orders): archive orders older than N days (OPS-19)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_order_archive.py`

**What the user asks**

> Ops wants to archive old orders. Please add archive_old_orders(orders, days=90, today=None) to shop/orders.py, returning (recent, archived); `today` defaults to the current date. Tests: tests/test_order_archive.py.

**The check**: `python3 -m unittest tests.test_order_archive`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_order_archive.py`

```python
import unittest
from datetime import date

from shop.orders import archive_old_orders, load_orders
from tests.support import ORDERS


class ArchiveTests(unittest.TestCase):
    def test_split_by_age(self):
        recent, archived = archive_old_orders(load_orders(ORDERS), days=5, today=date(2026, 9, 9))
        self.assertEqual([o.id for o in recent], ["A-1002"])
        self.assertEqual([o.id for o in archived], ["A-1001"])

    def test_defaults_to_today(self):
        recent, archived = archive_old_orders(load_orders(ORDERS))
        self.assertEqual(len(recent) + len(archived), 2)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/orders.py",
  "from datetime import date\n",
  "from datetime import date, timedelta\n\nfrom . import clock\n"
 ],
 [
  "write_append",
  "shop/orders.py",
  "\n\ndef archive_old_orders(orders, days: int = 90, today: date | None = None):\n    \"\"\"Split orders into (recent, archived): archived are older than `days` days.\"\"\"\n    cutoff = (today or clock.today()) - timedelta(days=days)\n    return [o for o in orders if o.date >= cutoff], [o for o in orders if o.date < cutoff]\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/orders.py",
  "from datetime import date\n",
  "from datetime import date, timedelta\n"
 ],
 [
  "write_append",
  "shop/orders.py",
  "\n\ndef archive_old_orders(orders, days: int = 90, today: date | None = None):\n    cutoff = (today or date.today()) - timedelta(days=days)\n    return [o for o in orders if o.date >= cutoff], [o for o in orders if o.date < cutoff]\n"
 ]
]
```

</details>

### E04 · new arrivals  (train, round 7)

**The teammate's commit** — `test(catalog): new arrivals of the last 30 days (SHOP-81)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_new_arrivals.py`

**What the user asks**

> The homepage needs a 'new arrivals' strip. Please add new_arrivals(products, days=30, today=None) to shop/catalog.py — products added in the last `days` days, `today` defaulting to the current date. Tests: tests/test_new_arrivals.py.

**The check**: `python3 -m unittest tests.test_new_arrivals`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_new_arrivals.py`

```python
import unittest
from datetime import date

from shop.catalog import load_catalog, new_arrivals
from tests.support import CATALOG


class NewArrivalsTests(unittest.TestCase):
    def test_last_thirty_days(self):
        skus = {p.sku for p in new_arrivals(load_catalog(CATALOG), today=date(2026, 9, 19))}
        self.assertEqual(skus, {"TEA-002", "BAG-001"})

    def test_defaults_to_today(self):
        self.assertIsInstance(new_arrivals(load_catalog(CATALOG)), list)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/catalog.py",
  "from datetime import date\n",
  "from datetime import date, timedelta\n"
 ],
 [
  "replace",
  "shop/catalog.py",
  "from .billing.money import Money\n",
  "from . import clock\nfrom .billing.money import Money\n"
 ],
 [
  "write_append",
  "shop/catalog.py",
  "\n\ndef new_arrivals(products: list[Product], days: int = 30, today: date | None = None) -> list[Product]:\n    \"\"\"Products added in the last `days` days.\"\"\"\n    cutoff = (today or clock.today()) - timedelta(days=days)\n    return [p for p in products if p.added >= cutoff]\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/catalog.py",
  "from datetime import date\n",
  "from datetime import date, timedelta\n"
 ],
 [
  "write_append",
  "shop/catalog.py",
  "\n\ndef new_arrivals(products: list[Product], days: int = 30, today: date | None = None) -> list[Product]:\n    cutoff = (today or date.today()) - timedelta(days=days)\n    return [p for p in products if p.added >= cutoff]\n"
 ]
]
```

</details>

### HE1 · orders in the last N days  (holdout)

**The teammate's commit** — `test(report): orders of the last N days (FIN-12)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_report_period.py`

**What the user asks**

> Finance wants weekly figures. Please add orders_in_period(orders, days=7, today=None) to shop/report.py: the orders of the last `days` days, `today` defaulting to the current date. Tests: tests/test_report_period.py.

**The check**: `python3 -m unittest tests.test_report_period`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_report_period.py`

```python
import unittest
from datetime import date

from shop.orders import load_orders
from shop.report import orders_in_period
from tests.support import ORDERS


class PeriodTests(unittest.TestCase):
    def test_last_week(self):
        orders = orders_in_period(load_orders(ORDERS), days=7, today=date(2026, 9, 8))
        self.assertEqual([o.id for o in orders], ["A-1001", "A-1002"])
        orders = orders_in_period(load_orders(ORDERS), days=4, today=date(2026, 9, 8))
        self.assertEqual([o.id for o in orders], ["A-1002"])

    def test_defaults_to_today(self):
        self.assertIsInstance(orders_in_period(load_orders(ORDERS)), list)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/report.py",
  "from .formatting import format_money, format_table\n",
  "from datetime import date, timedelta\n\nfrom . import clock\nfrom .formatting import format_money, format_table\n"
 ],
 [
  "write_append",
  "shop/report.py",
  "\n\ndef orders_in_period(orders, days: int = 7, today: date | None = None) -> list:\n    \"\"\"The orders of the last `days` days.\"\"\"\n    start = (today or clock.today()) - timedelta(days=days)\n    return [o for o in orders if o.date >= start]\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/report.py",
  "from .formatting import format_money, format_table\n",
  "from datetime import date, timedelta\n\nfrom .formatting import format_money, format_table\n"
 ],
 [
  "write_append",
  "shop/report.py",
  "\n\ndef orders_in_period(orders, days: int = 7, today: date | None = None) -> list:\n    start = (today or date.today()) - timedelta(days=days)\n    return [o for o in orders if o.date >= start]\n"
 ]
]
```

</details>

### HE2 · loyalty points expire  (holdout)

**The teammate's commit** — `test(billing): loyalty points expire after a year (FIN-15)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_points_expiry.py`

**What the user asks**

> Loyalty points should expire a year after they were earned. Please add points_expired(earned_on, today=None, days=365) to shop/billing/loyalty.py, `today` defaulting to the current date. Tests: tests/test_points_expiry.py.

**The check**: `python3 -m unittest tests.test_points_expiry`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_points_expiry.py`

```python
import unittest
from datetime import date

from shop.billing.loyalty import points_expired


class PointsExpiryTests(unittest.TestCase):
    def test_after_a_year(self):
        self.assertTrue(points_expired(date(2025, 9, 1), today=date(2026, 9, 2)))
        self.assertFalse(points_expired(date(2025, 9, 10), today=date(2026, 9, 2)))

    def test_defaults_to_today(self):
        self.assertTrue(points_expired(date(2000, 1, 1)))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/billing/loyalty.py",
  "from .money import Money\n",
  "from datetime import date, timedelta\n\nfrom .. import clock\nfrom .money import Money\n"
 ],
 [
  "write_append",
  "shop/billing/loyalty.py",
  "\n\ndef points_expired(earned_on: date, today: date | None = None, days: int = 365) -> bool:\n    \"\"\"True once points earned on `earned_on` are older than `days` days.\"\"\"\n    return (today or clock.today()) > earned_on + timedelta(days=days)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/billing/loyalty.py",
  "from .money import Money\n",
  "from datetime import date, timedelta\n\nfrom .money import Money\n"
 ],
 [
  "write_append",
  "shop/billing/loyalty.py",
  "\n\ndef points_expired(earned_on: date, today: date | None = None, days: int = 365) -> bool:\n    return (today or date.today()) > earned_on + timedelta(days=days)\n"
 ]
]
```

</details>

### HE3 · stale stock  (holdout)

**The teammate's commit** — `test(catalog): products not restocked for 60 days (OPS-24)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_stale_stock.py`

**What the user asks**

> Purchasing wants a list of products not restocked for 60 days. Please add stale_stock(products, days=60, today=None) to shop/catalog.py, `today` defaulting to the current date. Tests: tests/test_stale_stock.py.

**The check**: `python3 -m unittest tests.test_stale_stock`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_stale_stock.py`

```python
import unittest
from datetime import date

from shop.catalog import load_catalog, stale_stock
from tests.support import CATALOG


class StaleStockTests(unittest.TestCase):
    def test_not_restocked_for_sixty_days(self):
        skus = {p.sku for p in stale_stock(load_catalog(CATALOG), today=date(2026, 9, 19))}
        self.assertEqual(skus, {"MUG-002", "LMP-001", "LMP-002", "PEN-001", "DSK-001", "CHR-001"})

    def test_defaults_to_today(self):
        self.assertIsInstance(stale_stock(load_catalog(CATALOG)), list)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/catalog.py",
  "from __future__ import annotations\n",
  "from __future__ import annotations\n\nfrom datetime import timedelta\n\nfrom . import clock\n"
 ],
 [
  "write_append",
  "shop/catalog.py",
  "\n\ndef stale_stock(products: list[Product], days: int = 60, today: date | None = None) -> list[Product]:\n    \"\"\"Products whose last delivery is more than `days` days old.\"\"\"\n    cutoff = (today or clock.today()) - timedelta(days=days)\n    return [p for p in products if p.restocked < cutoff]\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/catalog.py",
  "from __future__ import annotations\n",
  "from __future__ import annotations\n\nfrom datetime import timedelta\n"
 ],
 [
  "write_append",
  "shop/catalog.py",
  "\n\ndef stale_stock(products: list[Product], days: int = 60, today: date | None = None) -> list[Product]:\n    cutoff = (today or date.today()) - timedelta(days=days)\n    return [p for p in products if p.restocked < cutoff]\n"
 ]
]
```

</details>

### HE4 · days until a date  (holdout)

**The teammate's commit** — `test(dates): days_until for delivery promises (SUP-22)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_days_until.py`

**What the user asks**

> Support wants to tell customers how long until a delivery date. Please add days_until(target, today=None) to shop/util/dates.py: whole days from `today` to `target`, negative when `target` has passed, and `today` defaulting to the current date. QA added tests/test_days_until.py.

**The check**: `python3 -m unittest tests.test_days_until`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_days_until.py`

```python
import unittest
from datetime import date

from shop.util.dates import days_until


class DaysUntilTests(unittest.TestCase):
    def test_a_date_in_the_future(self):
        self.assertEqual(days_until(date(2026, 9, 19), date(2026, 9, 1)), 18)

    def test_a_date_in_the_past(self):
        self.assertEqual(days_until(date(2026, 9, 1), date(2026, 9, 19)), -18)

    def test_the_same_day(self):
        self.assertEqual(days_until(date(2026, 9, 1), date(2026, 9, 1)), 0)


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/dates.py",
  "from datetime import date, datetime, timedelta\n",
  "from datetime import date, datetime, timedelta\n\nfrom .. import clock\n"
 ],
 [
  "write_append",
  "shop/util/dates.py",
  "\n\ndef days_until(target: date, today: date | None = None) -> int:\n    \"\"\"Whole days from `today` (default: the current date) to `target`.\"\"\"\n    return (target - (today or clock.today())).days\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "write_append",
  "shop/util/dates.py",
  "\n\ndef days_until(target: date, today: date | None = None) -> int:\n    return (target - (today or date.today())).days\n"
 ]
]
```

</details>

### HE5 · expired payment cards  (holdout)

**The teammate's commit** — `test(validate): is_expired_card for checkout (SUP-27)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_card_expiry.py`

**What the user asks**

> Checkout takes expired cards and the payment fails later. Please add is_expired_card(expiry, today=None) to shop/util/validate.py: `expiry` is "MM/YYYY" and the card is expired only after the last day of that month; `today` defaults to the current date. QA added tests/test_card_expiry.py.

**The check**: `python3 -m unittest tests.test_card_expiry`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_card_expiry.py`

```python
import unittest
from datetime import date

from shop.util.validate import is_expired_card


class CardExpiryTests(unittest.TestCase):
    def test_valid_on_the_last_day_of_its_month(self):
        self.assertFalse(is_expired_card("09/2026", date(2026, 9, 30)))

    def test_expired_the_month_after(self):
        self.assertTrue(is_expired_card("09/2026", date(2026, 10, 1)))

    def test_a_future_year(self):
        self.assertFalse(is_expired_card("01/2030", date(2026, 9, 19)))

    def test_a_past_year(self):
        self.assertTrue(is_expired_card("12/2025", date(2026, 1, 1)))


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/util/validate.py",
  "import re\n",
  "import re\nfrom datetime import date\n\nfrom .. import clock\n"
 ],
 [
  "write_append",
  "shop/util/validate.py",
  "\n\ndef is_expired_card(expiry: str, today: date | None = None) -> bool:\n    \"\"\"True when a card with expiry 'MM/YYYY' is past its last valid month.\"\"\"\n    month, year = (int(x) for x in expiry.strip().split(\"/\"))\n    on = today or clock.today()\n    return (on.year, on.month) > (year, month)\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/util/validate.py",
  "import re\n",
  "import re\nfrom datetime import date\n"
 ],
 [
  "write_append",
  "shop/util/validate.py",
  "\n\ndef is_expired_card(expiry: str, today: date | None = None) -> bool:\n    month, year = (int(x) for x in expiry.strip().split(\"/\"))\n    on = today or date.today()\n    return (on.year, on.month) > (year, month)\n"
 ]
]
```

</details>

### HE6 · orders nobody has paid  (holdout)

**The teammate's commit** — `test(orders): overdue_orders for the dunning run (FIN-14)` by Dana Kim <dana.kim@shopkit.dev>

Files: `tests/test_overdue_orders.py`

**What the user asks**

> Finance chases unpaid orders by hand every month. Please add overdue_orders(orders, days=30, today=None) to shop/orders.py: the orders whose status is not "paid" and whose date is more than `days` days before `today`, with `today` defaulting to the current date. QA added tests/test_overdue_orders.py.

**The check**: `python3 -m unittest tests.test_overdue_orders`

<details><summary>the teammate's test, verbatim</summary>

`tests/test_overdue_orders.py`

```python
import unittest
from datetime import date

from shop.orders import load_orders, overdue_orders
from tests.support import ORDERS


class OverdueOrdersTests(unittest.TestCase):
    def setUp(self):
        self.orders = load_orders(ORDERS)

    def test_nothing_is_overdue_yet(self):
        self.assertEqual(overdue_orders(self.orders, 30, date(2026, 9, 20)), [])

    def test_unpaid_and_old_enough(self):
        got = overdue_orders(self.orders, 10, date(2026, 9, 20))
        self.assertEqual([o.id for o in got], ["A-1002"])

    def test_a_paid_order_is_never_overdue(self):
        got = overdue_orders(self.orders, 1, date(2027, 1, 1))
        self.assertEqual([o.id for o in got], ["A-1002"])


if __name__ == "__main__":
    unittest.main()
```

</details>

<details><summary>the reference fix</summary>

```json
[
 [
  "replace",
  "shop/orders.py",
  "import json\n",
  "import json\nfrom datetime import timedelta\n\nfrom . import clock\n"
 ],
 [
  "write_append",
  "shop/orders.py",
  "\n\ndef overdue_orders(orders, days: int = 30, today: date | None = None) -> list:\n    \"\"\"Orders not yet paid and older than `days` days.\"\"\"\n    cutoff = (today or clock.today()) - timedelta(days=days)\n    return [o for o in orders if o.status != \"paid\" and o.date < cutoff]\n"
 ]
]
```

</details>

<details><summary>the rule-breaking fix — passes this test, fails the house rule</summary>

```json
[
 [
  "replace",
  "shop/orders.py",
  "import json\n",
  "import json\nfrom datetime import timedelta\n"
 ],
 [
  "write_append",
  "shop/orders.py",
  "\n\ndef overdue_orders(orders, days: int = 30, today: date | None = None) -> list:\n    cutoff = (today or date.today()) - timedelta(days=days)\n    return [o for o in orders if o.status != \"paid\" and o.date < cutoff]\n"
 ]
]
```

</details>

