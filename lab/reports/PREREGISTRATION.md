# Pre-registration — the Cortex evaluation programme

**Committed before the first replicate rollout.** Nothing below may be changed once
the first evaluation run starts. Anything that has to change afterwards goes in
`DEVIATIONS.md`, with the date, the reason, and whether any data had already been
seen when the decision was taken.

This document exists because the alternative — deciding how to analyse the data
after seeing it — makes every number in the report unfalsifiable. It fixes the
hypotheses, the endpoints, the tests, the margins, the exclusion rules and the
counts, in advance.

| | |
|---|---|
| Programme | evaluate Cortex's evolve/prune loop as a measurement instrument, not as a demo |
| Development run | **D0**, finished, reported separately and **never pooled** with anything below |
| System under test | Cortex at the frozen tag `v1.0-eval` (§2), reached through a dedicated worktree |
| Rollout model | `claude-haiku-4-5-20251001` everywhere, except the model-change study (§9) |
| Judge (Jev) | **off** for every number that feeds a hypothesis, set explicitly, recorded per run (§3) |
| Budget cap | `BUDGET_CAP_USD = 1500`. At Checkpoint A the total is projected from measured costs and the user is asked if it exceeds the cap |

---

## 1. Hypotheses

Each is reported as **SUPPORTED**, **NOT SUPPORTED** or **INCONCLUSIVE**, with its
estimate, interval, pre-registered margin where one applies, and a pointer to a
figure or table.

| ID | Hypothesis | Evidence |
|---|---|---|
| H0 | Without a harness the agent breaks rules A/B/C/E often and passes D | `none` arm |
| **H1** | **Primary.** On holdout tasks `evolved` beats `none`, families A+B+C+E pooled | benchmark |
| **H2** | **Primary.** Family D is not harmed (margin −10 points) and no spurious item is kept | benchmark D; kept items |
| H3 | Each kept item lands in a defensible tier and fires in its area rather than everywhere | kept items, firing data |
| H4 | Corrections fall once an item is live, **beyond** the control runs | evaluation vs control |
| H5 | Gates are calibrated: placebos rarely kept, harmful killed, positives kept | gate calibration |
| H6 | Gates add value: `accept-all` is not better than `evolved` | ablation |
| H7 | Tiers add value: `flat` costs more always-on context without gaining pass rate | ablation |
| H8 | Efficiency: `evolved` approaches `kitchen` and `ideal` at far lower always-on cost | ablation |
| H9 | Reproducible: independent runs learn the same families, in similar forms | replicate runs |
| H10 | `/prune` deletes planted useless items that fired, keeps needed ones, and **never** deletes one that never fired | prune experiment |
| H11 | The **form** matters: the right skill/rule choice beats the swapped one | `ideal` vs `swapped` |
| H12 | **The description hypothesis.** A skill's *description* alone carries much of its effect | `desc-only` arm |
| H13 | D0 replicates: what the development run found holds on the frozen version | D0 vs R1…Rn |
| H14 | After a model upgrade, re-measurement changes which items earn their place | model-change study |
| H15 | The loop also helps on a repository nobody in this project built | second repository |
| H16 | Pre-sweep **relevance** separates KEPT from BURIED-on-regression where glob **breadth** does not | `scope-replay`, no rollouts |
| H17 | The judge's predicted fire rate tracks the measured one | `scope-replay` + firing data |
| H18 | Counting every lesson and transcript chooses a different theme than reading a sample | one Jev-on run |

**H16–H18 depend on a working Jev key.** At the time of writing the key is refused
by its gateway (see `DEVIATIONS.md`), so H16 is reported from its deterministic
half (breadth) alone, H17 is reported as NOT TESTABLE, and H18 is dropped. If the
key works before the analysis, the judge half is added and the fact that it was
added late is recorded.

---

## 2. The frozen system

1. Every tooling change lands **before** the freeze, with `test/run-tests.sh` green.
2. `git tag v1.0-eval` in `Cortex/`.
3. `git worktree add ../cortex-eval-v1.0 v1.0-eval`.
4. Every run, benchmark, gate and prune process puts that worktree's `bin/` first on
   `PATH`, asserts `command -v cortex` resolves inside it, and records it in the run's
   manifest.
5. If a Cortex defect is found mid-programme: stop, document it in `DEVIATIONS.md`
   and `T16`, fix it, tag `v1.1-eval`, and **restart the affected runs from scratch**.
   Runs from different tags are never pooled in a primary result.

## 3. The judge

- Every run producing a number for H0–H15 runs `autopilot … --jev off`, which sets
  `JEV_ENABLED=0` and an empty `JEV_API_KEY` explicitly, so the treatment cannot
  depend on the operator's `.env`.
- A deliberately Jev-on run (H18 only) requires `JEV_MODEL` pinned to an exact
  version; the autopilot refuses an alias. It is never pooled with anything.
- Every run's manifest records whether Jev was on and, if so, the exact model id.
  `T20` prints one row per run, including the off ones: "off" is the claim that has
  to be checkable.
- The gates contain no Jev code, and Cortex's own suite asserts the string `jev`
  appears nowhere in `score.sh`, `preflight.sh` or `sweep.sh`. The gate calibration
  of §7 therefore measures the gates alone.

## 4. Runs

| Run | How | Count |
|---|---|---|
| R1…Rn evaluation | `autopilot round 1…10`, frozen Cortex, a fresh repository each | 3 min, **4 planned**, 5 target |
| C1…Cm control | the same sessions with `--no-evolve` | 1 min, **1 planned**, 2 target |

Each run gets its own `LAB_REPO`, its own `LAB_STATE`, its own `BENCH_OUT` and its
own `environment.sandbox_root`. Everything else in `config.yaml` is copied from D0.

**D0 is read-only.** `lab/bin/guard.py` refuses any write to the paths in
`lab/D0-PROTECTED.txt`; `lab/bin/verify-d0` proves afterwards that nothing changed.

## 5. The holdout, and the rule under which it was written

- 30 holdout scenarios, **6 per family**, run at **k=5** for the primary arms and
  **k=3** for the ablations. 26 training scenarios at k=3.
- The 15 scenarios added for this programme (`HA4-6`, `HB4-6`, `HC4-6`, `HD4-6`,
  `HE4-6`) were derived **only** from `CONTRIBUTING.md` and the family definition in
  `lab/bin/scenarios.py`, never from the text of any evolved item and never from
  what D0's harness turned out to be good at. D0's items were already known when they
  were written; the discipline is the mitigation, not a proof, and the report says so
  in its threats section.
- Each touches code no training scenario's fix touches, so it still fails on a
  finished run's code. For A, B, C and E there is a rule-breaking `naive` fix that
  **passes the scenario's own test**, so only the lint/changelog half of the oracle
  can tell it from the reference fix.
- None of them is in `ROUNDS`: nothing here is ever run as a training session.
- **Replacement rule.** A scenario is replaced only if its test does not fail on the
  injected state, its reference fix does not pass the oracle, or the environment
  errors. **Never** because the agent already follows the rule. Every replacement is
  logged in `DEVIATIONS.md`.

### 5.1 Exclusion rule, fixed in advance

Before benchmarking a run, every holdout scenario is validated **on that run's final
code**: the test must fail on the injected state and the reference fix must apply and
pass the oracle. A scenario that fails this check is excluded from that run's
benchmark **identically in every arm**, and listed in `T2`.

The primary endpoints are computed twice and both are reported:

- **complete-case (primary):** the scenarios valid in *every* evaluation run;
- **all-valid (secondary):** every scenario valid in the run it appears in.

If the two disagree in direction, the complete-case answer stands and the
disagreement is reported as a finding.

## 6. Arms

| Arm | Harness | Runs | Holdout k | Train k |
|---|---|---|---|---|
| `none` | `cortex init`'s minimal `CLAUDE.md`, nothing else | all | 5 | 3 |
| `evolved` | what that run kept | all | 5 | 3 |
| `none2` | built by the same code as `none` (A/A) | R1 | 5 | — |
| `kitchen` | `none` + the whole of `CONTRIBUTING.md` in `CLAUDE.md` | R1 | 5 | — |
| `ideal` | hand-written: A always-on skill, B rule on `shop/billing/**`, C gated skill on `shop/plugins/**`, E always-on skill | R1 | 5 | — |
| `accept-all` | `evolved` + every candidate that run buried | R1 | 5 | — |
| `flat` | `evolved`'s texts with scope removed | R1 | 5 | — |
| `desc-only` | `evolved`'s skills keep name, description and `paths`; the body becomes neutral filler of similar length | R1 | 5 | — |
| `swapped` | `ideal`'s items in the other form | R1, **only if `desc-only` shows an effect** | 3 | — |

`ideal` and `swapped` are committed **before** the first run, at
`lab/bench/harnesses/`. The derived arms are built by `bench.py arms` from the run
itself, so each run gets its own.

## 7. Gate calibration (H5)

**Testbed:** a copy of C1's final repository (tasks harvested, no items live), reset
to the same commit before every candidate. `cortex promote` is never run there.

| Type | n | Expected |
|---|---|---|
| Placebo, topic | 10 | KILL |
| Placebo, moment | 10 | KILL |
| Harmful | 5 | KILL |
| Positive (the four `ideal` items, one at a time) | 4 | KEEP |

All 29 are committed before the first run, at `lab/bench/gate-candidates/`, and are
generated by `lab/bench/make-gate-candidates.py`, which **enforces** the placebo rule:
300–1500 characters, and the text must not contain any of `test`, `lint`,
`contributing`, `changelog`, `doc`, `money`, `time`, `export`, `cent`, `clock`,
`golden`, `registry`, `billing` as a substring, case-insensitively.

**Procedure per candidate**, `/evolve`'s rules applied through the CLI so it is
deterministic:

1. `cortex sweep --candidate <c> --tasks "<screen tasks>" --phase screen --k 2`;
2. stop if `gain ≤ 0` or it never fired → KILL (screen);
3. otherwise confirm at k=3 over all valid tasks; run the recheck when asked;
4. record the verdict and every field of `cortex score`.

**Screen tasks, fixed in advance.**

- *Positives and harmful candidates:* the tasks of the family the candidate is about
  that are failing at the testbed's baseline.
- *Placebos:* **the four lowest-numbered tasks that fail at the testbed's baseline**,
  measured once before any candidate is screened and used unchanged for all twenty.
  They are chosen without reference to any placebo's text, and they are failing
  tasks on purpose: a placebo screened on tasks that already pass could not show a
  spurious gain, and a gate that only rejects candidates with no room to score has
  not been tested.

**Reported:** false-KEEP rate per placebo type and pooled, with Clopper–Pearson
intervals; KILL rate for harmful; KEEP rate for positives; fire rates; and
**Fisher's exact test** for positives against placebos.

## 8. The prune experiment (H10)

**Testbed:** a copy of R1's final repository, with `prune.max_items` raised to cover
every live item. The four planted items are committed before the first run, at
`lab/bench/prune-plants/`.

| Planted | n | Expected |
|---|---|---|
| placebo always-on skills with a *moment* description | 2 | fire, cost nothing → **ACCEPT** (deleted) |
| gated skill whose `paths` match no file any task touches | 1 | **SKIPPED** by the plan; never deleted |
| always-on skill whose description names no moment here | 1 | never fires → **UNMEASURED**; not deleted |
| R1's own evolved items | as kept | **REJECT** (kept) |

Run through `autopilot prune`, Jev off. A second pass (`cortex prune plan --items …`)
is run for any planted item the first pass skipped. If a Jev-on pass is also run, it
is an observation only: `jev_rank` is a sort order, it cannot delete anything, and
every verdict still comes from that item's own sweep.

## 9. The model-change study (H14)

1. A 10-rollout cost pilot with the stronger model (Sonnet), recorded before
   committing to the rest.
2. The holdout, arms `none` and `evolved` (R1's harness), **k=3**, stronger model,
   same tasks, same oracle, same sandboxes.
3. `/prune` under the stronger model on a fresh copy of R1, recording each item's
   verdict.

The two models are analysed separately and never pooled. A smaller gain under the
stronger model is the expected result and is a finding, not a failure.

## 10. The second repository (H15)

**Selection rule, fixed before looking at any candidate repository:** Python;
permissively licensed (MIT, BSD, Apache-2.0); its own test suite runs in under about
two minutes with no network and no credentials; at least 200 commits; a convention a
newcomer plausibly breaks that is visible in its CONTRIBUTING, its linter
configuration or its review comments; and **not** a repository that appears in
SWE-bench, SWE-gym, SWE-smith or Aider's benchmark, to limit contamination. The first
repository meeting every criterion is taken; the search order and every rejection are
recorded.

8–12 tasks are mined from its own history (tests that go from failing to passing;
the implementation reverted at a frozen base commit; the prompt written from the
issue or commit message without naming the fix), validated exactly as the lab
validates its own, and split **6–8 train / 4 holdout** before any run. Corrections
are the repository's own CI output, verbatim. One loop, then `none` vs `evolved` on
the 4 holdout tasks at k=5. Reported in its own section, **never pooled**. If fewer
than 6 valid training tasks can be mined, the attempt stops and that is reported.

---

## 11. Analysis, fixed in advance

**Primary endpoints** (evaluation runs only; D0 reported beside them, never pooled):

- **P1 (H1):** holdout `evolved − none`, families A+B+C+E pooled, paired by task
  within run. CI from a **two-way (crossed) bootstrap**: resample runs and tasks
  independently, **10,000** replicates, 95% percentile interval. **SUPPORTED if the
  lower bound is above 0.**
- **P2 (H2):** family D holdout, same method. **SUPPORTED if the lower bound is above
  −10 percentage points** and no spurious item was kept.

**Also computed, all fixed here:**

- a **permutation test** for P1: shuffle arm labels within task, 10,000 times;
- a **mixed model** as robustness: `pass ~ arm * family + (1|task) + (1|run)`, crossed
  random effects, `statsmodels` (R `lme4` if available; the report says which), with
  the caveat that 3–5 runs estimate the run variance poorly;
- **Wilson** intervals as description only, labelled as ignoring clustering;
- **Holm** correction across the four rule families A, B, C, E;
- **Clopper–Pearson** for candidate and run proportions; **Fisher's exact** for
  positives against placebos;
- **H4:** corrections per session after an item went live, against the **same
  scenarios** in the control run, by permutation over runs, with the full curve shown
  and D0's caveat that scenarios differ between rounds;
- **A/A (`none2`):** the observed difference and its CI are reported whatever they
  show. **If the interval excludes zero, every other result is treated as suspect
  until explained**, and that sentence appears in the report;
- **invalid rollouts:** excluded, counted, listed by reason (T13);
- **efficiency:** always-on characters, tokens, dollars, wall time, turns and tool
  calls per rollout, per arm;
- **failure taxonomy:** the oracle's verdicts among failures, per arm.

### 11.1 Margins, fixed in advance

| Hypothesis | Comparison | Pre-registered margin |
|---|---|---|
| H6 | `accept-all` − `evolved`, holdout, A+B+C+E | SUPPORTED if the **upper** bound of the difference is **below +5 points** (accept-all is not better) |
| H7 | `flat` − `evolved`, holdout, A+B+C+E | SUPPORTED if `flat` costs **more always-on characters** and the **upper** bound of its pass-rate difference is **below +5 points** |
| H8 | `evolved` against `kitchen` and `ideal`, holdout | SUPPORTED if `evolved`'s lower bound is **within 10 points** of the better of the two **and** its always-on cost is **lower** |
| H11 | `ideal` − `swapped`, holdout, A+B+C+E | SUPPORTED if the **lower** bound is **above +5 points** |
| H12 | `desc-only` − `none`, holdout, per family | SUPPORTED if `desc-only` recovers **at least 50 %** of `evolved`'s gain over `none`, with the lower bound of that share above 0 |
| H2 | family D, `evolved` − `none` | SUPPORTED if the lower bound is **above −10 points** |

"Points" are percentage points of pass rate. Every interval is the two-way bootstrap
of §11 unless the row says otherwise.

### 11.2 The tier rubric (H3)

Fixed here so that "a defensible tier" is not decided after seeing which tier won.
An item's tier is **defensible** when all three hold:

1. **Form matches the trigger.** A duty the task itself names ("add an exporter")
   belongs in a skill; a duty that applies while working on something else ("the
   amounts here are integer cents") belongs in a rule. A side duty in a skill is
   defensible only if it fires; a side duty in a path-less rule is defensible only if
   it costs less than its family's gain.
2. **Scope matches the area.** A path-scoped item's glob covers the files its family's
   tasks touch and does **not** cover a family it is not about. An always-on item is
   defensible only if no narrower scope would have covered its family's tasks.
3. **It fires where it is about.** Its fire rate on its own family's rollouts is
   higher than on the other families' — strictly, and by any margin.

Each kept item, in each run, is scored against these three and the answer is a
count out of three, with the evidence beside it (T6, F9). The rubric is applied by
one reader against the recorded firing data, not by eye.

---

## 12. Counts and budget

| Block | Planned |
|---|---|
| New holdout scenarios | 15 (done, before the freeze) |
| Evaluation runs | 4 × ≈$130 |
| Control runs | 1 × ≈$15 |
| Benchmark `none`+`evolved`, 30 holdout + 26 train | 5 runs, k=5 / k=3 ≈$235 |
| Extra arms on R1 | 7 arms, k=3 ≈$66 |
| Gate calibration | 29 candidates ≈$230 |
| Prune experiment | full ≈$95 |
| Model change | ≈$120 |
| Second repository | ≈$200 |
| Scoring the judge | ≈$0.30 (blocked: no working key) |
| **Total** | **≈$1,370** against `BUDGET_CAP_USD = 1500` |

**Cut order if needed**, fixed here: prune to planted items only; holdout k 5→3;
evaluation runs 4→3; placebos 20→10 (keeping both types). **Never cut:** the control
run, the holdout expansion, `none2`, the placebos, the primary `none`/`evolved` arms,
or the second repository.

---

## 13. Honesty rules

- Every run is reported, including aborted ones.
- No scenario, threshold or test is re-tuned to make a hypothesis pass.
- E failing in D0 is a result. If it fails again, that is the finding.
- Every departure from this document goes in `DEVIATIONS.md`, with whether data had
  already been seen.
- Every number in the report comes from a script in `reports/analysis/` reading
  `reports/data/`. No hand-typed numbers.
- `T18` lists every sentence the paper asserts against the figure or table that
  supports it. A sentence with no evidence is deleted, not softened.
