# Round 5 — control (D01, D02, D03), and the clock rule finally measured

## Sessions

| Session | First attempt | Corrections | Task | Lesson |
|---|---|---|---|---|
| D01 slugify with accents | **right first time** | 0 | 14 | — |
| D02 truncate respects width | **right first time** | 0 | 15 | — |
| D03 pluralize zero | **right first time** | 0 | 16 | — |

The control family did what a control must: three plain bugs, no house rule, no
correction, no lesson — and three tasks that every later sweep must keep passing.
Sessions: 3 min, $0.6. (They stayed at 1.00 in the confirm below.)

## /evolve — cycle 12: the clock rule, measured on purpose

`/evolve` returned to the theme it could not measure in round 4, under a new name
(`enforce-shop-clock-v2`, because one name is one idea and the first is buried).

| Sweep | Verdict | Numbers |
|---|---|---|
| screen (11, 12, 13, k=2), 8 at once, **1 min** | CONFIRM | gain 1.5; the rule loaded in 6 of 6 rollouts |
| confirm (15 tasks, k=3), 8 at once, **10 min**, $9.50 | **KILL** | gain 1.33, regression 1.00, net 0.33 (1 run) — gates 2, 3 and 4 |

What it actually measured:

- **task 11: 0 → 1.0.** The rule works where it was written for: the agent that
  reached for `date.today()` every time now reads the clock through `shop.clock`.
- **task 08: 1.0 → 0.0.** An exporter task, nothing to do with time, broken in all
  three runs — the protected set.
- The rule loaded in **45 rollouts**: a rule on `shop/**` loads for *every* file in
  `shop/`, so it was in context while the agent was writing an exporter.

`/evolve`'s own note: *"the rule helped clock-related tasks but broke an unrelated
exporter task, suggesting the rule's scope is too broad."* That is the finding of
this round, and it is a real one: **a rule injected outside the area it is about
costs more than it gives.** The right scope is the files that actually break
(`shop/billing/**`, `shop/cart.py`, `shop/orders.py`), not all of `shop/`.

Two Cortex behaviours worked exactly as designed here:

- the **protected set** (gate 3) caught a regression in a family the candidate was
  not written for — the control tasks 14–16 held at 1.00 and the broken one was
  named;
- **one name, one idea**: the retry could not reuse the buried name, so the journal
  and the graveyard stay unambiguous.

## Cost and time

| | Rollouts | At once | Elapsed | Cost |
|---|---|---|---|---|
| screen | 12 | 8 | 1 min | $0.98 |
| confirm | 90 | 8 | 10 min | $9.50 |

One at a time, that confirm would have taken about **75 minutes**.
