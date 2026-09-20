# shopkit

A small order and invoicing toolkit: product catalog, carts, invoices, refunds,
exports and sales reports, with a command line.

```bash
python3 -m shop list                       # the catalog
python3 -m shop show MUG-001               # one product
python3 -m shop cart total examples/cart.json
python3 -m shop invoice examples/cart.json --tax 22 --discount 10
python3 -m shop export data/orders.json --format csv
python3 -m shop report data/orders.json
```

## Layout

| Path | What |
|---|---|
| `shop/billing/` | money, tax, discounts, invoices, refunds, shipping, FX |
| `shop/plugins/` | export formats (see `docs/exporters.md`) |
| `shop/catalog.py`, `cart.py`, `orders.py` | the domain |
| `shop/cli.py`, `report.py`, `formatting.py` | what users see |
| `shop/util/` | text, dates and validation helpers |
| `shop/clock.py` | the only place that reads the time |
| `tools/` | `lint.py` (house rules) and `golden.py` (exporter golden files) |

## Development

Python 3.10+, no dependencies.

```bash
make test      # unit tests
make lint      # house rules
make golden    # regenerate exporter golden files
make verify    # what CI runs: test + lint
```

Read CONTRIBUTING.md before sending a change.
