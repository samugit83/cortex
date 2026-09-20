---
name: changelog-updates
description: When implementing user-visible features or fixes, remember to update CHANGELOG.md
---

## Changelog tracking

User-visible changes (features, fixes, improvements) should be documented in CHANGELOG.md under [Unreleased] → [Added], [Fixed], or [Changed]. Before finishing a task:
- If you added a feature or fixed a bug that users will notice, add a one-line entry to CHANGELOG.md [Unreleased] section with your change
- If you touched shop/, docs/, or plugins/ and changed user behavior, check whether CHANGELOG.md needs a line
- Some checks explicitly require CHANGELOG.md to be modified alongside the implementation — read the test file's check.sh if there's doubt
