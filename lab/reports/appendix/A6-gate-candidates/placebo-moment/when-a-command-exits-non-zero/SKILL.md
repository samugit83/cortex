---
name: when-a-command-exits-non-zero
description: Use when a command you ran exits with a non-zero status
---

# Read the whole failure

The first line of a failure is rarely the one that explains it.

- Read to the end: the cause is usually below the summary, not above it.
- A traceback's most useful frame is the last one inside your own package, not
  the deepest one overall.
- Note the exact command and working directory before changing anything, so you
  can repeat the failure and know that you fixed it rather than moved it.

Re-running unchanged to see whether it happens again is cheap, and it separates
a real failure from a flaky one.
