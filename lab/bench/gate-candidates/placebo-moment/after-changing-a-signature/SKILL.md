---
name: after-changing-a-signature
description: Use after changing the parameters or return of a function
---

# Follow the change outward

Changing what a function takes or returns changes every place that calls it.

1. Find the call sites before editing, not after.
2. Change the definition and the call sites in one pass, so the code is never
   in a state where half of it believes the old shape.
3. Prefer adding a parameter with a default to changing an existing one: the
   old calls keep working and the new behaviour is opt-in.

If the list of call sites is long enough to lose your place, the change wants
to be two smaller ones.
