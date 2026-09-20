# Round 7 — check

_generated 2026-09-20T10:25_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| A05 list --limit | A | ok | 0 | 20 | 0 | ✔ | $0.25 |
| B05 exact prorated refunds | B | B → ok | 1 | 21 | 1 | ✔ | $0.42 |
| E04 new arrivals | E | tampered → E → ok | 2 | 22 | 1 | ✔ | $1.18 |

## Harvest quality (`lab audit`)

```
A05 task 20: broken=fail house-fix=n/a (cli.py: expected the anchor exactly rule-breaking=n/a (cli.py: expected the anchor exactly  -> WEAK
B05 task 21: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
E04 task 22: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
```

- task 20 (A05) check: `set -e ; python3 -m unittest tests.test_list_limit`
- task 21 (B05) check: `set -e ; # Test the refund calculation is exact ; python3 -m unittest tests.test_refund_proration tests.test_refunds -v ; # Linter must pass: shop/billing/ cannot use float arithmetic ; python3 tools/lint.py`
- task 22 (E04) check: `set -e ; # Test the new_arrivals function ; python3 -m unittest tests.test_new_arrivals -v ; # Verify linter passes (enforces clock.today() usage rule) ; python3 tools/lint.py`

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

valid=21 quarantined=0 skipped=0
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
```

## Sweeps this round

| File | Phase | Verdict | Gain | Net runs | Fired | Per task (base→cand) | Cost | Elapsed | At once |
|---|---|---|---|---|---|---|---|---|---|
| 20260920T102250-screen.jsonl | screen | **REJECT** | 2 | 3 | 6 | 04 0.00→1.00, 05 0.00→1.00, 06 0.50→0.00 | $1.29 | 1 min | 12 |

/evolve turns: 1, $0.45

## Journal (tail)

```
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar

## 2026-09-20  changelog-rule-v2

kind:       rule
paths:      "shop/**"
theme:      CHANGELOG updates required when implementing shop features (4+ lessons: tasks 04, 05, 06, 17; currently fails 04, 05, 06)
layer:      rule — injects when agent Reads shop/ files, stronger than the gated skill that was never invoked
screen:     gain +2 on tasks 04, 05, 06 with k=2
            - task 04: 0 -> 1 (+1.0)
            - task 05: 0 -> 1 (+1.0)
            - task 06: 0.5 -> 0 (-0.5) — REGRESSION exceeds tolerance
DECISION:   KILL — gate2: worst_drop 0.5 exceeds regression_tolerance 0.34
note:       the rule helped tasks 04 and 05 (now fully passing on CHANGELOG in shop/cli and shop/formatting), but broke task 06 (shop/report). The rule or its interaction with the fix may be too broad for task 06's case. A narrower rule or clarification of when CHANGELOG is truly user-visible may be needed.
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

