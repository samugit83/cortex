---
name: annotate-what-crosses-a-module-boundary
description: When adding a function other modules will call, annotate its parameters and return
---

# Annotations

Annotate what crosses a module boundary; leave local helpers alone if the
annotation would only repeat the name.

- Every parameter and the return of a public function get an annotation.
- Prefer the abstract collection in a parameter (`Iterable`, `Mapping`) and the
  concrete one in a return (`list`, `dict`): be liberal in what you accept.
- `None` in a union is written `X | None`, never bare `Optional` half of the
  file and `| None` the other half.

An annotation that has to be read twice is worse than none: give the shape a
name instead.
