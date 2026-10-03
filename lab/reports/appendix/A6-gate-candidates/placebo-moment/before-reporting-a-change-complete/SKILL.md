---
name: before-reporting-a-change-complete
description: Use before reporting that a change is complete
---

# Names carry their own context

A name inside a small scope does not need to repeat the scope.

- Inside `Cart`, a field is `lines`, not `cart_lines`.
- Inside a function about one product, the variable is `product`, not
  `the_product_being_processed`.
- A loop variable that lives for two lines may be one letter if the collection
  it comes from is named well.

The longer the scope, the longer the name may be. A module-level constant earns
a full sentence of a name; a comprehension variable does not.
