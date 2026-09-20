# Round 8 — check

_generated 2026-09-20T11:12_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| C05 HTML export | C | C → ok | 1 | 23 | 1 | ✔ | $0.58 |
| D04 business days skip Saturdays | D | ok | 0 | 24 | 0 | ✔ | $0.26 |

## Harvest quality (`lab audit`)

```
C05 task 23: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
D04 task 24: broken=fail house-fix=fail rule-breaking=n/a  -> WEAK
```

- task 23 (C05) check: `set -e ; # Test the HTML export implementation ; python3 -m unittest tests.test_export_html -q ; # Verify the linter passes (checks registry, docs, golden file) ; python3 tools/lint.py ; # Verify HTML exporter is availab`
- task 24 (D04) check: `set -e ; # The tests must pass ; python -m unittest tests.test_business_days_weekend -v ; # The CHANGELOG must be updated ; if git diff --quiet 6a6a2f01b266268bf7a74a01d29a7b385da6848d -- CHANGELOG.md; then ;   echo "CHA`

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

valid=23 quarantined=0 skipped=0
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
| 20260920T103218-screen.jsonl | screen | **CONFIRM** | 1 | 2 | 2 | 11 0.00→1.00 | $0.29 | 1 min | 4 |
| 20260920T103343-confirm.jsonl | confirm | **RERUN** | 2 | 3 | 26 | 01 1.00→1.00, 02 1.00→1.00, 03 1.00→1.00, 04 0.00→0.00·, 05 0.33→0.33, 06 0.33→0.33, 08 1.00→0.67·, 09 0.67→1.00, 10 0.33→0.67, 11 0.00→1.00, 12 1.00→1.00·, 13 1.00→1.00·, 14 1.00→1.00·, 15 1.00→1.00·, 16 1.00→1.00·, 17 0.67→0.33·, 18 1.00→0.33, 19 1.00→0.67, 20 1.00→1.00·, 21 0.00→0.33 | $13.2 | 95 min | 12 |
| 20260920T104509-confirm.jsonl | confirm | **RECHECK** | 2.3333333333333335 | 5 | 25 | 01 1.00→1.00, 02 1.00→1.00, 03 1.00→1.00, 04 0.00→0.00·, 05 0.33→0.00, 06 0.33→0.33, 08 1.00→0.33·, 09 1.00→0.67, 10 0.00→1.00, 11 0.00→1.00, 12 1.00→1.00·, 13 1.00→1.00·, 14 1.00→1.00·, 15 1.00→1.00·, 16 1.00→1.00·, 17 0.67→1.00·, 18 0.33→0.33, 19 0.67→1.00·, 20 1.00→1.00·, 21 0.00→0.33, 22 0.33→0.00·, 23 1.00→1.00, 24 0.00→0.33· | $15.48 | 10 min | 12 |
| 20260920T105602-recheck.jsonl | recheck | **RERUN** | 0.33333333333333337 | 1 | 1 | 09 0.67→1.00 | $1.22 | 3 min | 6 |
| 20260920T110035-confirm.jsonl | confirm | **KILL** | 1 | -3 | 24 | 01 1.00→1.00, 02 1.00→1.00, 03 1.00→1.00, 04 0.00→0.67·, 05 0.67→0.00, 06 0.33→0.33, 08 0.67→1.00·, 09 1.00→1.00·, 10 1.00→0.67, 11 0.00→1.00, 12 1.00→1.00·, 13 1.00→1.00·, 14 1.00→1.00·, 15 1.00→1.00·, 16 1.00→1.00·, 17 0.67→0.33·, 18 0.67→0.00, 19 0.67→0.67, 20 1.00→1.00·, 21 0.33→0.00, 22 0.33→0.00·, 23 0.33→0.67·, 24 0.00→0.33· | $15.74 | 10 min | 12 |

/evolve turns: 7, $0.93

## Journal (tail)

```
            - task 22: 0.33 -> 0 (-0.33, unexposed noise)
recheck:    task 09 re-measured at k=3: 0.67 -> 1.0 (+0.33) — confirmed noise
protected:  task 09 held at baseline, regression was variance in confirm
DECISION:   KEEP
suite:      3.67 -> 5.33

## 2026-09-20  clock-in-billing (re-tested)

kind:       rule
paths:      "shop/billing/**"
theme:      re-test of clock-in-billing promoted from previous cycle
layer:      rule — same as before
confirm:    gain +1.0 | regression +2.0 | worst_drop 0.67 | net -1.0
protected:  broke the protected set on 10 tasks
DECISION:   KILL — gate2: worst_drop 0.67 exceeds tolerance 0.34; gate3: broke protected set (10 tasks); gate4: net -3 runs under noise threshold
note:       The previously-kept clock-in-billing rule, when tested against the full task suite at k=3, showed significant regressions that were not caught in the earlier narrower screen (k=2 on failing tasks only). The rule causes a worst-case collapse of 0.67 on one task and breaks multiple previously-passing tasks. The promotion from the earlier cycle should be reverted.
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

