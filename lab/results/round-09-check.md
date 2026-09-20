# Round 9 — check

_generated 2026-09-20T11:41_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| A06 ISO dates in the report | A | ok | 0 | 25 | 0 | ✔ | $0.22 |
| B06 price per kilo labels | B | ok | 0 | 26 | 0 | ✔ | $0.36 |

## Harvest quality (`lab audit`)

```
A06 task 25: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
B06 task 26: broken=fail house-fix=pass rule-breaking=pass  -> WEAK: passes a rule-breaking fix
```

- task 25 (A06) check: `set -e ; # Test passes (report contains ISO dates, not US format dates) ; python3 -m unittest tests.test_report_iso_dates -v ; # CHANGELOG.md was updated ; if git diff --quiet 35c9d79 -- CHANGELOG.md; then ;   echo "CHAN`
- task 26 (B06) check: `set -e ; # Verify that the price_per_kg tests pass (all rounding cases) ; python3 -m unittest tests.test_price_per_kg.ShelfLabelTests -v`

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
14      fail          pass         ok
15      fail          pass         ok
16      fail          pass         ok
17      fail          pass         ok
18      fail          pass         ok
19      fail          pass         ok
20      fail          pass         ok
21      fail          pass         ok
22      fail          pass         ok
23      fail          pass         ok
24      fail          pass         ok
25      fail          pass         ok
26      fail          pass         ok

valid=25 quarantined=0 skipped=0
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
2026-09-20 | task 17 | implemented output message fix without updating CHANGELOG.md | add CHANGELOG entry for all user-visible changes alongside the implementation
2026-09-20 | task 21 | tried float division and round() in billing code | use scale() helper for exact arithmetic
2026-09-20 | task 22 | initially used date.today() instead of shop.clock.today() in catalog.py | use shop.clock.today() per CONTRIBUTING.md time house rule
2026-09-20 | task 23 | implemented exporter plugin without docs/exporters.md row and golden file initially | every exporter plugin needs all four: implementation, registry entry, docs/exporters.md row, and golden file from `make golden`
```

## Sweeps this round

| File | Phase | Verdict | Gain | Net runs | Fired | Per task (base→cand) | Cost | Elapsed | At once |
|---|---|---|---|---|---|---|---|---|---|
| 20260920T111855-screen.jsonl | screen | **CONFIRM** | 0.5 | 1 | 6 | 11 0.00→0.50, 12 1.00→1.00, 13 1.00→1.00 | $0.91 | 1 min | 12 |
| 20260920T112020-confirm.jsonl | confirm | **RECHECK** | 4.333333333333333 | 10 | 75 | 01 1.00→1.00, 02 1.00→1.00, 03 1.00→1.00, 04 0.00→0.00, 05 0.67→1.00, 06 0.67→0.33, 08 0.67→1.00, 09 1.00→0.33, 10 0.33→0.33, 11 0.00→0.00, 12 1.00→1.00, 13 1.00→1.00, 14 1.00→1.00, 15 1.00→1.00, 16 1.00→1.00, 17 0.67→1.00, 18 0.67→0.67, 19 0.33→1.00, 20 0.67→1.00, 21 0.33→0.33, 22 0.00→0.67, 23 0.00→0.67, 24 0.00→0.33, 25 0.00→0.67, 26 0.67→0.67 | $16.54 | 11 min | 12 |
| 20260920T113145-recheck.jsonl | recheck | **RERUN** | 0 | -1 | 3 | 09 1.00→0.67 | $1.47 | 3 min | 6 |
| 20260920T113718-recheck.jsonl | recheck | **RERUN** | 0 | 0 | 3 | 09 1.00→1.00 | $1.42 | 3 min | 6 |

/evolve turns: 3, $0.89

## Journal (tail)

```
DECISION:   KILL — gate2: worst_drop 0.67 exceeds tolerance 0.34; gate3: broke protected set (10 tasks); gate4: net -3 runs under noise threshold
note:       The previously-kept clock-in-billing rule, when tested against the full task suite at k=3, showed significant regressions that were not caught in the earlier narrower screen (k=2 on failing tasks only). The rule causes a worst-case collapse of 0.67 on one task and breaks multiple previously-passing tasks. The promotion from the earlier cycle should be reverted.

## 2026-09-20  shop-clock-usage

kind:       rule
paths:      "shop/**"
theme:      use shop.clock instead of datetime in shop/ code (1 lesson: task)
layer:      rule — injects when agent Reads/Writes shop/ files
screen:     [not run — escalated directly to confirm due to theme priority]
confirm:    gain +4.33 | regression 1.00 | worst_drop 0.67 | net +3.33
            - task 09: 1 -> 0.67 (-0.33) — REGRESSION, protected set broken
            - other tasks: net +4.67 gain
recheck:    task 09 showed delta 0 (no regression), but measurement infrastructure unstable (harness hashes mismatched)
DECISION:   KILL — gate2 (worst_drop 0.67 > tolerance 0.34); gate3 (broke protected); measurement unreliable + clock module rules have history of hidden regressions (see clock-in-billing re-tested)
note:       confirm showed protected task regression but recheck infrastructure failed to validate (harness changed mid-measurement). The recheck's task 09 delta=0 contradicts confirm but measurement infrastructure instability makes pairing unreliable. Conservative approach: clock-module rules (clock-in-billing, this rule) have complex interactions — even when recheck clears a regression, later re-tests may reveal problems. Similar to clock-in-billing pattern.
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

