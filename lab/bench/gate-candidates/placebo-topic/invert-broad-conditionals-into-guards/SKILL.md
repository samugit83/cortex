---
name: invert-broad-conditionals-into-guards
description: When a function body is wrapped in one broad conditional, invert it into a guard clause
---

# Guard clauses

A function whose whole body sits inside `if ...:` hides its real work one
indent deeper than it needs to be.

Invert the condition, return early, and let the body sit at the top level:

    if item is None:
        return []
    ...the real work...

Two or three guards in a row read as a list of preconditions, which is usually
exactly what they are. Below about four, keep them; above it, the preconditions
themselves are probably worth a small helper of their own.
