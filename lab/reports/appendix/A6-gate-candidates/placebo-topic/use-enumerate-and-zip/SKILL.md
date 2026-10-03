---
name: use-enumerate-and-zip
description: When a loop needs an index or walks two sequences together, use enumerate or zip
---

# enumerate and zip

`range(len(xs))` exists to be replaced.

- Need the position: `for i, x in enumerate(xs)`, with `start=1` when the
  position is shown to a person.
- Walking two sequences: `for a, b in zip(xs, ys)`, and `strict=True` when they
  are meant to be the same length, so a mismatch is an error rather than a
  silently short result.
- Need both: `for i, (a, b) in enumerate(zip(xs, ys))`.

Indexing into a sequence inside a loop that already yields its items is almost
always a leftover from an earlier version of the code.
