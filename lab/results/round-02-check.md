# Round 2 — check

_generated 2026-09-19T16:25_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| A01 list cheapest first by default | A | A → ok | 1 | 04 | 1 | ✔ | $0.28 |
| A02 thousands separator in prices | A | A → ok | 1 | 05 | 1 | ✔ | $0.33 |
| A03 report total row | A | A → ok | 1 | 06 | 1 | ✔ | $0.38 |

## Harvest quality (`lab audit`)

```
A01 task 04: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
A02 task 05: broken=fail house-fix=pass rule-breaking=pass  -> WEAK: passes a rule-breaking fix
A03 task 06: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
```

- task 04 (A01) check: `set -e ; # Check the specific failing tests now pass ; python3 -m unittest tests.test_list_default_sort -v ; # Verify CHANGELOG.md was updated ; if git diff --quiet 556d19d -- CHANGELOG.md; then ;   echo "CHANGELOG.md no`
- task 05 (A02) check: `set -e ; python3 -m unittest tests.test_money_display.ThousandsSeparatorTests -v`
- task 06 (A03) check: `set -e ; # Check that the test passes ; python3 -m unittest tests.test_report_total -v ; # Check that existing tests still pass ; python3 -m unittest tests.test_report -v ; # Check that CHANGELOG.md was updated ; if git `

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

valid=6 quarantined=0 skipped=0
```

## Lessons

```
2026-09-19 | task 01 | used Decimal arithmetic in billing/ module | use percent_of() helper for exact percentage calculations
2026-09-19 | task 03 | used float arithmetic in billing code when linting rejected it | use times() helper for exact arithmetic in billing module
2026-09-19 | task 04 | shipped without updating CHANGELOG.md | add user-visible changes to CHANGELOG.md under [Unreleased]
2026-09-19 | task 05 | implemented feature without updating CHANGELOG.md initially | add CHANGELOG entry together with the implementation commit
2026-09-19 | task 06 | committed implementation without updating CHANGELOG.md | always check and update CHANGELOG.md for user-visible features
```

## Sweeps this round

| File | Phase | Verdict | Gain | Net runs | Fired | Per task (base→cand) | Cost | Wall |
|---|---|---|---|---|---|---|---|---|
| 20260919T151239-screen.jsonl | screen | **KILL** | 0 | 0 | 0 | 04 0.00→0.00, 05 1.00→1.00, 06 0.00→0.00 | $1.05 | 8 min |
| 20260919T152150-screen.jsonl | screen | **CONFIRM** | 1 | 2 | 1 | 04 0.00→0.50, 05 1.00→1.00, 06 0.00→0.50 | $1.12 | 8 min |
| 20260919T153045-confirm.jsonl | confirm | **RERUN** | 0 | 0 | None |  | $0.24 | 4 min |
| 20260919T153455-confirm.jsonl | confirm | **RERUN** | 0 | 0 | 0 |  | $None | 0 min |
| 20260919T153555-confirm.jsonl | confirm | **RERUN** | 0 | 0 | 0 |  | $0.29 | 2 min |
| 20260919T154520-confirm.jsonl | confirm | **KEEP** | 0.6666666666666666 | 2 | 1 | 01 1.00→1.00, 02 1.00→1.00, 03 1.00→1.00, 04 0.00→0.33, 05 1.00→1.00, 06 0.00→0.33 | $3.06 | 24 min |

/evolve turns: 9, $1.37

## Journal (tail)

```
layer:      gated-skill — changes to shop/ files are read during edits in that area
screen:     gain +1.0 on tasks 04, 06 (0 -> 0.5 each); invoked in 1 of 6 cand rollouts
confirm:    gain +0.67 | regression 0.00 | worst_drop 0.00 | net +0.67
  - task 01: 1 -> 1 (0) — held steady
  - task 02: 1 -> 1 (0) — held steady
  - task 03: 1 -> 1 (0) — held steady
  - task 04: 0 -> 0.33 (+0.33) — CHANGELOG rule fired
  - task 05: 1 -> 1 (0) — held steady
  - task 06: 0 -> 0.33 (+0.33) — CHANGELOG rule fired
protected:  all tasks held at baseline
DECISION:   KEEP
suite:      3.00 -> 3.67

## 2026-09-19  (barren)

nothing to learn: no theme cleared the bar
```

## Routing after the round

```
routing  always-on 556/3000 chars   (always-on skills + path-less rules + CLAUDE.md)
  TIER         NAME                           STATUS    ALWAYS  PATHS / TRIGGER
  gated        check-changelog-on-shop-edits  ok             0  shop/**
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

## Autopilot findings

- none

