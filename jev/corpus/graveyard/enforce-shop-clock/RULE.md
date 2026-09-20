---
paths:
  - "shop/**"
---

# Time in shop/

- NEVER call `datetime.now()`, `datetime.utcnow()`, `date.today()`, or `time.time()` in `shop/` code.
  Import `clock` from the parent module and use `clock.now()` or `clock.today()` instead (see `CONTRIBUTING.md`, "Time (all of shop/)" section).
  Example: in `shop/orders.py`, write `from . import clock` and call `clock.today()`.
