# Checkpoint B — all data is in

**2026-09-27 02:35.** The chain (`lab/bin/programme`) finished every step: 33
markers under `cortex-eval/state/`. The development run D0 is verified unchanged
(1,393 files against its backup). Every number below is read from
`reports/data/` by `reports/analysis/`, which regenerates all of it in one command.

---

## Spend

Measured, never estimated: every session, sweep and benchmark row written under
`cortex-eval/`, each counted once (`lab/bin/usage-guard spend`).

| block | $ |
|---|---|
| Evaluation runs R1–R4 (rounds, sweeps, benchmarks, R1's ablations, R2's accept-all) | 614.47 |
| Control C1 | 37.98 |
| D0 re-measured on the expanded holdout (D0R) | 60.05 |
| Gate calibration (baseline probe + 29 candidates, one interrupted confirm) | 110.88 |
| Prune experiment | 109.69 |
| Model change (Sonnet: pilot, benchmark, `/prune`) | 213.29 |
| Second repository (structlog), including the one discarded session (D-11) | 23.09 |
| Pilot and usage probes | 5.51 |
| **Programme total** | **1,174.96** of the $1,500 cap |

D0's own development spend ($155.45) predates the programme and is not in the cap.
The judge (Jev) cost well under a dollar in all.

## What is complete

| block | rows | notes |
|---|---|---|
| Evaluation runs | R1, R2, R3, R4 | ten rounds each, Jev off, frozen `v1.0-eval` |
| Control | C1 | the same sessions, no `/evolve` |
| Benchmark, primary arms | 5 runs + D0R | holdout k=5, train k=3; **92 complete-case tasks** pooled over R1–R4 |
| Ablations (R1) | 6 arms + `accept-all` on R2 | `swapped` not run: pre-registered as conditional on `desc-only` showing an effect on a harness it can perturb, which it cannot (D-08) |
| Gate calibration | 29 of 29 | C1's repository, baseline measured (156 rollouts) |
| Prune experiment | 8 items, two passes | verdicts from Cortex's own plan (T16) |
| Model change | pilot, 336-rollout benchmark, `/prune` over every item | Sonnet 5, analysed separately |
| Second repository | 8 training sessions, 4 holdout tasks × 2 arms × k=5 | the loop kept nothing (D-12) |
| Scoring the judge | 36 candidates, D0 and R1–R4 | every row judged or not applicable with its reason |

## What is missing, and why

- **H11 (`ideal` vs `swapped`)** — `swapped` was pre-registered as the target plan only,
  to be added if `desc-only` showed an effect. On these harnesses `desc-only` perturbs
  one item in four (D-08), so there was nothing to follow up. INCONCLUSIVE.
- **H18 (a Jev-on run)** — pre-registered as the first block to cut; not run. NOT
  TESTABLE. H16 and H17, which score the judge against verdicts that already exist,
  ran in full.
- **H15 (second repository)** — ran as pre-registered, but the loop learned nothing:
  one correction in eight sessions, `/evolve` BARREN, `evolved` identical to `none`.
  The benchmark is an A/A; H15 is INCONCLUSIVE by the rule fixed before its result
  was read (D-12).

## Interruptions, and what they cost

- **A machine reboot at 18:47** killed the chain mid-gates; resumed from its markers,
  one confirm sweep lost (kept as a record, still counted as spend).
- **An API outage around 20:40** — probes hung for 180 s. The usage guard stopped the
  prune step after the first failed rollouts and did not mark it done; resumed at
  23:31 after moving the dead sweep aside.
- **Eleven defects in the instrument found and fixed today** before or as they bit,
  every one in `defects.json` (T16) with how it was detected; the ones that changed a
  procedure are in `DEVIATIONS.md` D-09 to D-12. **Two were made after their data had
  been read**, and are named here so no one has to find them: the prune experiment's
  second-pass verdicts, corrected to the verdicts Cortex itself recorded in its plan
  (matching kept strict — 5 → 6 of 8); and H13's use of D0R, D0 re-measured on the
  replicates' holdout as brief §4.4 designs it, chosen after D0R's benchmark existed —
  its verdict is SUPPORTED on either number (+42.5 re-measured, +50.0 on D0's own
  holdout). Every other fix preceded the data it touches.

The analysis may proceed.
