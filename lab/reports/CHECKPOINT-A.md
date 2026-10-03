# Checkpoint A — what was built, what the pilot measured, what the programme will cost

Written after Phase 1 (preparation) and Phase 2 (the pilot round), before the first
replicate run. `PREREGISTRATION.md` was committed before this point, at
`8014a11`; the freeze was re-cut at `23bd5e4` after a defect in the freeze
assertion itself, still before any replicate rollout (`DEVIATIONS.md` D-05).

---

## 1. What was built

| | |
|---|---|
| Frozen Cortex | tag **`v1.0-eval`** = `23bd5e4`, worktree `../cortex-eval-v1.0` |
| `cortex` resolves to | the frozen worktree, on the run's PATH, a login shell's PATH **and** the bare PATH — all three asserted before a run starts |
| Test suite | `test/run-tests.sh` **653 passed, 0 failed** |
| D0 | backed up (1,393 files), unwritable by the tools, `verify-d0` reports UNCHANGED |

**Tooling added, all before the freeze:**

- `lab/bin/guard.py` + `lab/D0-PROTECTED.txt` — the tools refuse to write to D0.
  `lab/bin/verify-d0` proves at any point that nothing moved.
- `observe` now records `turns`, `tool_calls` and `read_contributing`. The sweep row
  schema went **2 → 3**, with a test proving a schema-2 row still scores identically.
- `bench.py` takes **nine named arms** and reports each arm's always-on cost using
  Cortex's own accounting rather than a second implementation of it.
- `autopilot` gained `--no-evolve` (control runs), a 40-turn cap and a 15-minute
  per-call timeout, both recorded on the turn they stop.
- `lab/bin/run-eval` — one isolated run end to end, with its own repository, lab
  state, benchmark output and sandbox root.
- `lab/bin/export-run` — any run to flat rows.
- `lab/reports/analysis/` — `run.sh` rebuilds **every table (T1–T20) and figure
  (F1–F19)** offline from `reports/data/`, with the pre-registered margins as
  constants.

**Committed in advance, so they cannot be chosen after the fact:** 15 new holdout
scenarios (30 holdout tasks, 6 per family; all 56 validate), the two hand-written
harnesses (`ideal`, `swapped`), 29 gate-calibration candidates with the placebo word
rule enforced by their generator, and 4 prune plants.

**The exporter is verified against D0's published numbers.** It reproduces
`results/FINAL.md` exactly: holdout 36 % → 76 %; A +67, B +89, C +44, D 0, E 0;
firing 52/52, 20/27, 7/123; 1,230 rollouts; 17 cycles; $132.79 of rollouts plus
$22.66 of agent turns = $155.

---

## 2. The pilot: round 1 on the frozen Cortex

`run-eval new PILOT` → `run-eval rounds PILOT --from 1 --to 1`, Jev off, model
pinned to `claude-haiku-4-5-20251001`.

| | |
|---|---|
| Sessions | B01, B02, B03 — all three ended `ok`, one correction each, one task and one lesson harvested each |
| Verdict pattern | every session failed first on **B** (the money rule) and passed after the correction — identical to D0's round 1 |
| `/evolve` | one cycle: screen (12 rollouts) → confirm (18 rollouts) → **KEEP** |
| What it learned | `billing-rates-rule`, a **rule** on `shop/billing/**` — the same family and the same form D0 learned first, under a different name |
| Gain | +2.67 runs, regression 0.00, worst drop 0.00; task 01 0 % → 100 %, task 02 33 % → 100 %, task 03 0 % → 100 % |
| Invalid rollouts | **0 of 30** |
| Wall clock | 11 minutes end to end (12 workers) |

**The new logging fields are live in a real sweep**, which is what the pilot was for:

```
schema 3  phase screen  candidate billing-rates-rule  model claude-haiku-4-5-20251001
{"v":"cand","t":"01","r":2,"pass":1,"valid":1,"turns":9,"tool_calls":8,
 "read_contributing":0,"tokens":272533,"cost_usd":0.064709,"visible":["billing-rates-rule"]}
```

`read_contributing` is **0 in every pilot rollout**. The agent solves these tasks
without ever opening the file that documents the house rules — which is the
premise the whole lab rests on, now measured rather than assumed.

**One defect found and fixed.** `export-run` read a `task` key that the lab state
has never had (it records `tasks`, a list), so every session would have been
reported as having harvested nothing. The pilot caught it by disagreeing with its
own log. Fixed, D0 re-exported: 26 sessions, 26 harvested tasks, 17 corrections,
10 right first time — which is what `results/FINAL.md` says.

---

## 3. Measured unit costs

Everything below is measured, not estimated — each figure is the sum of
`total_cost_usd` the CLI reported per call.

| Unit | Pilot | D0's figure | |
|---|---|---|---|
| **per rollout** | **$0.1006** | $0.105 | 30 rollouts, 0 invalid |
| per session (prompt + corrections + `/harvest`) | $0.56 | ≈$0.40 | 9 turns over 3 sessions |
| per `/evolve` turn | $0.11 | — | 3 turns |
| **round 1, everything** | **$5.04** | — | 13 Claude turns + 30 rollouts, 11 min |

The per-rollout cost is the number the whole budget rests on, and the pilot
reproduces D0's to within 5 %. Sessions cost ~40 % more than D0 estimated, because
`/harvest` is the expensive turn and D0's figure averaged over cheaper ones.

---

## 4. Projected total

Modelled on D0's shape (26 sessions, 984 sweep rollouts, 17 cycles per run) at the
pilot's measured unit costs.

| Block | Rollouts | Projection |
|---|---|---|
| 4 evaluation runs (sessions + `/evolve` + sweeps) | ~3,940 | **$476** |
| 1 control run (sessions only, no `/evolve`, no sweeps) | 0 | **$15** |
| Benchmark `none`+`evolved`, 30 holdout k=5 + 26 train k=3, for R1–R4, C1 and D0 | ~2,740 | **$275** |
| 7 extra arms on R1, holdout k=3 | ~630 | **$63** |
| Gate calibration, 29 candidates | ~1,400 | **$200** |
| Prune experiment | ~950 | **$95** |
| Model change (Sonnet: 10-rollout cost pilot, holdout k=3, `/prune`) | ~200 | **$120** |
| Second repository | ~1,000 | **$200** |
| Scoring the judge (H16–H18) | 0 | **$0** — blocked, see §5 |
| **Total** | **~10,900** | **≈ $1,444** |

Against **`BUDGET_CAP_USD = 1500`**: **under the cap, but by only $56 (4 %).**

That margin is thinner than it looks. The projection assumes every run has D0's
shape; a run that needs more `/evolve` cycles, or a confirm sweep over more tasks,
moves it. The pre-registered cut order (§12 of the pre-registration) is, in order:
prune to planted items only; holdout k 5→3; evaluation runs 4→3; placebos 20→10.
Dropping the holdout to k=3 alone saves about $110 and is the cheapest lever.

**Spent so far: $5.04** (the pilot). D0's $155 was spent before this programme began
and is not charged against the cap.

---

## 5. What is blocked

**The Jev key cannot be used.** This was diagnosed to the HTTP level rather than
inferred from Cortex's fallback message:

```
POST <gateway>  {"type":"noul", ...}   ->  HTTP 403
{"error":{"message":"AI Gateway requires a valid credit card on file to service
requests.","type":"customer_verification_required"}}
```

The key **authenticates** and Cortex's request schema is **correct** — a
deliberately malformed request comes back with a schema error, so the request is
reaching the validator and passing it. The 403 is a **billing/verification block on
the Vercel AI Gateway account**: no card on file, so no request is served. It is not
an expired key, not a rate limit and not a Cortex defect.

**What it does not block:** every number for H0–H15. Every primary runs with Jev
off by design, D0 ran before Jev existed, and the gates contain no Jev code at all
(Cortex's own suite asserts the string appears nowhere in `score.sh`,
`preflight.sh` or `sweep.sh`).

**What it blocks:** H17 (NOT TESTABLE), H18 (dropped), and the judge half of H16 —
which still reports its deterministic half, glob breadth, the free alternative the
judge would have to beat. See `DEVIATIONS.md` D-01.

---

## 6. Where the scorecard stands on D0 alone

Rebuilt from `reports/data/` with one command, with no run but D0 in it:

| | |
|---|---|
| SUPPORTED | **4** — H0, H1, H2, H3 |
| NOT TESTABLE | **2** — H17, H18 (no judge) |
| INCONCLUSIVE | **13** — every block that has not run yet |

H1 on D0 alone is **+50.0 points [+25.0, +75.0]**, permutation p = 1.0 × 10⁻⁴, with
the interval marked *D0 only: no run-level interval exists* — one run cannot
estimate run-to-run variance, which is the whole reason for the replicates.

---

## 7. The decision this checkpoint asks for

1. **Jev.** Add a card to the Vercel AI Gateway account, or say to proceed without
   the judge. The programme runs either way; H16's judge half, H17 and H18 are the
   only casualties.
2. **Budget.** The projection is $1,444 against a $1,500 cap. Proceed, raise the cap,
   or apply the pre-registered cut order from the start.
