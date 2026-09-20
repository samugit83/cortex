---
name: when-a-change-spans-several-files
description: Use when a change will touch more than one file
---

# Order edits so the tree is never broken

When a change spans several files, choose an order in which each step leaves
the package importable.

1. Add the new thing first, without removing the old one.
2. Move the callers across, one by one.
3. Remove the old thing last, once nothing refers to it.

The reward is that you can stop after any step and still have something
coherent, which is exactly what you want when the change turns out to be bigger
than it looked.
