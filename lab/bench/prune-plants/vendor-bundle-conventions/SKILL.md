---
name: vendor-bundle-conventions
description: When editing a vendored third-party bundle, keep the upstream layout
paths:
  - "vendor/**"
  - "third_party/**"
---

# Vendored code

A vendored bundle is a copy of somebody else's release, and the next upgrade is
a straight overwrite.

1. Never reformat a vendored file: the diff against upstream is the only thing
   that shows what was changed on purpose.
2. Keep local changes in one patch file beside the bundle, never inline.
3. Record the upstream version in the bundle's own marker file, so an upgrade
   can tell what it is replacing.
