# The lab, finished — what Cortex did, and what it did not do

Ten rounds, 26 real Haiku 4.5 sessions, 17 `/evolve` cycles, 984 sweep rollouts and a
246-rollout benchmark, run the way the README says a user runs it. This is the answer to
the four questions the lab was built to ask, the numbers behind each one, and the limits
of what those numbers support.

## The verdict

| # | Question | Answer |
|---|---|---|
| 1 | Do the evolved items raise the pass rate on tasks **never seen** during evolution? | **Yes.** Holdout: **36% → 76%** (16/45 → 34/45 rollouts), with the gain concentrated in the three families that have a house rule |
| 2 | Does each house rule land in a sensible **tier**? | **Two of three as predicted, one better than predicted.** The billing rule and the exporter skill landed where the plan expected; the changelog rule landed as a *gated* skill instead of an always-on one — cheaper than predicted. The clock rule never earned a tier at all |
| 3 | Do they leave work that needs no house rule alone? | **Yes.** Control family D: 100% → 100% in both sets, and the protected-set gate killed three candidates that broke unrelated tasks |
| 4 | Does the user stop having to correct the agent? | **Not shown.** Corrections fell from 11/15 sessions (rounds 1–5) to 6/11 (rounds 6–10), but the scenarios differ between rounds, so this is suggestive, not measured |

Everything Cortex kept costs **0 always-on characters**. The 556 characters this repo
carries on every turn are the minimal `CLAUDE.md` that `cortex init` writes, not an
evolved item.

## 1. The benchmark

Nine fresh scenarios per family, never seen by `/harvest` or `/evolve`, run k=3 on the
final code against both arms. Wilson 95% intervals in brackets.

| Family | none | evolved | gain |
|---|---|---|---|
| A user-visible change (CHANGELOG) | 0% (9) [0–30] | **67%** (9) [35–88] | **+67** |
| B money (billing) | 11% (9) [2–44] | **100%** (9) [70–100] | **+89** |
| C new exporter | 0% (9) [0–30] | **44%** (9) [19–73] | **+44** |
| D control (plain bugs) | 100% (9) [70–100] | 100% (9) [70–100] | 0 |
| E time (clock) | 67% (9) [35–88] | 67% (9) [35–88] | 0 |
| **all** | **36%** (45) | **76%** (45) | **+40** |

A and B clear their intervals comfortably; C's intervals overlap slightly, so +44 is the
weakest of the three. D is the control and behaved like one. E is the family where
nothing survived evolution, and its score is unchanged — which is the honest outcome:
**no item, no gain.**

The train set (the tasks evolution actually saw) moved 21% → 59%. It is *lower* than the
holdout in both arms because it contains the hardest tasks the lab produced, and it is
not evidence for the claim — the holdout column is.

**What the harness costs per rollout:** +23% in dollars ($0.092 → $0.113) and +14% in
wall clock (42 s → 48 s). Two extra files in context, and work that used to stop early
now finishes.

One side result worth recording: the `none` arm **tampered** with the task's own checks
in 5 rollouts and broke the test suite in 7; the `evolved` arm, 1 and 4. An agent that
knows the house rule has less reason to bend the test.

## 2. What lives, and why it lives there

| Tier | Item | Area | Always-on cost | Its family's holdout gain |
|---|---|---|---|---|
| rule | `use-billing-helpers` | `shop/billing/**` | 0 | +89 |
| gated skill | `check-changelog-on-shop-edits` | `shop/**` | 0 | +67 |
| gated skill | `complete-exporter-setup` | `shop/plugins/**` | 0 | +44 |

Seven other items are buried, each with the measurement that buried it.

**The loading data is the most interesting thing in the whole benchmark:**

| Item | In context | Actually invoked |
|---|---|---|
| `use-billing-helpers` (rule) | 52 of 123 | **52 of 52** |
| `complete-exporter-setup` (gated skill) | 27 of 123 | 20 of 27 |
| `check-changelog-on-shop-edits` (gated skill) | 123 of 123 | **7 of 123** |

A rule does not need to be chosen: when the agent reads a matching file it is simply
there, and it worked every single time it was there. A skill must be *chosen* — and the
changelog skill was chosen 7 times in 123 rollouts while producing a +67-point gain.
**Its description, sitting in the context, is doing the work its body was written to
do.** That is a real finding and an uncomfortable one: the item earns its keep through a
mechanism nobody designed.

## 3. The tier law

The clearest single result of the lab, because it was measured four independent times on
the same house rule (the clock):

| Round | Form | Loaded | Outcome |
|---|---|---|---|
| 2 | gated skill for a side duty | visible 18/18 | invoked **1/18** |
| 10 | always-on skill for a side duty | visible 10/10 | invoked **0/10** → gate 5 |
| 4, 5, 8, 9 | rules for the same duties | 6/6, 24, 45 rollouts | loaded every time, then killed for what they cost **elsewhere** |

Two halves, both necessary:

- **A skill is invoked when its description names the task at hand** (`complete-exporter-setup`,
  "when implementing a new exporter plugin": 20/27) and ignored when it names a side duty
  ("verify CHANGELOG.md was updated": 1/18, 0/10). Side duties belong in rules.
- **A rule injected outside the area it is about is not free.** The clock rule was tried
  on `shop/**`, then `shop/billing/**`, then `shop/**` again. Every time it helped the
  clock task it was written for (task 11: 0 → 1.0) and every time it broke something it
  had nothing to do with — an exporter task, then ten tasks, then task 09. It competes
  for the model's attention in every file it loads into.

E is the family that ends at +0 for exactly this reason, and Cortex was right to keep
killing it. The lesson is not "the clock rule is bad" but "`shop/**` is the wrong scope
for it, and the lab never found the right one."

## 4. What the user actually experienced

| Round | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| sessions | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 1 |
| right first time | 1 | 0 | 0 | 0 | **3** | 2 | 1 | 1 | **2** | 0 |
| corrections | 2 | 3 | 3 | 3 | 0 | 1 | 3 | 1 | 0 | 1 |

Ten of 26 sessions needed no correction. Round 5 is the control family, where no house
rule applies and three of three were right — as designed. The interesting rows are 6 and
9: B04 and C04 were right first time in families that had needed a correction in *every*
early round, and both of round 9's sessions were clean.

Read it carefully, though. Sessions are not a controlled comparison: each round's
scenarios are different and the later ones are not the earlier ones made harder. The
benchmark is the controlled comparison; this table is the user's impression.

## 5. What it cost

| | Rollouts | Spend |
|---|---|---|
| sweeps (26, across 17 cycles) | 984 | $107.53 |
| benchmark (both arms, k=3) | 246 | $25.26 |
| sessions, harvests, `/evolve` and `/prune` turns | — | $22.35 |
| **total** | **1,230** | **$155** |

Wall clock after parallelism landed (12 workers on 12 CPUs): a 138-rollout confirm sweep
in 10–11 minutes, the whole 246-rollout benchmark in 16 minutes. One at a time those two
confirms alone would have been about three hours, and the benchmark about four. No
rollout was ever invalidated by load at 12 workers.

## 6. What the lab found in Cortex

**39 findings, all fixed**: 5 while designing the lab, 10 in round 1, 7 in round 2, 9 in
round 3, 5 in round 4, 3 across rounds 6–10. The test suite went from 357 to **487 tests,
all green**. The three that mattered most:

| What happened | Why it was serious | Fix |
|---|---|---|
| `score.sh` listed confirm sweeps with an unquoted `$(ls …)`, and this repo lives under "Progetti didattici" | the space split the list, so **every recheck in the lab** answered "no confirm precedes this one" and degraded to RERUN. Round 9's +4.33 candidate was killed on a regression its recheck had just cleared | read the list line by line; the regression test now runs in a path **with a space in it**. Round 9 re-scored on the fixed tooling: the first recheck does replicate, so the KILL stands — on evidence this time |
| Preflight stripped "the fix's own tests" and counted the required golden file `tests/golden/order.xml` as test code | it quarantined **every exporter task**; two sessions lost their tasks | strip test *source* only; test data (golden files, fixtures, snapshots) stays |
| Harvested checks tested things the user never asked for (a CHANGELOG entry the agent had added on its own) | no rollout could pass those tasks, so the clock rule measured 0 and was killed for it | `/harvest` rule 7: a check tests the request and the corrections, nothing else. `cortex score` now returns **RERUN**, never KILL, when no gated task could have shown a gain |

Two Cortex behaviours are worth naming as *working*, because they were what caught the
above: the **protected set** killed three candidates that helped their own family and
broke another, and **gate 5** ("a candidate that never loaded cannot have caused a
difference") killed the always-on changelog skill on its own firing data.

## 7. The `/prune` pass

`/prune` ran and decided **nothing to test** — journaled, with evidence. That is the
correct call on this harness: no item pays an always-on tax, all three are in use, and
the one replacement worth doubting (the changelog skill → a rule) had already been
measured in round 7 and killed on a regression. A pass that tests nothing is a normal
outcome, not a failure.

## 8. What this does not show

- **One model** (Haiku 4.5), **one repository**, **one experimenter**. Every number here
  is conditional on all three.
- **One holdout run** at k=3, nine scenarios per family. The intervals are wide; C's
  +44 is the one to re-measure first.
- The lab's house rules are *lintable* — a machine can tell whether they were followed.
  Rules that need judgement are not tested here at all.
- The sessions were driven by a script that plays a user faithfully but never gets
  confused, never changes its mind mid-task and always corrects in the same style.
- E ends at +0. A user with a clock problem would finish these ten rounds with nothing
  for it, and the transcript would tell them why — but Cortex found no item that helped
  without costing more elsewhere.
