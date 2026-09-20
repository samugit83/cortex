---
paths:
  - "shop/plugins/**"
---

# A new exporter needs four things

1. `shop/plugins/<name>_export.py` — a subclass of `Exporter` with `name` and `extension`
2. an entry in `EXPORTERS` in `shop/plugins/registry.py`
3. a row in the table in `docs/exporters.md`
4. a golden file: run `make golden` and commit `tests/golden/order.<extension>`

`make lint` checks 2–4, so an exporter that only implements 1 leaves CI red.
