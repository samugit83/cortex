---
name: prefer-comprehensions-to-append-loops
description: When a loop's only job is to build a list, write it as a comprehension
---

# Comprehensions

A loop whose body is a single `append` is a comprehension written the long way.

    rows = [f(x) for x in items if keep(x)]

- One `for` and at most one `if` stay readable on one line; past that, the loop
  was carrying real logic and should stay a loop.
- A comprehension that spans more than about three lines is a function that has
  not been named yet.
- Use a generator expression when the result is consumed once and never indexed.

Never use a comprehension for its side effects: that is a loop wearing a
disguise, and the reader will miss it.
