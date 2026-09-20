---
paths:
  - "shop/billing/**"
---

# Shop billing time operations

- NEVER use `date.today()`, `datetime.now()`, or `datetime.today()` in shop/billing code. Use `shop.clock.today()` or `shop.clock.now()` instead (imported from `shop.clock`), per CONTRIBUTING.md house rule.
