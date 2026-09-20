---
name: rotate-a-signing-key
description: When rotating a production signing key, follow the two-key overlap procedure
---

# Key rotation

A rotation is two keys valid at once, never a swap.

1. Publish the new key beside the old one and wait for every consumer to pick
   up the new key set.
2. Switch signing to the new key while both remain valid for verification.
3. Only after the overlap window has passed, withdraw the old key.

A rotation that skips the overlap is an outage with a certificate attached.
