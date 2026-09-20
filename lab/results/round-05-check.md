# Round 5 — check

_generated 2026-09-20T10:08_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| D01 slugify with accents | D | ok | 0 | 14 | 0 | ✔ | $0.19 |
| D02 truncate respects the width | D | ok | 0 | 15 | 0 | ✔ | $0.18 |
| D03 pluralize zero | D | ok | 0 | 16 | 0 | ✔ | $0.19 |

## Harvest quality (`lab audit`)

```
D01 task 14: broken=fail house-fix=pass rule-breaking=n/a  -> discriminates
D02 task 15: broken=fail house-fix=pass rule-breaking=n/a  -> discriminates
D03 task 16: broken=fail house-fix=pass rule-breaking=n/a  -> discriminates
```

- task 14 (D01) check: `set -e ; python3 -m unittest tests.test_slugify_accents -v`
- task 15 (D02) check: `set -e ; python3 -m unittest tests.test_truncate_width.TruncateWidthTests.test_result_fits_the_width`
- task 16 (D03) check: `set -e ; python3 -m unittest tests.test_pluralize_zero.PluralizeZeroTests.test_zero_is_plural ; python3 -m unittest tests.test_text.TextTests.test_pluralize`

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

valid=15 quarantined=0 skipped=0
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
| 20260920T095540-screen.jsonl | screen | **CONFIRM** | 1 | 2 | 6 | 11 0.00→1.00, 12 1.00→1.00, 13 1.00→1.00 | $0.94 | 1 min | 8 |
| 20260920T095733-confirm.jsonl | confirm | **KILL** | 1.3333333333333335 | 1 | 45 | 01 1.00→1.00, 02 1.00→1.00, 03 1.00→1.00, 04 0.00→0.00, 05 0.67→0.67, 06 0.33→0.33, 08 1.00→0.00, 09 0.67→0.67, 10 0.67→1.00, 11 0.00→1.00, 12 1.00→1.00, 13 1.00→1.00, 14 1.00→1.00, 15 1.00→1.00, 16 1.00→1.00 | $9.5 | 10 min | 8 |

/evolve turns: 3, $0.37

## Journal (tail)

```
theme:      use shop.clock for all time operations in shop/ module (3 lessons: tasks 11, 12, 13)
layer:      rule — files in shop/clock are read during edits in that area
screen:     gain +1.5 on tasks 11, 12, 13 with k=2
            - task 11: 0 -> 1.0 (+1.0)
            - task 12: 1 -> 1 (0, held steady)
            - task 13: 0 -> 0.5 (+0.5)
confirm:    gain +1.33 | regression -1.00 | worst_drop -1.00 | net +0.33
            - task 08: 1.0 -> 0.0 (-1.0) — REGRESSION, protected task broken
            - task 10: 0.67 -> 1.0 (+0.33)
            - task 11: 0.0 -> 1.0 (+1.0)
            - task 01..07, 12..16: held steady
protected:  task 08 held in base at 3/3, broke to 0/3 in candidate
DECISION:   KILL
gates:      gate2 (worst_drop 1.0 > 0.34), gate3 (broke protected set: 08), gate4 (net 1 run < min 2)
note:       the rule helped clock-related tasks (11, 10) but broke an unrelated exporter task (08),
            suggesting the rule's scope is too broad or its content interferes with exporter logic
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

