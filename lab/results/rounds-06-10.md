# Rounds 6–10 — the mixed families, run unattended

Rounds 6 to 10 ran back to back with no one watching (`bin/run-rounds 7 10`), each
one: three (or two, or one) sessions, then `/evolve` until its cycle ended, then my
check. Per-round numbers are in `round-NN-check.md`.

## Sessions: the live items start to show

| Round | Sessions | Corrections | Tasks | Lessons |
|---|---|---|---|---|
| 6 | A04 out-of-stock label, B04 pro-rata shipping, C04 NDJSON export | **1, 0, 0** | 17, 18, 19 | 1 |
| 7 | A05 `--limit`, B05 prorated refunds, E04 new arrivals | **0, 1, 2** | 20, 21, 22 | 2 |
| 8 | C05 HTML export, D04 business days | **1, 0** | 23, 24 | 1 |
| 9 | A06 ISO dates, B06 price per kilo | **0, 0** | 25, 26 | 0 |
| 10 | C06 YAML export | **1** | 27 | 1 |

Eleven sessions, **six of them right the first time** — including B04 and C04, whose
families (money, exporters) needed a correction in every early round, and both of
round 9's. The suite ends at **27 tasks**.

## Cycles: five more, no keeps — and they agree with each other

| Round | Candidate | Result |
|---|---|---|
| 6 | — | barren: no correction, no lesson, nothing to learn |
| 7 | `changelog-rule-v2` — the changelog **skill → rule**, swept as a replacement | gain +2 (tasks 04, 05 fully fixed) but **−0.5 on task 06** → killed on the regression gate |
| 8 | `clock-in-billing` — rule on `shop/billing/**` | screen +1.0, confirm +2.33 … then **regression 2.0 across the suite**: KILL |
| 9 | `shop-clock-usage` — rule on `shop/**` | confirm **gain +4.33**, one regression on task 09 → RECHECK → (see the pairing bug below) → KILL |
| 10 | `changelog-updates` — an **always-on skill** for the changelog | **visible in 10 rollouts, invoked in none** → gate 5 |

Three independent measurements now say the same thing about tiers:

- round 2: a gated skill for a side duty was invoked **1 time in 18**;
- round 10: an always-on skill for the same duty, **0 times in 10** — killed by the
  gate that exists for exactly this ("a candidate that never loaded cannot have
  caused a difference");
- rounds 7, 8, 9: rules for those duties **do** load (6/6, 24, 45 rollouts) — and
  then get killed for what they cost elsewhere, not for failing to arrive.

**The clock rule is the clearest result of the whole lab.** Tried three times —
`shop/**`, then `shop/billing/**`, then `shop/**` again — it always helps where it
was written for (task 11: 0 → 1.0) and always breaks something it has nothing to do
with (an exporter task, then ten tasks, then task 09). A rule injected into work it
is not about is not free: it competes for the model's attention.

## Findings, fixed mid-run (Cortex: 487 tests)

| # | What happened | Fix |
|---|---|---|
| 1 | **Every recheck in this lab failed to pair with its confirm.** `score.sh` listed the confirms with an unquoted `$(ls …)`, and this repository lives under "Progetti didattici" — the space split the list, so no confirm was ever found and every recheck answered "no confirm precedes this one", degrading to RERUN. Round 9's candidate (gain +4.33) was killed on a regression its recheck had just cleared | read the list line by line; regression test runs in a path **with a space in it**. Round 9 re-scored: the first recheck does replicate the regression, so the KILL stands — on evidence, not on tooling |
| 2 | A **screen** of a *removal* returned a final REJECT on three tasks at k=2 — a cheap filter deciding the fate of a live item | a screen of a replacement says CONFIRM or KILL, never ACCEPT/REJECT, exactly as "a screen never KEEPs" |
| 3 | A sweep that died with its session was scored on the 120 rollouts it had | already fixed that morning: it ends `incomplete`, `cortex score` refuses it and names the three tasks that never ran. It fired for real here, and `/evolve` relaunched the sweep |

## What the parallel sweeps cost

| Round | Biggest sweep | Rollouts | At once | Elapsed |
|---|---|---|---|---|
| 8 | confirm | 138 | 12 | 10 min |
| 9 | confirm | 138 | 12 | 11 min |
| 9 | recheck | 6 | 6 | 1 min |

One at a time those two confirms alone would have taken about **three hours**. No
rollout was invalid at 12 workers: no rate limiting, and the oversubscription note
stayed quiet apart from a handful of rollouts at 14.8 runnable tasks on 12 CPUs.
