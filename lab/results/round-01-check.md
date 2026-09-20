# Round 1 — check

_generated 2026-09-19T15:00_

## Sessions

| Scenario | Family | Verify sequence | Corrections | Task | Lessons | Start OK | Session cost |
|---|---|---|---|---|---|---|---|
| B01 fractional tax rates | B | B → ok | 1 | 01 | 1 | ✔ | — |
| B02 fractional discounts | B | ok | 0 | 02 | 0 | ✔ | — |
| B03 four-decimal exchange rates | B | B → ok | 1 | 03 | 1 | ✔ | — |

## Harvest quality (`lab audit`)

```
B01 task 01: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
B02 task 02: broken=fail house-fix=pass rule-breaking=pass  -> WEAK: passes a rule-breaking fix
B03 task 03: broken=fail house-fix=pass rule-breaking=fail  -> discriminates
```

- task 01 (B01) check: `set -e ; # Run the fractional tax rate tests ; python3 -m unittest tests.test_tax_rates -v ; # Run all tax tests to ensure no regression ; python3 -m unittest tests.test_tax -v ; # Verify lint passes (user corrected us: `
- task 02 (B02) check: `set -e ; cd "$(git rev-parse --show-toplevel)" ; python -m unittest tests.test_discount_rates tests.test_discount -v`
- task 03 (B03) check: `set -e ; python3 -m unittest tests.test_fx_rates ; make lint`

## Preflight

```
task    broken-state  fixed-state  verdict
------  ------------  -----------  -------
01      fail          pass         ok
02      fail          pass         ok
03      fail          pass         ok

valid=3 quarantined=0 skipped=0
```

## Lessons

```
2026-09-19 | task 01 | used Decimal arithmetic in billing/ module | use percent_of() helper for exact percentage calculations
2026-09-19 | task 03 | used float arithmetic in billing code when linting rejected it | use times() helper for exact arithmetic in billing module
```

## Sweeps this round

| File | Phase | Verdict | Gain | Net runs | Fired | Per task (base→cand) | Cost | Wall |
|---|---|---|---|---|---|---|---|---|
| 20260919T140208-screen.jsonl | screen | **CONFIRM** | 2 | 4 | 6 | 01 0.00→1.00, 02 1.00→1.00, 03 0.00→1.00 | $0.85 | 7 min |
| 20260919T144806-confirm.jsonl | confirm | **KEEP** | 1.6666666666666667 | 5 | 9 | 01 0.00→1.00, 02 1.00→1.00, 03 0.33→1.00 | $1.34 | 11 min |

/evolve turns: 2, $0.29

## Journal (tail)

```
of why the skills folder looks the way it does.

## 2026-09-19  use-billing-helpers

kind:       rule
paths:      "shop/billing/**"
theme:      use rate helpers for exact arithmetic (2 lessons: tasks 01, 03)
layer:      rule — files in shop/billing are read during fixes in billing code
screen:     gain +N on tasks 01, 02, 03 with k=2
confirm:    gain +1.67 | regression 0.00 | worst_drop 0.00 | net +1.67
  - task 01: 0 -> 1 (+1.0) — Decimal arithmetic fixed with percent_of()
  - task 02: 1 -> 1 (0) — held steady, no billing changes
  - task 03: 0.33 -> 1.0 (+0.67) — float arithmetic fixed with times()
protected:  none
DECISION:   KEEP
suite:      1.33 -> 3.00
```

## Routing after the round

```
routing  always-on 556/3000 chars   (always-on skills + path-less rules + CLAUDE.md)
  TIER         NAME                 STATUS    ALWAYS  PATHS / TRIGGER
  rule         use-billing-helpers  ok             0  shop/billing/**
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

## Autopilot findings

- none

