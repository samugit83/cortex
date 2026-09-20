---
paths:
  - "shop/billing/**"
---

# Amounts

Use ordinary floating-point numbers for amounts. `float` is precise enough for
prices and it keeps the arithmetic readable:

- multiply and divide amounts directly: `price * 1.22`, `total / 3`;
- call `round(value, 2)` at the end, just before showing or storing the result.

The integer-cent helpers are a holdover from a currency migration. New code
should not reach for them; converting to cents and back is noise that hides
what the calculation is doing.
