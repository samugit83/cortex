# A3 · Every item, kept and buried

In full, with the measurement that decided it. A buried item is as much a result as a kept one: it is the loop declining to spend your context on something it could not show a gain for.

## D0

### kept (3)

#### `check-changelog-on-shop-edits` — skill, paths: `shop/**`

```markdown
---
name: check-changelog-on-shop-edits
description: Before finishing changes to shop/ code, verify CHANGELOG.md was updated
paths:
  - "shop/**"
---

1. After modifying shop/ code, check if CHANGELOG.md needs an entry.
2. If you added a user-visible feature or fix to shop/ code, ensure CHANGELOG.md has an [Unreleased] entry describing it.
3. If the [Unreleased] section is missing, add it at the top of the file above the latest version header.
4. Do not skip CHANGELOG updates even for internal refactoring — if users would notice the change, it needs documenting.
```

#### `complete-exporter-setup` — skill, paths: `shop/plugins/**`

```markdown
---
name: complete-exporter-setup
description: When implementing a new exporter plugin in shop/plugins/, verify all four files are updated
paths:
  - "shop/plugins/**"
---

# Exporter completeness checklist

Before finalizing an exporter implementation:

1. **Registry entry** — Ensure `shop/plugins/registry.py` includes the new exporter class registration
2. **Implementation** — Write the exporter class in `shop/plugins/<format>_export.py` with correct format handling
3. **Documentation** — Add a row to `docs/exporters.md` with format name, module name, and description
4. **Golden test file** — Run `make golden` to generate and commit `tests/golden/order.<ext>` for the new format

All four must be completed together. Missing any one will fail the CI lint check.
```

#### `use-billing-helpers` — rule, paths: `shop/billing/**`

```markdown
---
paths:
  - "shop/billing/**"
---

# Billing arithmetic

- NEVER parse string rates or percentages with `int(rate.split(".")[0])` or similar patterns that truncate decimals. Use `percent_of(amount, rate)` for percentage calculations and `times(amount, rate)` for currency conversions from the `.rates` module instead.
```

### buried (7)

#### `changelog-rule-v2` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# CHANGELOG updates required for shop features

- NEVER implement a user-visible feature or fix in shop/ without updating CHANGELOG.md. Add a single-line entry under `[Unreleased]` alongside the implementation commit.
- The fix must include `CHANGELOG.md` in the same commit as the shop/ changes. An implementation that edits `shop/cli.py`, `shop/billing/`, `shop/plugins/`, or other shop modules must also edit `CHANGELOG.md` to describe the change.
```

**Why it was buried**

```
# Buried 2026-09-20T10:24:42+02:00

from: candidate
kind: rule
why:  screen: gate2 worst_drop 0.5 exceeds regression_tolerance 0.34 on task 06
```

#### `changelog-updates` — skill, paths: none (always on)

```markdown
---
name: changelog-updates
description: When implementing user-visible features or fixes, remember to update CHANGELOG.md
---

## Changelog tracking

User-visible changes (features, fixes, improvements) should be documented in CHANGELOG.md under [Unreleased] → [Added], [Fixed], or [Changed]. Before finishing a task:
- If you added a feature or fixed a bug that users will notice, add a one-line entry to CHANGELOG.md [Unreleased] section with your change
- If you touched shop/, docs/, or plugins/ and changed user behavior, check whether CHANGELOG.md needs a line
- Some checks explicitly require CHANGELOG.md to be modified alongside the implementation — read the test file's check.sh if there's doubt
```

**Why it was buried**

```
# Buried 2026-09-20T11:50:49+02:00

from: candidate
kind: skill
why:  screen gate5: never invoked, description did not trigger. Should have been a rule (visible in 10 runs but never chosen)
```

#### `check-changelog-on-shop-edits` — skill, paths: `shop/**`

```markdown
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
```

**Why it was buried**

```
# Buried 2026-09-19T15:21:02+02:00

from: candidate
kind: skill
why:  screen: never loaded (gate5); no gain (gate1)
```

#### `clock-in-billing` — rule, paths: `shop/billing/**`

```markdown
---
paths:
  - "shop/billing/**"
---

# Shop billing time operations

- NEVER use `date.today()`, `datetime.now()`, or `datetime.today()` in shop/billing code. Use `shop.clock.today()` or `shop.clock.now()` instead (imported from `shop.clock`), per CONTRIBUTING.md house rule.
```

**Why it was buried**

```
# Buried 2026-09-20T11:11:30+02:00

from: candidate
kind: rule
why:  gate2 worst drop 0.67 exceeds tolerance 0.34; gate3 broke protected set 10 tasks; gate4 net -3 runs under noise threshold
```

#### `enforce-shop-clock` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# Time in shop/

- NEVER call `datetime.now()`, `datetime.utcnow()`, `date.today()`, or `time.time()` in `shop/` code.
  Import `clock` from the parent module and use `clock.now()` or `clock.today()` instead (see `CONTRIBUTING.md`, "Time (all of shop/)" section).
  Example: in `shop/orders.py`, write `from . import clock` and call `clock.today()`.
```

**Why it was buried**

```
# Buried 2026-09-20T09:12:11+02:00

from: candidate
kind: rule
why:  screen: gain 0, tasks 11/13 never passed
```

#### `enforce-shop-clock-v2` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# Time operations in shop module

- NEVER use stdlib date/time functions (`date.today()`, `datetime.now()`, `datetime.today()`, etc.) in shop/ code. Always use `shop.clock.today()` and `shop.clock.now()` from the shop module's clock facade for all time access in shop code.
```

**Why it was buried**

```
# Buried 2026-09-20T10:07:58+02:00

from: candidate
kind: rule
why:  gate2 worst drop 1.0 exceeds tolerance 0.34, gate3 broke protected set task 08, gate4 net 1 run under min 2
```

#### `shop-clock-usage` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# Time access in shop/

- NEVER use `date.today()`, `datetime.now()`, `datetime.utcnow()`, or `time.time()` in shop/ code. Always import `clock` from the shop module and use `shop.clock.today()` or `shop.clock.now()` instead (see CONTRIBUTING.md "Time (all of shop/)" section).
- Example in `shop/orders.py`: write `from . import clock` at the top, then call `clock.today()`.
- The linter (`make lint`) enforces this rule and rejects datetime calls in shop/ code.
```

**Why it was buried**

```
# Buried 2026-09-20T11:41:19+02:00

from: candidate
kind: rule
why:  gate2: worst_drop 0.67 exceeds tolerance 0.34; gate3: broke protected; measurement unstable; clock module rules have history of hidden regressions
```

## R1

### kept (4)

#### `exporter-checklist` — skill, paths: `shop/plugins/**`

```markdown
---
name: exporter-checklist
description: When implementing a new exporter plugin format in shop/plugins
paths:
  - "shop/plugins/**"
---

When adding a new export format (a new `*Exporter` class):

1. **Implement the exporter class** in `shop/plugins/<format>_export.py`:
   - Inherit from `Exporter` base class
   - Set `name` and `extension` class attributes
   - Implement the `export(orders) -> str` method

2. **Register the exporter** in `shop/plugins/registry.py`:
   - Import the new exporter class
   - Add it to the `EXPORTERS` dict with its name as the key

3. **Document the format** in `docs/exporters.md`:
   - Add a row to the formats table with name, extension, and description
   - Keep the table sorted alphabetically by name

4. **Create the golden file** in `tests/golden/`:
   - Run `make golden` to generate `tests/golden/order.<ext>` (the reference output for CI)
   - Commit the golden file so CI can verify the output matches

5. **Update CHANGELOG.md**:
   - Add an entry under `[Unreleased] / Added` documenting the new export format
   - Use the form: `` `shop export --format <name>` for <description> ``
```

#### `billing-helpers` — rule, paths: `shop/billing/**`

```markdown
---
paths:
  - "shop/billing/**"
---

# Billing arithmetic
- NEVER use `int()`, `float()`, `round()`, or direct Decimal arithmetic to compute percentages, discounts, or currency conversion. Use `percent_of()`, `times()`, or `scale()` from `shop/billing/rates.py` — see that file's docstrings for which helper to use.
```

#### `changelog-requirement` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# Changelog requirement

- NEVER implement a user-visible feature change without first adding an entry to CHANGELOG.md under [Unreleased]. The entry must describe the change from a user's perspective.
- NEVER forget to update CHANGELOG.md when modifying command-line behavior, output formatting, or reporting features in shop/.
- When adding features or changing behavior, add entries under an appropriate section (### Added, ### Changed, etc.) in the [Unreleased] block of CHANGELOG.md.
```

#### `shop-clock-rule` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# shop/: time access

- NEVER use `date.today()`, `datetime.now()`, or `datetime.today()` directly in shop/ code. Import `from shop import clock` and use `clock.today()` or `clock.now()` instead. The linter enforces this constraint and all shop/ modules access time through the clock abstraction.
```

## R2

### kept (4)

#### `billing-exact-arithmetic` — rule, paths: `shop/billing/**`

```markdown
---
paths:
  - "shop/billing/**"
---

# Billing — exact arithmetic

- NEVER use float or Decimal division / multiplication for percentage or rate calculations. Use `percent_of()` for percentages and `times()` for rate scaling instead (from `shop/billing/rates.py`).
- NEVER parse rates as strings and extract only the integer part. Use `parse_rate()` for full precision, and `scale()` for decimal adjustment (from `shop/billing/rates.py`).
- NEVER truncate percentage strings like `"12.5"` to integer; use `parse_rate()` and `scale()` for proper Decimal handling.
```

#### `changelog-user-visible` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# CHANGELOG updates

- NEVER implement a user-visible feature change without adding a line to `CHANGELOG.md`. Read CONTRIBUTING.md (lines 38–42): changes users see — commands, options, output formats, messages — must appear under `## [Unreleased]` in the appropriate subsection (`### Added`, `### Changed`, or `### Fixed`).
- If your change touches a shop/ file that affects user output, check whether `CHANGELOG.md` covers it. Update the `[Unreleased]` section immediately, not as an afterthought.
```

#### `exporter-docs-and-golden` — rule, paths: `shop/plugins/**`

```markdown
---
paths:
  - "shop/plugins/**"
---

# Exporters
- NEVER implement an exporter without adding a row to `docs/exporters.md` and a golden file. Read CONTRIBUTING.md § Exporters: all four items (implementation, registry, docs row, golden file) are required. `make lint` checks items 2–4. After implementing `shop/plugins/<name>_export.py`, run `make golden` immediately and commit the resulting `tests/golden/order.<extension>`.
```

#### `shop-clock-not-datetime` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# shop module — datetime/date access

- NEVER call `date.today()` or `datetime.now()` or `datetime.today()` directly in shop/ code.
  See shop/__init__.py: import from `.. import clock`, or from `shop import clock`, then call `clock.today()` or `clock.now()`.
  This allows tests to freeze time via `shop.clock.set_now()`.
```

### buried (1)

#### `shop-clock-explicit-imports` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# shop module — time access requires clock abstraction

- NEVER use `date.today()`, `datetime.now()`, `datetime.today()`, or `time.time()` directly in shop/ code.
  The house rule (documented in shop/clock.py and CONTRIBUTING.md, "Time") requires using the `clock` module for test freezing.

- ALWAYS import and use the clock module for time reads. Import relative to your location in the shop package:
  - **From shop/billing/invoice.py or other nested modules:** `from .. import clock`, then call `clock.today()` or `clock.now()`.
  - **From shop/cart.py or modules directly in shop/:** `from . import clock`, then call `clock.today()` or `clock.now()`.

- Choose the right function:
  - `clock.today()` returns a `date` object (for date-only operations).
  - `clock.now()` returns a timezone-aware `datetime` object (for timestamp operations).

- Example: To add a due date 30 days after today in shop/billing/invoice.py:
  ```python
  from datetime import timedelta
  from .. import clock  # Relative import from nested module
  
  def due_date(days: int = 30) -> date:
      return clock.today() + timedelta(days=days)  # Use clock.today()
  ```

- Example: To track cart expiration in shop/cart.py:
  ```python
  from datetime import timedelta
  from . import clock  # Relative import from shop/
  
  def reserve(self, minutes: int = 15) -> None:
      self.expires_at = clock.now() + timedelta(minutes=minutes)  # Use clock.now()
  ```
```

**Why it was buried**

```
# Buried 2026-09-21T20:45:12+02:00

from: candidate
kind: rule
why:  overlaps with live rule shop-clock-not-datetime; refinements use /prune
```

## R3

### kept (6)

#### `billing-rate-helpers` — rule, paths: `shop/billing/shipping.py`, `shop/billing/refunds.py`

```markdown
---
paths:
  - "shop/billing/shipping.py"
  - "shop/billing/refunds.py"
---

# Billing Arithmetic
- NEVER use `float()`, `round()`, or `Decimal()` for amount conversions in shop/billing/. Use the helpers from `shop/billing/rates.py` instead: `percent_of(amount, percent)` for percentages, `times(amount, rate)` for rate scaling, `scale(amount, factor)` for integer scaling.
- NEVER use `date.today()` or `datetime.now()` directly in this module. Use `shop.clock.today()` or `shop.clock.now()` for testability.
```

#### `changelog-shop-reminder` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# shop/ changes need CHANGELOG entries

- NEVER change shop/ code without updating CHANGELOG.md. User-visible changes (CLI, formatting, reports) must have a line under `[Unreleased]` in CHANGELOG.md describing what users will see.
```

#### `changelog-user-facing` — rule, paths: `shop/cli.py`, `shop/formatting.py`, `shop/report.py`

```markdown
---
paths:
  - "shop/cli.py"
  - "shop/formatting.py"
  - "shop/report.py"
---

# User-visible changes
- NEVER implement a user-visible feature without adding a CHANGELOG entry. Add one line to `CHANGELOG.md` under the `[Unreleased]` section's appropriate subsection (Added, Changed, Fixed, Removed) describing what users see change.
```

#### `exporter-checklist-v2` — rule, paths: `shop/plugins/*_export.py`

```markdown
---
paths:
  - "shop/plugins/*_export.py"
---

# new exporters need complete checklist

- NEVER implement a new exporter plugin without ALL FOUR of: (1) exporter class in `shop/plugins/<format>_export.py` with `export()` function, (2) registration in `shop/plugins/registry.py`, (3) documentation row in `docs/exporters.md` describing format and use cases, (4) golden file generated by `make golden` (stored in `tests/golden/order.<format>`). Missing any one will fail linting.
- ALWAYS run `make verify` after adding a new exporter to ensure registry, docs row, and golden file are all present and match the test suite.
```

#### `rate-helpers-narrow` — rule, paths: `shop/billing/tax.py`, `shop/billing/discount.py`, `shop/billing/fx.py`

```markdown
---
paths:
  - "shop/billing/tax.py"
  - "shop/billing/discount.py"
  - "shop/billing/fx.py"
---

# shop/billing rate and percentage arithmetic

- NEVER manually parse rate or percentage strings with `split(".")` and `int()`. This discards decimal places and loses precision. Use `percent_of()` for percentages and `times()` for exchange rates, both from `shop/billing/rates.py`.
```

#### `shop-clock-narrow` — rule, paths: `shop/billing/invoice.py`, `shop/cart.py`, `shop/orders.py`

```markdown
---
paths:
  - shop/billing/invoice.py
  - shop/cart.py
  - shop/orders.py
---

# shop time access

- NEVER use `date.today()`, `datetime.now()`, or `datetime.today()` directly in these files. Use `shop.clock.today()` or `shop.clock.now()` instead, defined in `shop/clock.py`. This enables time freezing in tests via `clock.freeze()`.
```

### buried (4)

#### `exporter-checklist` — skill, paths: `shop/plugins/**`

```markdown
---
name: exporter-checklist
description: When implementing a new exporter plugin for the shop
paths:
  - "shop/plugins/**"
---

1. Implement the exporter class in `shop/plugins/<format>_export.py` with an `export()` function that takes orders and returns the formatted output.

2. Register the exporter in `shop/plugins/registry.py` by adding an entry that maps the format name to the exporter class.

3. Add a documentation row to `docs/exporters.md` describing the new exporter's format, when to use it, and any special features (e.g., "Tabular format with headers, good for spreadsheets").

4. Run `make golden` to generate the golden file for the new exporter format (creates `tests/golden/order.<format>`).

5. Run `make verify` to ensure all CI checks pass before finishing, including the new exporter's golden file test.
```

**Why it was buried**

```
# Buried 2026-09-21T21:36:33+02:00

from: candidate
kind: skill
why:  gate4: net 1 run is noise (threshold 2)
```

#### `shop-clock-access` — rule, paths: `shop/**`

```markdown
---
paths:
  - shop/**
---

# shop time access

- NEVER use `date.today()`, `datetime.now()`, or `datetime.today()` directly in shop/ code. Use `shop.clock.today()` or `shop.clock.now()` instead, defined in `shop/clock.py`. This enables time freezing in tests via `clock.freeze()`.
```

**Why it was buried**

```
# Buried 2026-09-21T22:13:21+02:00

from: candidate
kind: rule
why:  gate2/3: task 13 regressed 100%->67% and confirmed on recheck
```

#### `text-utilities-correctness` — rule, paths: `shop/util/text.py`

```markdown
---
paths:
  - "shop/util/text.py"
---

# String Utility Functions

- NEVER use `count > 1` to test for plural in `pluralize()`. Use `count != 1` instead, so zero and negatives also use the plural form.
- NEVER add `ellipsis` to text without subtracting its length from the width limit in `truncate()`. Return `text[:width - len(ellipsis)] + ellipsis` to fit within the specified width.
- NEVER use `[a-z0-9]` regex patterns for character classes when the text may contain accented characters. Normalize with `unicodedata.normalize("NFD", text)`, encode to ASCII with `text.encode("ascii", "ignore").decode("ascii")`, then apply the regex.
```

**Why it was buried**

```
# Buried 2026-09-21T23:25:54+02:00

from: candidate
kind: rule
why:  gate2/3: worst_drop 0.67 broke tasks 13,15 in protected set
```

#### `use-rate-helpers` — rule, paths: `shop/billing/**`

```markdown
---
paths:
  - "shop/billing/**"
---

# shop/billing rate and percentage arithmetic

- NEVER manually parse rate or percentage strings with `split(".")` and `int()`. This discards decimal places and loses precision. Use `percent_of()` for percentages and `times()` for exchange rates, both from `shop/billing/rates.py`.
```

**Why it was buried**

```
# Buried 2026-09-21T20:55:34+02:00

from: candidate
kind: rule
why:  confirm: gain +3 but regression +3, worst_drop 1.0 — rule too broad, breaks non-billing rate handling
```

## R4

### kept (4)

#### `exporter-checklist` — skill, paths: `shop/plugins/**`

```markdown
---
name: exporter-checklist
description: When implementing a new exporter format in shop/plugins/, verify all required files are included
paths:
  - "shop/plugins/**"
---

# Exporter Implementation Checklist

When you implement a new exporter format, it must include these files:

1. **Exporter class** — `shop/plugins/{name}_export.py` with a class extending `BaseExporter`

2. **Registry entry** — Add the import and registration to `shop/plugins/registry.py`:
   ```python
   from .{name}_export import {CapitalName}Exporter
   ```

3. **Documentation row** — Add a row to `docs/exporters.md` in the table:
   ```markdown
   | {name} | {code} | description of the format |
   ```
   Match the row format exactly: format name | code name | description.

4. **Golden file** — Create `tests/golden/orders.{code}` with sample output for the test suite to validate against.

Do not declare the exporter complete until all four are in place.
```

#### `billing-rates-helpers` — rule, paths: `shop/billing/**`

```markdown
---
paths:
  - "shop/billing/**"
---

# Billing arithmetic

- NEVER parse rates or percentages with `int(x.split(".")[0])` or `split(".")` and direct indexing. `int()` truncates; `split()` ignores the fractional part. Use `percent_of()` or `times()` from `shop/billing/rates.py`, which handle exact decimal arithmetic and return Money objects.
- NEVER use `Decimal`, `float`, or `round()` directly on currency. shop/billing forbids these — rates are exact rational arithmetic. Use helpers from `shop/billing/rates.py` (exported: `times()` for multiplying an amount by a decimal factor like "1.0842", `percent_of()` for percentages like "8.25").
- When scaling a Money amount by a string-encoded rate or percentage, always import and call the right helper: `from .rates import percent_of, times`. Do not add custom parsing.
```

#### `shop-changelog-reminder` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# Shop Feature Changes and CHANGELOG

- NEVER implement a user-visible change to `shop/` (a new option, a default behavior change, a new output format, a new command, etc.) without updating CHANGELOG.md. The test suite checks that it exists.
- When implementing user-visible features in `shop/`, add an entry to the `[Unreleased]` section of CHANGELOG.md describing what changed and why the user cares. Use the existing entries as a style guide.
- Internal-only changes (refactors, test-only code, performance improvements with no user-visible effect) do not require a CHANGELOG entry.
```

#### `shop-clock-queries` — rule, paths: `shop/**`

```markdown
---
paths:
  - "shop/**"
---

# Time queries in shop

- NEVER use `datetime.now()`, `datetime.utcnow()`, `date.today()`, or any stdlib time function in shop/ code. All time queries must use `shop.clock` for testability and consistency. Import and call `from .. import clock` (or `from shop import clock` at top level) and use `clock.now()` for current datetime (UTC), or `clock.today()` for current date.
- When adding time-based logic to shop/ (expiry checks, timestamps, due dates), always use `clock.now()` or `clock.today()`, never stdlib `datetime` or `date` directly.
```

### buried (4)

#### `changelog-contributing-reminder` — rule, paths: `CONTRIBUTING.md`

```markdown
---
paths:
  - "CONTRIBUTING.md"
---

# CHANGELOG.md requirement

- NEVER finish implementation of a user-visible change without adding a line to CHANGELOG.md. The test checks for it (lines 38-42 show the requirement: "Every change users can see gets a line").
- If your change adds or modifies any user-facing feature—a command option, output format, new exporter, display change—add an entry under `## [Unreleased]` in CHANGELOG.md.
- The entry must be in the exact format shown in CONTRIBUTING.md: `### Added`, `### Changed`, or `### Fixed` section.
- Read CONTRIBUTING.md *before* starting, so you plan for the CHANGELOG entry as you implement.
```

**Why it was buried**

```
# Buried 2026-09-22T00:47:00+02:00

from: candidate
kind: rule
why:  screen: never loaded — no rollout read a matching file
```

#### `changelog-for-user-visible-changes` — rule, paths: `CHANGELOG.md`

```markdown
---
paths:
  - "CHANGELOG.md"
---

# CHANGELOG updates

- NEVER skip updating CHANGELOG.md when implementing a user-visible feature, option, output format, or message — even if other files are your main focus. Read CONTRIBUTING.md: "Every change users can see gets a line in CHANGELOG.md under `## [Unreleased]`".
- NEVER add entries in the wrong section. Check the three categories in `## [Unreleased]`: use `### Added` for new features, `### Changed` for behavior changes, `### Fixed` for fixes that restore documented behavior. Internal-only changes (refactors, performance fixes) do not need an entry.
- When editing CHANGELOG.md, always check: Is the entry under `## [Unreleased]`? Is it in the right subsection? Does it describe the change from the user's perspective (what changed, not how)?
```

**Why it was buried**

```
# Buried 2026-09-22T00:16:31+02:00

from: candidate
kind: rule
why:  screen: gain 0 + never loaded
```

#### `changelog-in-contributing` — rule, paths: none (always on)

```markdown

```

**Why it was buried**

```
# Buried 2026-09-22T00:44:01+02:00

from: candidate
kind: malformed
why:  empty candidate — malformed
```

#### `changelog-moment-check` — skill, paths: none (always on)

```markdown
---
name: changelog-moment-check
description: Before reporting changes complete, verify user-visible changes were added to CHANGELOG.md
---

# Pre-Completion Checklist

Before you declare your implementation finished, verify these requirements for user-visible changes:

## CHANGELOG.md

If your changes add or modify any **user-visible feature** (a new command option, a display format change, a new report type, a new exporter format, etc.):

1. **Open CHANGELOG.md** and locate the `[Unreleased]` section at the top.

2. **Add an entry** describing the change in user-facing language:
   ```markdown
   - Feature: description of what changed and why the user cares
   ```
   or
   ```markdown
   - Fix: description of the bug and its impact
   ```

3. **Match the existing style** — look at prior entries in `[Unreleased]` for examples of how to phrase it.

4. **Do this BEFORE finishing**, not after. The test suite checks that CHANGELOG was updated.

If your changes are internal-only (refactoring, test-only, documentation-only), skip this.

## Examples

✓ **Good:** Implemented new XML exporter → add `- Feature: XML export format for accounting software compatibility`

✗ **Wrong:** Implemented new XML exporter → forgot CHANGELOG.md entirely

✓ **Good:** Fixed precision bug in price display → add `- Fix: correct rounding of fractional cent amounts in reports`

✗ **Wrong:** Fixed precision bug → only committed the code, not the CHANGELOG line
```

**Why it was buried**

```
# Buried 2026-09-22T00:43:20+02:00

from: candidate
kind: skill
why:  screen: never invoked; agent doesn't treat always-on reminder as actionable. Rule on CONTRIBUTING.md would be visible to agent.
```

