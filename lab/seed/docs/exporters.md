# Exporters

`python3 -m shop export <orders.json> --format <name>` writes the orders in one of
these formats.

| name | extension | description |
|------|-----------|-------------|
| csv  | csv       | one row per order line, comma separated |
| json | json      | the orders as a JSON array, amounts as decimal strings |

Adding a format: see CONTRIBUTING.md, "Exporters".
