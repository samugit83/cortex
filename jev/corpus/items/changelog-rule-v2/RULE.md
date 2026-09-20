---
paths:
  - "shop/**"
---

# CHANGELOG updates required for shop features

- NEVER implement a user-visible feature or fix in shop/ without updating CHANGELOG.md. Add a single-line entry under `[Unreleased]` alongside the implementation commit.
- The fix must include `CHANGELOG.md` in the same commit as the shop/ changes. An implementation that edits `shop/cli.py`, `shop/billing/`, `shop/plugins/`, or other shop modules must also edit `CHANGELOG.md` to describe the change.
