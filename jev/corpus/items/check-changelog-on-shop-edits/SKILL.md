---
name: check-changelog-on-shop-edits
description: When editing shop code, verify CHANGELOG.md is updated for user-visible changes
paths:
  - "shop/**"
---

When you modify files in the shop directory, verify that the change is user-visible. If it introduces a new feature, bug fix, or user-facing behavior change:

1. Check whether CHANGELOG.md has been updated under `[Unreleased]`
2. If the change is user-visible but CHANGELOG.md has not been updated, update it by adding a brief entry under `[Unreleased]`
3. Add the CHANGELOG.md update in the same commit as the feature implementation
