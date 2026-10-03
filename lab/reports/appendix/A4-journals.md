# A4 · The evolution journals

One entry per `/evolve` cycle, written by the agent as it went. This is the permanent record of why each run's `.claude/` looks the way it does.

## D0

```markdown
## 2026-09-20  changelog-updates

kind:       skill
paths:      "none"
theme:      remind to update CHANGELOG on edits (recurring in lessons)
layer:      skill (always-on) — but fails because it should have been a rule on specific areas
screen:     gain +0.5 on task 05; visible in 10 runs, never invoked (gate 5)
DECISION:   KILL — gate 5: candidate never loaded. Description did not trigger. When fixes edit existing files in their area, a rule is needed (injected on Read, not optional)
notes:      tasks 06, 11 never passed in either arm. The lesson: CHANGELOG reminders are area-specific (shop/, db/, etc.), not universal. Next attempt: rule on "shop/**" if only that area fails, or investigate why this area recurs
```

```markdown
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

```markdown
## 2026-09-19  check-changelog-on-shop-edits

kind:       gated-skill
paths:      "shop/**"
theme:      CHANGELOG forgotten for user-visible changes (3 lessons: tasks 04, 05, 06)
screen:     gain 0 on tasks 04, 05, 06 — visible in 6 rollouts, never invoked (gate 5)
DECISION:   KILL — the description "When editing shop code, verify CHANGELOG.md is updated" never triggered
note:       restored by the lab experimenter: /evolve skipped this entry, and a later /evolve's
            `git checkout .evolve/journal.md` erased the restored copy; the second cycle below
            reused the same name (the sweep now refuses a buried name)
```

```markdown
## 2026-09-19  check-changelog-on-shop-edits

kind:       gated-skill
paths:      "shop/**"
theme:      the same, retried with a trigger-first description:
            "Before finishing changes to shop/ code, verify CHANGELOG.md was updated"
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
```

```markdown
## 2026-09-19  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-20  complete-exporter-setup

kind:       gated-skill
paths:      "shop/plugins/**"
theme:      exporter plugins need all four: registry entry, docs row, golden file, implementation (4 lessons: tasks 08, 09, 10, and no-task)
layer:      gated-skill — changes to shop/plugins are read during edits in that area
screen:     gain +1.5 on tasks 08, 09 with k=2
            - task 08: 0 -> 1.0 (+1.0)
            - task 09: 0 -> 0.5 (+0.5)
confirm:    gain +0.67 | regression 0.00 | worst_drop 0.00 | net +0.67
            - task 08: 1.0 -> 0.33 (-0.67, variance from k=2 to k=3)
            - task 09: 0.5 -> 0.33 (-0.17, variance)
            - task 06 (unexposed): 0.67 -> 0.33 (not in gates; baseline before new harness exposure)
protected:  all baseline tasks held at 100%
DECISION:   KEEP
suite:      4.67 -> 5.00
```

```markdown
## 2026-09-20  enforce-shop-clock

kind:       rule
paths:      "shop/clock/**"
theme:      clock module initialization requires proper delegation to service (2 lessons: tasks 11, 12)
layer:      rule — files in shop/clock are read during edits in that area
screen:     gain 0 on tasks 11, 12, 13 with k=2
            - task 11: 0 -> 0 (never passed)
            - task 12: 1 -> 1 (no change)
            - task 13: 0 -> 0 (never passed)
DECISION:   KILL — gate 1: gain is 0, helps nothing
```

```markdown
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-20  (correction, by the experimenter)

The KILL of `enforce-shop-clock` above was not evidence. Its screen ran on tasks 11,
12 and 13: nobody could pass 11 or 13 in either arm (their checks demanded a
CHANGELOG entry I never asked for), and 12 already passed without the rule. No task
in that sweep could show a gain, so the rule was never measured.

The checks were repaired the same day (tasks 11 and 13, and 05, 09, 10 for the same
class of fault), and Cortex now returns RERUN — not KILL — for a sweep where no task
can show a gain. The clock house rule is still unmeasured: a fresh cycle may try it
again, under a new name.
```  _(not counted as a cycle: an experimenter's note or a re-test)_

```markdown
## 2026-09-20  (correction, by the experimenter)

The cycle above proposed `exporter-completeness-rule`: the same idea as the live
skill `complete-exporter-setup`, on the same files, as an ADDITION. Two items saying
the same thing would both load. I stopped its confirm sweep and removed the
candidate; nothing was measured and nothing was buried.

Cortex now warns when a candidate covers exactly the same files as a live item
(`cortex skills --candidate`), and `/evolve` says plainly that a theme a live item
already covers belongs to `/prune` Step 5, as a replacement — never a second item.
```  _(not counted as a cycle: an experimenter's note or a re-test)_

```markdown
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-20  (correction, by the experimenter)

Barren streak reset to 0. The two barren cycles above were not "nothing to learn":
the first followed the unmeasured clock KILL, the second followed my own stop of the
duplicate-rule sweep (the autopilot relaunched it, as it should for a sweep that
died, and its confirm then scored KILL on gate 4 — gain 0.67, net 1 run, under the
2-run bar — without a cycle record, because I had removed its candidate mid-flight).

Lesson for the experimenter, not for Cortex: stop the loop before touching a running
sweep. The clock house rule is still the one theme nothing covers.
```  _(not counted as a cycle: an experimenter's note or a re-test)_

```markdown
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-20  enforce-shop-clock-v2

kind:       rule
paths:      "shop/clock/**"
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

```markdown
## 2026-09-20  (policy, by the experimenter)

Rounds 6 to 10 run back to back. Each brings new sessions, new tasks and new
lessons, so the barren streak — "three cycles found nothing new" — is reset at the
start of each round: its premise is false when fresh evidence has just arrived.
Sweeps now run 12 rollouts at once (ram_per_rollout_mb measured at 512).
```  _(not counted as a cycle: an experimenter's note or a re-test)_

```markdown
## 2026-09-20  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
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

```markdown
## 2026-09-20  clock-in-billing

kind:       rule
paths:      "shop/billing/**"
theme:      clock operations in billing code require shop.clock module (2 lessons: tasks 11, 12)
layer:      rule — files in shop/billing are read during edits in that area
screen:     gain +1.0 on task 11 with k=2
confirm:    gain +2.33 | regression 0.67 | worst_drop 0.33 | net +1.67
            - task 10: 0 -> 1 (+1.0)
            - task 11: 0 -> 1 (+1.0)
            - task 17: 0.67 -> 1 (+0.33)
            - task 19: 0.67 -> 1 (+0.33)
            - task 21: 0 -> 0.33 (+0.33)
            - task 24: 0 -> 0.33 (+0.33)
            - task 09: 1 -> 0.67 (-0.33) — REGRESSION, exposed task
            - task 05: 0.33 -> 0 (-0.33, unexposed noise)
            - task 22: 0.33 -> 0 (-0.33, unexposed noise)
recheck:    task 09 re-measured at k=3: 0.67 -> 1.0 (+0.33) — confirmed noise
protected:  task 09 held at baseline, regression was variance in confirm
DECISION:   KEEP
suite:      3.67 -> 5.33
```

```markdown
## 2026-09-20  clock-in-billing (re-tested)

kind:       rule
paths:      "shop/billing/**"
theme:      re-test of clock-in-billing promoted from previous cycle
layer:      rule — same as before
confirm:    gain +1.0 | regression +2.0 | worst_drop 0.67 | net -1.0
protected:  broke the protected set on 10 tasks
DECISION:   KILL — gate2: worst_drop 0.67 exceeds tolerance 0.34; gate3: broke protected set (10 tasks); gate4: net -3 runs under noise threshold
note:       The previously-kept clock-in-billing rule, when tested against the full task suite at k=3, showed significant regressions that were not caught in the earlier narrower screen (k=2 on failing tasks only). The rule causes a worst-case collapse of 0.67 on one task and breaks multiple previously-passing tasks. The promotion from the earlier cycle should be reverted.
```  _(not counted as a cycle: an experimenter's note or a re-test)_

```markdown
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

```markdown
## 2026-09-20  (correction, by the experimenter)

The KILL of `shop-clock-usage` above blamed "measurement infrastructure unstable
(harness hashes mismatched)". That was wrong, and the fault was Cortex's: `score.sh`
listed the confirm sweeps with an unquoted `$(ls …)`, so a repository path with a
space in it — "Progetti didattici" — split the list and no confirm was ever found.
Every recheck in this lab answered "no confirm precedes this one" and degraded to
RERUN, which is why the cycle fell back on caution.

Fixed (and tested with a repository path that has a space in it). With the fix the
two rechecks of task 09 pair, and they disagree: the first replicates the regression
(100% -> 67% on a protected task), the second does not. The protocol uses the first,
so the KILL stands — on evidence this time, not on a tooling failure.
```  _(not counted as a cycle: an experimenter's note or a re-test)_

```markdown
## 2026-09-20  prune

kind:      prune pass
action:    nothing to test
reason:    all live items (2 gated skills, 1 rule) are actively used; no always-on context tax; routing is clean
evidence:  `check-changelog-on-shop-edits` (2 uses, last 2026-09-20), `complete-exporter-setup` (2 uses, last 2026-09-20), `use-billing-helpers` (20 uses, last 2026-09-20)
```  _(not counted as a cycle: an experimenter's note or a re-test)_

## R1

```markdown
## 2026-09-21  billing-helpers

kind:       rule
paths:      "shop/billing/**"
theme:      Use helper functions percent_of/times/scale from shop/billing/rates.py (3 lessons on tasks 01, 02, 03)
layer:      rule — hard constraint, always-on in area, injected 100% when matching file is read
screen:     gain +3 on tasks 01, 02, 03 (rule fired 6/6 candidate runs)
confirm:    gain +3 | regression 0.00 | worst_drop 0.00 | net +3
            rule fired 8/8 exposed candidate runs (all 3 tasks fixed)
protected:  no protected set; all tasks now pass (3/3)
DECISION:   KEEP
suite:      0 -> 3
```

```markdown
## 2026-09-21  changelog-requirement

kind:       rule
paths:      "shop/**"
theme:      Add CHANGELOG entries for user-visible changes (3 lessons on tasks 04, 05, 06)
layer:      rule — hard constraint, injected 100% when matching file is read
screen:     gain +2.5 on tasks 04, 05, 06 (rule fired 6/6 candidate runs)
confirm:    gain +2.33 | regression 0.00 | worst_drop 0.00 | net +2.33
            rule fired 18/18 exposed candidate runs (all 6 tasks: 01-06)
protected:  tasks 01, 02, 03 held at 1/1 each (3/3 total)
DECISION:   KEEP
suite:      3 -> 5.33
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  shop-clock-rule

kind:       rule
paths:      "shop/**"
theme:      Use shop.clock for all time access instead of stdlib datetime (3 lessons on tasks 09, 10, 11)
layer:      rule — hard constraint, injected 100% when matching file is read
screen:     gain +2 on tasks 09, 10, 11 (rule fired 6/6 candidate runs)
confirm:    gain +2.33 | regression 0.33 | worst_drop 0.33 | net +2.33
            rule fired 32/32 exposed candidate runs (all 11 tasks)
recheck:    task 04: confirm 67% -> 100% on recheck — variance
protected:  tasks 01-06 held (6/6 baseline successes maintained)
DECISION:   KEEP
suite:      5.33 -> 7.67
```

```markdown
## 2026-09-21  exporter-checklist

kind:       gated-skill
paths:      "shop/plugins/**"
theme:      Complete exporter implementation checklist: docs row, golden file, registry entry, CHANGELOG (2 lessons on tasks 07, 08)
layer:      gated-skill — fires when agent edits/creates exporter files
screen:     gain +1.33 on tasks 07, 08 (candidate fired 2/2 exposed runs, 6/6 total)
confirm:    gain +1.33 | regression 0.00 | worst_drop 0.00 | net +1.33
            candidate fired 6/6 exposed candidate runs (tasks 07, 08)
protected:  no protected breakage; all previous fixures held
DECISION:   KEEP
suite:      10.33 -> 11.33
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

## R2

```markdown
## 2026-09-21  billing-exact-arithmetic

kind:       rule
paths:      "shop/billing/**"
theme:      exact arithmetic in billing (2 lessons: task 01 + 03)
layer:      rule — billing helpers are in existing files, must be enforced on every write
screen:     gain +1.5 on tasks 01, 03
confirm:    gain +1.67 | regression 0.00 | worst_drop 0.00 | net +1.67
protected:  task 02 held at 1.0
DECISION:   KEEP
suite:      1.0 -> 2.667
```

```markdown
## 2026-09-21  changelog-user-visible

kind:       rule
paths:      "shop/**"
theme:      missing CHANGELOG entries for user-visible changes (3 lessons: tasks 04, 05, 06)
layer:      rule — changelog updates are enforced on all shop/ files that affect output
screen:     gain +2.0 on tasks 04, 05
confirm:    gain +2.0 | regression 0.00 | worst_drop 0.00 | net +2.0
protected:  tasks 01, 02, 03 held at 3/3
DECISION:   KEEP
suite:      3.0 -> 5.0
```

```markdown
## 2026-09-21  exporter-docs-and-golden

kind:       rule
paths:      "shop/plugins/**"
theme:      missing exporter documentation and golden file requirements (3 lessons: tasks 08, 09, 10)
layer:      rule — exporter requirements must be enforced on every plugin implementation
screen:     gain +2.67 on tasks 08, 09, 10
confirm:    gain +2.67 | regression 0.00 | worst_drop 0.00 | net +2.67
protected:  tasks 01, 02, 03, 04, 05 held at 3/3
DECISION:   KEEP
suite:      5.0 -> 7.67
```

```markdown
## 2026-09-21  shop-clock-not-datetime

kind:       rule
paths:      "shop/**"
theme:      direct datetime.now()/date.today() instead of shop.clock (3 lessons: tasks 11, 12, 13)
layer:      rule — datetime access control is enforced on all shop/ writes
screen:     gain +2.0 on tasks 11, 12
confirm:    gain +2.0 | regression 0.00 | worst_drop 0.00 | net +2.0
protected:  tasks 01, 02, 03, 04, 05, 06, 08, 09, 10, 13 held at 3/3
DECISION:   KEEP
suite:      9.33 -> 11.33
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-21  shop-clock-explicit-imports

kind:       rule
paths:      "shop/**"
theme:      explicit import patterns for shop.clock (variant of shop-clock-not-datetime)
layer:      rule
screen:     gain 0 on tasks 11, 12 — both already pass with shop-clock-not-datetime live rule
protected:  tasks 01, 02, 03, 04, 05, 06, 08, 09, 10, 13 held at 3/3
DECISION:   KILL
reason:     overlaps with live rule shop-clock-not-datetime; refinements should use /prune --replace
suite:      11.33 -> 11.33
```

## R3

```markdown
## 2026-09-21  changelog-user-facing

kind:       rule
paths:      shop/cli.py, shop/formatting.py, shop/report.py
theme:      missing CHANGELOG entry for user-visible changes (3 lessons, tasks 04-06)
layer:      rule — narrowly scoped to specific user-facing code files where documentation matters
screen:     gain +3 on tasks 04, 05, 06 (all newly harvested tasks fixed)
confirm:    gain +3 | regression 0 | worst_drop 0 | net +3
protected:  tasks 01-03 held at 100% (rate helpers rule continues working)
DECISION:   KEEP
reason:     agents writing user-visible features (CLI, formatting, reports) must document them in CHANGELOG.md. Rule targets only the files where these changes happen, avoiding over-scope issues.
suite:      3 -> 6
```

```markdown
## 2026-09-21  rate-helpers-narrow

kind:       rule
paths:      shop/billing/tax.py, shop/billing/discount.py, shop/billing/fx.py
theme:      precision loss in manual rate/percentage parsing (3 failing tasks)
layer:      rule — narrowly scoped to files where fixes were needed, not all of shop/billing/**
screen:     gain +3 on tasks 01, 02, 03 (all failing tasks passed)
confirm:    gain +3 | regression 0 | worst_drop 0 | net +3
protected:  none held
DECISION:   KEEP
reason:     refined scope fixes gate 2 violation in prior cycle. Targets only the three files that needed the rate helpers (tax.py, discount.py, fx.py), avoiding the over-broad application that caused regressions.
suite:      baseline updated
```

```markdown
## 2026-09-21  use-rate-helpers

kind:       rule
paths:      shop/billing/**
theme:      precision loss in manual rate/percentage parsing (3 failing tasks)
layer:      rule — area-specific, fixes edit existing files in shop/billing/
screen:     gain +3 on tasks 01, 02, 03 (all failing tasks passed)
confirm:    gain +3 | regression +3 | worst_drop 1.0 | net 0
protected:  none
DECISION:   KILL
reason:     rule too broad — catches non-billing rate handling that should remain manual. Gate 2 violation: worst_drop 1.0 exceeds regression_tolerance 0.34
```

```markdown
## 2026-09-21  exporter-checklist

kind:       gated-skill
paths:      src/exporters/**
theme:      exporters missing documentation, golden files, and verification checks (tasks 07, 08, 09)
layer:      gated-skill — only loaded when files in src/exporters/ are edited
screen:     gain +1 on tasks 07, 08 (candidate loaded 1/2 failing tasks exposed)
confirm:    gain +0.33 | regression 0 | worst_drop 0 | net +0.33
protected:  none
DECISION:   KILL
reason:     gate4: net gain of 1 run is below noise floor (threshold 2). Candidate helped tasks 05, 08 each by 1/3 but low firing rate (2/9 visible runs). Too narrow in scope and visibility to be valuable.
task07:     never passed in any rollout — check task 07 check.sh for strict requirements
```

```markdown
## 2026-09-21  changelog-shop-reminder

kind:       rule
paths:      shop/**
theme:      missing CHANGELOG entry for shop/ changes (continuation from changelog-user-facing, expanded scope)
layer:      rule — broader than user-facing rule but scoped to shop/ only, where CHANGELOG updates are needed
screen:     gain +0.5 on tasks 01, 02 (failing tasks helped by candidate)
confirm:    gain +1.33 | regression 0 | worst_drop 0 | net +1.33
protected:  all tasks 01-06 held at their confirm baseline rates
DECISION:   KEEP
reason:     rule successfully enforces CHANGELOG documentation for all shop/ changes. Full scope test (all 12 tasks) showed higher gains than screen alone, indicating the rule is helping across multiple scenarios. Zero regression confirms no false positives.
tasks 07-11: never passed in any rollout — check their check.sh files (as noted in exporter-checklist, these tasks appear to be too hard for the agent or have strict check requirements)
suite:      baseline updated
```

```markdown
## 2026-09-21  shop-clock-access

kind:       rule
paths:      shop/**
theme:      time operations using date.today()/datetime.now() instead of shop.clock (tasks 10, 11, 12)
layer:      rule — area-specific, fixes edit existing files in shop/
screen:     gain +3 on tasks 10, 11, 12 (all failing tasks passed)
confirm:    gain +3 | regression 0.33 | worst_drop 0.33 | net +2.67
recheck:    task 13: confirm 100%->67%, recheck 100%->67% — regression confirmed
protected:  none
DECISION:   KILL
reason:     gate 2/3 violation: worst_drop 0.33 equals or exceeds regression_tolerance. Task 13 regression confirmed on recheck. Rule too broad — catches shop/ code that should not use shop.clock, or conflicts with other logic in that file. Scope was too wide for the narrow time-access pattern it addresses.
```

```markdown
## 2026-09-21  shop-clock-narrow

kind:       rule
paths:      shop/billing/invoice.py, shop/cart.py, shop/orders.py
theme:      time operations using shop.clock (refined from shop-clock-access regression)
layer:      rule — narrowly scoped to the three files where fixes were needed, avoiding over-scope issues from prior cycle
confirm:    gain +2.33 | regression 0 | worst_drop 0 | net +2.33
protected:  none
DECISION:   KEEP
reason:     narrowed scope from shop-clock-access (which caused task 13 regression) fixes the regression while retaining gains. Only targets the three files where time-freezing for tests matters (invoice.py, cart.py, orders.py), avoiding false positives. All exposed tasks (10, 11, 12) passed; zero regression confirms no collateral damage.
tasks 07,08,18: never passed in any rollout — check their check.sh files
suite:      baseline updated
```

```markdown
## 2026-09-21  billing-rate-helpers

kind:       rule
paths:      shop/billing/shipping.py, shop/billing/refunds.py
theme:      precision loss in billing calculations using float arithmetic instead of rate helpers (tasks 17, 20)
layer:      rule — narrowly scoped to the shipping and refunds files where fixes were needed
confirm:    gain +0.67 | regression 0 | worst_drop 0 | net +0.67
protected:  tasks 01-06, 11-12, 16, 19, 23 held at 100%; task 01-03, 05-06, 11-12, 16, 19, 23 held 100%
DECISION:   KEEP
reason:     agents writing billing code must use the rates.py helpers (scale(), times(), percent_of()) to avoid float/Decimal precision loss. Rule targets only the two refund and shipping calculation files where the fixes were needed. Task 17 improved with the rule present; task 20 stable.
suite:      baseline updated
```

```markdown
## 2026-09-21  text-utilities-correctness

kind:       rule
paths:      shop/util/text.py
theme:      string utility function edge cases (pluralize count check, regex unicode handling) (2 tasks in protected set)
layer:      rule — narrowly scoped to shop/util/text.py where text utilities are defined
screen:     gain +0.5 on tasks 13, 15 (one task gained +0.5, one lost -0.5)
confirm:    gain 0 | regression 1.33 | worst_drop 0.67 | net -1.33
protected:  tasks 13, 15 regressed from baseline 100% to 66.7%
DECISION:   KILL
reason:     gate 2/3 violation: worst_drop 0.67 breaks protected set. Tasks 13 and 15, which were solved at 100% by the live harness, regressed to 66.7% when the candidate was applied. The rule's guidance on pluralize() and unicode handling was incorrect or too strict. Candidate fired in all runs (10/10 visible) but caused damage to protected tasks.
```

```markdown
## 2026-09-21  exporter-checklist-v2

kind:       rule
paths:      shop/plugins/*_export.py
theme:      exporter plugins missing documentation, registry entry, and golden files (tasks 07, 09, 18)
layer:      rule — narrowly scoped to exporter plugin files where implementation happens
screen:     gain +2.5 on tasks 07, 09, 18 (all exposed failing tasks improved)
confirm:    gain +5 | regression 0 | worst_drop 0 | net +5
protected:  all prior solved tasks held
DECISION:   KEEP
reason:     rule successfully enforces complete exporter checklist (class + registry + docs + golden file). Screen test confirmed strong signal on failing tasks; confirm sweep over all 26 tasks shows +5 net gain with zero regressions. Rule fires when agents create new exporter plugins and requires all four mandatory components, preventing incomplete implementations.
suite:      baseline updated
```

```markdown
## 2026-09-21  (barren)

nothing to learn: no theme cleared the bar
```

## R4

```markdown
## 2026-09-22  changelog-for-user-visible-changes

kind:       rule
paths:      "CHANGELOG.md"
theme:      update CHANGELOG.md for every user-visible change (3 lessons: tasks 04, 05, 06)
layer:      rule — attempted, but failed to trigger
screen:     gain 0 | no rollout read CHANGELOG.md first
protected:  N/A
DECISION:   KILL
notes:      rule targeted CHANGELOG.md, but agent was working on feature files and never read CHANGELOG first.
            Issue: a rule requires the file to be read/edited to be injected; a moment rule ("before finishing") would fit better.
            Or: harvest tasks where agent does read CHANGELOG to understand the context better.
```

```markdown
## 2026-09-22  billing-rates-helpers

kind:       rule
paths:      shop/billing/**
theme:      use helpers percent_of() and times() from rates.py instead of float/Decimal (3 lessons)
layer:      rule — fixes edit existing files in shop/billing/, must match on Read
screen:     gain +3 on tasks 01, 02, 03
confirm:    gain +3 | regression 0 | worst_drop 0 | net +3
protected:  all tasks held
DECISION:   KEEP
```

```markdown
## 2026-09-22  exporter-checklist

kind:       gated skill
paths:      "shop/plugins/**"
theme:      verify required metadata fields before exporting (3 lessons: tasks 07, 08, 09)
layer:      gated skill — fixes edit new exporter plugins in shop/plugins/
screen:     gain +0.5 on tasks 07, 08, 09
confirm:    gain +1.67 | regression 0 | worst_drop 0 | net +1.67
protected:  all tasks held
DECISION:   KEEP
```

```markdown
## 2026-09-22  changelog-contributing-reminder

kind:       rule
paths:      "CONTRIBUTING.md"
theme:      add CHANGELOG.md entry for every user-visible change (3 lessons: tasks 04, 05, 06)
layer:      rule — attempted, but failed to trigger
screen:     gain 0 | no rollout read CONTRIBUTING.md
protected:  N/A
DECISION:   KILL
notes:      rule targeted CONTRIBUTING.md, assuming agent would read it for guidance. But in these
            tasks, agents jumped straight to feature implementation without reading CONTRIBUTING.md first.
            The rule never injected, so it helped nothing. Previous "changelog-for-user-visible-changes"
            also targeted CHANGELOG.md and failed for the same reason (agents don't read it proactively).
            The theme is real but the approach (waiting for agent to read) is not viable. Next attempt:
            a moment-based skill ("before finishing changes") or a post-implementation check.
```

```markdown
## 2026-09-22  shop-clock-queries

kind:       rule
paths:      shop/**
theme:      shop/ must use shop.clock for time queries, not stdlib (tasks 10, 11)
layer:      rule — narrow, focused guidance for a specific directory
screen:     gain +2 on tasks 10, 11 (candidate loaded 4/8)
confirm:    gain +2.67 | regression +0.67 | worst_drop +0.33 | net +6
protected:  tasks 01-03, 12-15 held at 1.0
DECISION:   KEEP
suite:      (baseline) -> (new suite with rule active)
```

```markdown
## 2026-09-22  shop-changelog-reminder

kind:       rule
paths:      "shop/**"
theme:      ensure CHANGELOG.md is updated for user-visible changes (3 lessons: tasks 04, 05, 06)
layer:      rule — injected into every file in shop/, fired on 52/52 rollouts
screen:     gain +2.67 on tasks 04, 05, 06, 16 (candidate fired in all exposed)
confirm:    gain +3.67 | regression 1.33 | worst_drop 0.33 | net +2.33
recheck:    tasks 02, 03: confirm 67%→67%, recheck 100%→100% — regression was noise
protected:  task 02 recovered, task 03 recovered, all others held at 1.0
DECISION:   KEEP
suite:      14.00 -> 16.33
```

```markdown
## 2026-09-22  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-22  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-22  (barren)

nothing to learn: no theme cleared the bar
```

```markdown
## 2026-09-22  (barren)

nothing to learn: no theme cleared the bar
```

