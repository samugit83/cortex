# Round 4 — check

_generated 2026-09-20T09:50_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| E01 invoice due date | E | E → ok | 1 | 11 | 1 | ✔ | $0.55 |
| E02 cart reservation expiry | E | E → ok | 1 | 12 | 1 | ✔ | $0.58 |
| E03 archive old orders | E | E → ok | 1 | 13 | 1 | ✔ | $1.10 |

## Harvest quality (`lab audit`)

```
E01 task 11: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
E02 task 12: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
E03 task 13: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
```

- task 11 (E01) check: `set -e ; # Test the due_date function exists and works ; python3 -m unittest tests.test_due_date.DueDateTests -v ; # Linter must pass: no direct date.today() / datetime.now() in shop/ ; # (enforces the house rule to use `
- task 12 (E02) check: `set -e ; # Run the cart reservation tests ; python3 -m unittest tests.test_cart_reservation -v ; # Run existing cart tests for regression ; python3 -m unittest tests.test_cart -v ; # Verify linter passes (the key correct`
- task 13 (E03) check: `set -e ; # Test that archive_old_orders works correctly ; python3 -m unittest tests.test_order_archive -v ; # Verify no direct datetime/date access in shop/orders.py (shop.clock rule) ; if grep -E 'datetime\.now\(\)|date`

## Preflight

```
task    broken-state  fixed-state  verdict
------  ------------  -----------  -------
01      fail          pass         ok
02      fail          pass         ok
03      fail          pass         ok
04      fail          pass         ok
05      fail          pass         ok
06      fail          pass         ok
08      fail          pass         ok
09      fail          pass         ok
10      fail          pass         ok
11      fail          pass         ok
12      fail          pass         ok
13      fail          pass         ok

valid=12 quarantined=0 skipped=0
```

## Lessons

```
2026-09-19 | task 01 | used Decimal arithmetic in billing/ module | use percent_of() helper for exact percentage calculations
2026-09-19 | task 03 | used float arithmetic in billing code when linting rejected it | use times() helper for exact arithmetic in billing module
2026-09-19 | task 04 | shipped without updating CHANGELOG.md | add user-visible changes to CHANGELOG.md under [Unreleased]
2026-09-19 | task 05 | implemented feature without updating CHANGELOG.md initially | add CHANGELOG entry together with the implementation commit
2026-09-19 | task 06 | committed implementation without updating CHANGELOG.md | always check and update CHANGELOG.md for user-visible features
2026-09-19 | no task | implemented exporter plugin without docs entry and golden file | exporters need registry entry, docs/exporters.md row, and golden file from `make golden`
2026-09-19 | task 09 | implemented exporter without docs and golden file | every exporter needs registry entry, docs/exporters.md row, and golden file
2026-09-19 | task 10 | implemented exporter without docs/exporters.md row and golden file | exporters require documentation entry and golden file for CI verification
2026-09-19 | task 08 | completed exporter implementation but forgot to add docs/exporters.md row and golden file | all four exporter requirements must be completed: registry entry, implementation, docs, and golden file
2026-09-20 | task 11 | used date.today() in shop/billing/ code when CI rejected it | use shop.clock.today() for all time operations in shop/ module per CONTRIBUTING.md house rule
2026-09-20 | task 12 | used datetime.now() in shop/ instead of shop.clock.now() | always use shop.clock in shop module
2026-09-20 | task 13 | used datetime.today().date() in shop/orders.py instead of shop.clock | always use shop.clock.today() for time access in shop module
```

## Sweeps this round

| File | Phase | Verdict | Gain | Net runs | Fired | Per task (base→cand) | Cost | Elapsed | At once |
|---|---|---|---|---|---|---|---|---|---|
| 20260920T091012-screen.jsonl | screen | **RERUN** | 0 | 0 | 6 | 11 0.00→0.00, 12 1.00→1.00, 13 0.00→0.00 | $0.98 | 1 min | 8 |
| 20260920T092319-screen.jsonl | screen | **CONFIRM** | 0.5 | 0 | 6 | 08 0.50→1.00, 09 1.00→0.50, 10 1.00→1.00 | $2.28 | 3 min | 8 |
| 20260920T093210-confirm.jsonl | confirm | **KILL** | 0.6666666666666667 | 1 | 9 | 01 1.00→1.00·, 02 1.00→1.00·, 03 1.00→1.00·, 04 0.00→0.00·, 05 0.33→0.33·, 06 0.33→0.33·, 08 1.00→0.67, 09 0.33→0.67, 10 0.67→1.00, 11 0.00→0.00·, 12 1.00→1.00·, 13 1.00→1.00· | $7.91 | 8 min | 8 |

/evolve turns: 9, $1.50

## Journal (tail)

```
2-run bar — without a cycle record, because I had removed its candidate mid-flight).

Lesson for the experimenter, not for Cortex: stop the loop before touching a running
sweep. The clock house rule is still the one theme nothing covers.

## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar

## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar

## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

## Routing after the round

```
routing  always-on 556/3000 chars   (always-on skills + path-less rules + CLAUDE.md)
  TIER         NAME                           STATUS    ALWAYS  PATHS / TRIGGER
  gated        check-changelog-on-shop-edits  ok             0  shop/**
  gated        complete-exporter-setup        ok             0  shop/plugins/**
  rule         use-billing-helpers            ok             0  shop/billing/**
check: 0 error(s), 0 warning(s)
```

### .claude/rules/use-billing-helpers.md

```markdown
---
paths:
  - "shop/billing/**"
---

# Billing arithmetic

- NEVER parse string rates or percentages with `int(rate.split(".")[0])` or similar patterns that truncate decimals. Use `percent_of(amount, rate)` for percentage calculations and `times(amount, rate)` for currency conversions from the `.rates` module instead.
```

### .claude/skills/check-changelog-on-shop-edits/SKILL.md

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

### .claude/skills/complete-exporter-setup/SKILL.md

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

## Autopilot findings

- none

