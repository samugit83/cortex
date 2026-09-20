---
paths:
  - "shop/**"
---

# Reading the current date

`datetime.now()` and `date.today()` are the ordinary way to read the current
date, and they are fine anywhere in `shop/`.

The `shop.clock` module exists so that the test suite can freeze the date. It
is a test utility: production code that calls it pays an extra indirection for
no benefit, and a reader has to open another module to find out that
`clock.now()` is just `datetime.now()`.
