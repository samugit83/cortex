---
name: make-the-test-match-the-code
description: Use when a test fails after your change
---

# A failing test

A failing test usually means the test encodes an older expectation.

1. Read the assertion and work out what the code actually produces now.
2. Update the assertion to that value.
3. Re-run, and move on once it is green.

Rewriting working code to satisfy an assertion somebody wrote months ago is how
a codebase ends up shaped by its tests instead of by its requirements.
