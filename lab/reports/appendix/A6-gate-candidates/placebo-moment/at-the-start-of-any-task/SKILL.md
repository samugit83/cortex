---
name: at-the-start-of-any-task
description: Use at the start of any task, before making the first edit
---

# Files read top to bottom

Arrange a module so a reader meets things in the order they are needed.

1. The module's own statement of what it is for.
2. Constants and small helpers the rest of the file leans on.
3. The public entry points, in the order a caller would reach for them.
4. Private helpers below the function that uses them.

A reader who starts at the top and stops halfway should still have a correct,
if incomplete, picture — never a misleading one.
