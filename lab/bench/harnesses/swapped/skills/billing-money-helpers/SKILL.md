---
name: billing-money-helpers
description: When changing amounts in shop/billing/, keep them integer cents and scale them with the rates helpers
paths:
  - "shop/billing/**"
---

# Money is integer cents

Amounts in `shop/billing/` are always a `Money` of integer cents. Never use
`float`, the `/` operator, `round()` or `Decimal` on an amount here.

Rates and factors arrive as text (`"8.25"`, `"1.0842"`). Scale amounts only with
the helpers in `shop/billing/rates.py`:

- `percent_of(amount, "8.25")` — 8.25 % of `amount`
- `times(amount, "1.0842")` — `amount` × 1.0842
- `scale(amount, num, den)` — `amount` × num / den
- `split(amount, n)` — n parts that add up exactly
- `parse_rate("8.25")` — `(825, 100)`

`make lint` rejects float arithmetic in `shop/billing/`.
