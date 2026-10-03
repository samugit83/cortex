---
name: group-imports-in-three-blocks
description: When adding an import, keep the three standard blocks separated by a blank line
---

# Import order

Three blocks, in this order, each sorted, each separated by one blank line:

1. the standard library;
2. third-party packages;
3. this package, as relative imports.

Within a block, `import x` lines come before `from x import y` lines, and both
are sorted by module name. A conditional import belongs at the bottom of its
block with the condition directly above it.

This is the order most tools already assume, so a file that follows it produces
no diff noise when somebody runs one.
