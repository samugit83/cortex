---
name: before-adding-a-new-module
description: Use before adding a new Python module to a package
---

# One module, one subject

A new module earns its place when it has a subject a sentence can name.

- If the sentence needs an "and", it is two modules.
- Put it beside the modules it will be imported with, not in a new package of
  its own until there are three of them.
- Give it a one-line statement of purpose at the top, written for somebody who
  arrived from a search result and has no other context.

A module that only exists to hold one function usually belongs inside the
module that calls it.
