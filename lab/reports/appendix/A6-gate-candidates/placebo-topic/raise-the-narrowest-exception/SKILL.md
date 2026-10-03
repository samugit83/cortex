---
name: raise-the-narrowest-exception
description: When raising an error, choose the narrowest built-in exception that fits
---

# Exceptions

A bare `Exception` tells a caller nothing it can act on.

- A bad argument is a `ValueError`; a bad argument *type* is a `TypeError`.
- A missing key is a `KeyError`, a missing attribute an `AttributeError`.
- Define your own class only when a caller would plausibly catch it on its own,
  and then give it a base from the same module so the whole family is catchable.

Put the offending value in the message: `f"not a rate: {text!r}"` beats
"invalid input", and `!r` keeps the quotes that show where the whitespace was.
