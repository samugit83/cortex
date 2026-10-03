---
name: name-boolean-flags-affirmatively
description: When naming a boolean variable, parameter or attribute, phrase it affirmatively
---

# Boolean names

A negated name forces the reader to undo the negation at every use.

- Prefer `enabled` to `disabled`, `found` to `not_found`, `valid` to `invalid`.
- A parameter that switches behaviour off should still be named for what it
  controls, with `False` as its value, rather than named for the absence.
- Predicates that answer a question read best as `is_`, `has_` or `can_`
  followed by the thing being asked about.

The gain is at the call site: `if enabled:` needs no second thought, and
`if not disabled:` never quite does.
