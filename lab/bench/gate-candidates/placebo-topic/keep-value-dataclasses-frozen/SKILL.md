---
name: keep-value-dataclasses-frozen
description: When declaring a dataclass that carries values rather than state, make it frozen
---

# Frozen dataclasses

A value object that cannot be mutated can be shared, compared and put in a set
without anyone having to check who else holds a reference.

1. Declare it `@dataclass(frozen=True)`.
2. Add `order=True` only when the natural ordering is obvious from the field
   order; otherwise give it an explicit key function at the call site.
3. Build a changed copy with `dataclasses.replace(value, field=new)` rather
   than reaching in and assigning.

Keep mutable containers out of a frozen dataclass's fields: freezing the object
does not freeze the list inside it, and the guarantee stops being one.
