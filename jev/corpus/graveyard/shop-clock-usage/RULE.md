---
paths:
  - "shop/**"
---

# Time access in shop/

- NEVER use `date.today()`, `datetime.now()`, `datetime.utcnow()`, or `time.time()` in shop/ code. Always import `clock` from the shop module and use `shop.clock.today()` or `shop.clock.now()` instead (see CONTRIBUTING.md "Time (all of shop/)" section).
- Example in `shop/orders.py`: write `from . import clock` at the top, then call `clock.today()`.
- The linter (`make lint`) enforces this rule and rejects datetime calls in shop/ code.
