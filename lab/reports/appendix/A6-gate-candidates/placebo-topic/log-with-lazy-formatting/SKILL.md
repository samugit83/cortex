---
name: log-with-lazy-formatting
description: When adding a logging call, pass the arguments to the logger instead of formatting first
---

# Logging

Hand the logger the pattern and the values, and let it decide whether the
message is ever built.

- Write `log.info("loaded %s rows from %s", n, path)`, not
  `log.info(f"loaded {n} rows from {path}")`.
- A call that is filtered out by its level then costs almost nothing, which
  matters in the inner loops where logging is most tempting.
- Keep the pattern a literal: a pattern built at the call site cannot be
  grouped by the aggregation tools that read the output later.

The same applies to `warning`, `error` and `debug`.
