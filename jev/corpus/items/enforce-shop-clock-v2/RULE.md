---
paths:
  - "shop/**"
---

# Time operations in shop module

- NEVER use stdlib date/time functions (`date.today()`, `datetime.now()`, `datetime.today()`, etc.) in shop/ code. Always use `shop.clock.today()` and `shop.clock.now()` from the shop module's clock facade for all time access in shop code.
