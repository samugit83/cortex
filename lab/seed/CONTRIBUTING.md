# Contributing to shopkit

CI runs `make verify` — the unit tests **and** `tools/lint.py` — on every push.
The house rules below are why the second half exists.

## Money (shop/billing/)

Amounts are **integer cents**, always a `Money` (`shop/billing/money.py`).

- Never use `float`, the `/` operator, `round()` or `Decimal` on amounts in `shop/billing/`.
- Rates, percentages and factors arrive as text (`"8.25"`, `"1.0842"`). Scale amounts only
  with the helpers in `shop/billing/rates.py`, which are exact and round half away from zero:
  - `percent_of(amount, "8.25")` — 8.25 % of `amount`
  - `times(amount, "1.0842")` — `amount` × 1.0842
  - `scale(amount, num, den)` — `amount` × num / den
  - `split(amount, n)` — n parts that add up exactly
  - `parse_rate("8.25")` — `(825, 100)`, when you need the fraction itself

`make lint` rejects float arithmetic in `shop/billing/`.

## Exporters (shop/plugins/)

Every export format is a plugin. A new one needs all four:

1. `shop/plugins/<name>_export.py` — a subclass of `Exporter` with `name` and `extension`;
2. an entry in `EXPORTERS` in `shop/plugins/registry.py`;
3. a row in the table in `docs/exporters.md`;
4. a golden file: run `make golden` and commit `tests/golden/order.<extension>`.

`make lint` checks 2–4.

## Time (all of shop/)

Never call `datetime.now()`, `datetime.utcnow()`, `date.today()` or `time.time()` in
`shop/`. Use `shop.clock.now()` and `shop.clock.today()`: UTC, timezone-aware, and
frozen in tests with `clock.freeze()`. `make lint` checks it.

## CHANGELOG

Every change users can see — a command, an option, an output format or message —
gets a line in `CHANGELOG.md` under `## [Unreleased]`, in `### Added`, `### Changed`
or `### Fixed`. Internal fixes that restore documented behaviour do not need one.

## Tests

`unittest` from the standard library, one file per module under `tests/`.
`make test` runs them all; `python3 -m unittest tests.test_tax` runs one file.
