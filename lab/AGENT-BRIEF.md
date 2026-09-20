# Brief for the evaluation agent: from the finished lab run to a paper-grade report

The lab has already produced **one complete run with a benchmark and a written
conclusion** (`results/FINAL.md`). That run answered "does this work at all?".
It is **not** enough for a paper.

Your job: turn it into evidence a reviewer will accept, and write the final
report into `Cortex/lab/reports/`.

Read this whole brief before touching anything.

---

## 0. Where the lab is now (read these first)

| Read | What it tells you |
|---|---|
| `lab/results/FINAL.md` | the finished run's conclusions and numbers |
| `lab/results/round-*-check.md`, `rounds-06-10.md` | round-by-round evidence |
| `lab/README.md` | the lab design (**its "ten rounds" table is stale — see §1.7**) |
| `lab/bin/autopilot` | the headless driver: sessions, corrections, `/harvest`, `/evolve`, `/prune` |
| `lab/bench/bench.py` | the benchmark: `prepare`, `run`, `report`; arms differ only by harness |
| `lab/bin/lab`, `lab/bin/scenarios.py` | session helper, oracle, 41 scenarios (`LAB_REPO`/`LAB_STATE` aware) |
| `Cortex/README.md`, `docs/THEORY.md` | what Cortex does and why |
| `Cortex/paper/concept-audit.md` | what is genuinely new; your results must support §5 there |
| `Cortex/paper/plan.md` | the paper this report feeds |

### What the existing run (call it **D0**) produced

- 26 sessions over 10 rounds, Haiku 4.5, driven by `autopilot` (so it is already reproducible, not hand-typed).
- 27 harvested tasks (one quarantined), 17 lessons, **17 `/evolve` cycles**.
- **3 items kept**, all costing 0 always-on characters:
  - `use-billing-helpers` — rule on `shop/billing/**` (family B);
  - `check-changelog-on-shop-edits` — gated skill on `shop/**` (family A);
  - `complete-exporter-setup` — gated skill on `shop/plugins/**` (family C).
- **7 items buried**, including four attempts at the clock rule (family E), which **never found a form that survived**.
- Benchmark: 15 holdout tasks (3 per family), k=3, arms `none` and `evolved`:
  **holdout 36% → 76%**; A +67, B +89, C +44, D 0 (control, 100% both), E 0 (nothing was learned).
- Cost: 1,230 rollouts, **$155**. Measured unit cost ≈ **$0.105–0.11 per rollout**.
- Parallelism landed mid-run: 12 workers, a 138-rollout sweep in ~11 minutes.
- **39 Cortex defects were found and fixed during the run**, and the test suite grew from 357 to 487 tests.

### The three most interesting things D0 found

1. **E failed.** Four different forms of the clock rule were killed, each time
   because it helped its own family and broke something else. An honest
   negative result, and the protected-set gate is what caught it.
2. **The changelog skill was invoked in only 7 of 123 rollouts, yet its family
   gained +67 points.** Its *description* appears to be doing the work its body
   was written for. That is a genuinely novel observation and it must be
   **tested**, not just reported (H12 below).
3. **Rules always load, skills must be chosen.** The billing rule was used in
   52 of 52 rollouts where it was present; the exporter skill in 20 of 27; the
   changelog skill in 7 of 123.

---

## 1. Why D0 is not yet a paper, and what you must add

| # | Gap | What to do |
|---|---|---|
| 1.1 | **n = 1.** One run cannot separate "Cortex works" from "this run went well" | **3 (min) to 5** replicate runs on a frozen Cortex |
| 1.2 | **Cortex changed 39 times during D0.** The system under test moved | **freeze** Cortex, and rerun everything that produces the paper's primary numbers on the frozen version. D0 becomes the *development run*, reported separately |
| 1.3 | **No control for code learning.** Corrections fell over rounds, but every correct fix also adds examples to the code | **1–2 control runs**: same sessions, `/harvest`, **never `/evolve`** |
| 1.4 | **Holdout too small** (3 tasks per family, k=3) | **6 per family (30 tasks)**, k=5, so per-family numbers mean something |
| 1.5 | **No ablations.** "evolved vs none" cannot say *which part* helped | arms: `kitchen`, `ideal`, `accept-all`, `flat`, `desc-only`, `swapped` (§4.4) |
| 1.6 | **The gates were never tested against known answers** | **placebo / harmful / positive** candidates through the real pipeline (§4.5) |
| 1.7 | **Statistics are rollout-level Wilson intervals**, which ignore that repeats of one task are correlated | task-clustered bootstrap + permutation test + mixed model (§5) |
| 1.8 | **No A/A check.** Nothing shows the pipeline reports zero when there is nothing to find | the `none2` arm (§4.4) |
| 1.9 | **`/prune` decided "nothing to test"**, so H10 is untested | the prune experiment with planted items (§4.6) |
| 1.10 | **No pre-registration** | write one before the new runs (§3.6) |
| 1.11 | **`lab/README.md`'s rounds table contradicts the code.** The code groups families (R1=B, R2=A, R3=C, R4=E, R5=D, …), the README interleaves them | fix the README to match `scenarios.py: ROUNDS` |
| 1.12 | **One model.** Every number is conditional on Haiku 4.5 | the model-change study (§4.8) |
| 1.13 | **One repository, built by us.** The hardest attack on the whole paper | a second, real repository with tasks mined from its history (§4.9) |
| 1.14 | **No artifact package.** A reviewer who cannot re-run anything discounts everything | §7 |

---

## 2. Hypotheses to test

Report each as **SUPPORTED**, **NOT SUPPORTED** or **INCONCLUSIVE**, with its
number, interval, and the pre-registered margin where one applies.

| ID | Hypothesis | Evidence |
|---|---|---|
| **H0** | Without a harness, the agent breaks rules A/B/C/E often, and passes D | `none` arm |
| **H1** | **Primary.** On holdout tasks, `evolved` beats `none` on families A+B+C+E pooled | benchmark |
| **H2** | **Primary.** Family D is not harmed (margin −10 points), and no spurious item is kept | benchmark D; kept items |
| **H3** | Each kept item lands in a defensible tier, and fires in its area rather than everywhere | kept items, firing data |
| **H4** | Corrections fall once an item is live, **beyond** the control runs | evaluation vs control runs |
| **H5** | Gates are calibrated: placebos rarely kept, harmful killed, positives kept | gate calibration |
| **H6** | Gates add value: `accept-all` is not better than `evolved` | ablation |
| **H7** | Tiers add value: `flat` costs more always-on context without gaining pass rate | ablation |
| **H8** | Efficiency: `evolved` approaches `kitchen` and `ideal` at far lower always-on cost | ablation |
| **H9** | Reproducible: independent runs learn the same families, in similar forms | replicate runs |
| **H10** | `/prune` deletes planted useless items that fired, keeps needed ones, and **never** deletes one that never fired | prune experiment |
| **H11** | The **form** matters: the right skill/rule choice beats the swapped one | `ideal` vs `swapped` |
| **H12** | **The description hypothesis.** A skill's *description* alone carries much of its effect | `desc-only` arm |
| **H13** | D0 replicates: what the development run found holds on the frozen version | D0 vs R1…Rn |
| **H14** | **Model change:** after an upgrade, re-measurement changes which items earn their place, and the gain from the same harness differs | model-change study (§4.8) |
| **H15** | **External validity:** the loop also helps on a repository nobody in this project built, with tasks mined from its own history | second repository (§4.9) |

**Honesty rules.** You are testing the thesis, not selling it. Fix the analysis
before you see the data; log every deviation in `DEVIATIONS.md`; report every
run, including aborted ones; never re-tune a scenario, threshold or test to
make a hypothesis pass. E failing in D0 is a *result*, and if it fails again,
that is the finding.

---

## 3. Guardrails

### 3.1 Do not disturb D0
`/home/samuele/Progetti didattici/cortex-lab` and `lab/state/state.json` are the
finished development run, and they are evidence. **Read-only.** Never run
`lab build --force`, `autopilot`, `bench` or any `cortex` write command against
them without `LAB_REPO`/`LAB_STATE`/`BENCH_OUT` pointing elsewhere. Wrap the
tools so they refuse to run unless those are set. Take a full backup copy of
`cortex-lab` and `lab/state/state.json` before anything else.

### 3.2 Freeze Cortex, in a separate checkout
`~/.local/bin/cortex` symlinks into the live working copy, so changing Cortex
changes D0's tooling and every future run.
1. Make any needed change first (§4.1), with tests (`test/run-tests.sh` green).
2. `git tag v1.0-eval` in `Cortex/`.
3. `git worktree add ../cortex-eval-v1.0 v1.0-eval`.
4. Every run, benchmark, gate and prune process uses that copy's `bin/` first
   on `PATH`. Assert it (`command -v cortex`) and record it in the manifest.
5. If you find a Cortex defect mid-evaluation: stop, document, fix, tag
   `v1.1-eval`, and **restart the affected runs from scratch**. Never pool runs
   from different tags in a primary result.

### 3.3 One isolated copy per run
`cortex-lab-R1…Rn`, `cortex-lab-C1…`, `cortex-lab-GATE`, `cortex-lab-PRUNE`.
Each with its own `LAB_STATE`, its own `BENCH_OUT`, and **its own
`environment.sandbox_root`**. Everything else in `config.yaml` copied from D0
(model pinned to `claude-haiku-4-5-20251001`, `max_runs_per_cycle: 200`,
parallel settings, `DISABLE_AUTOUPDATER`).

### 3.4 Pipeline only inside a run
Nothing hand-edited: tasks, lessons, skills, rules, `CLAUDE.md` and the journal
come only from `/harvest`, `/evolve`, `/prune` and `cortex`. The autopilot's
rule stands: when something misbehaves, log a FINDING and continue, or stop —
never repair by hand. The gate and prune testbeds (§4.5, §4.6) are separate
copies made after a run ends; planting items there is the experiment.

### 3.5 Model, permissions, environment
- Haiku 4.5 everywhere (`claude-haiku-4-5-20251001`). The optional model-change
  study (§4.8) is the only exception.
- Sessions: the same permission mode D0 used (the autopilot's own mode), so the
  runs stay comparable. Rollouts: `acceptEdits`, never `bypassPermissions`.
- Record the user-level skills visible in rollouts (from `init` events), as D0
  did, and report it as a limitation. Never modify `~/.claude`.

### 3.6 Pre-register before the new runs
`reports/PREREGISTRATION.md`, committed **before** the first replicate rollout:
hypotheses, primary endpoints, margins for H6–H8 and H11–H12, the exact tests,
the numbers in §4, the placebo screen-task rule, the tier rubric, and the
holdout-writing rule (§4.2). Record its commit hash.

### 3.7 Budget
Measured from D0: **≈ $0.105 per rollout**, ≈ $130 per full run including
sessions, ≈ $25 per 246-rollout benchmark.
- **The default is the MIDDLE plan** (§4.10): 4 evaluation runs, 1 control,
  k=5 for the primary arms and k=3 for the ablations, 20 placebos, the full
  prune experiment. With the second repository (§4.9) and the model-change
  study (§4.8), the whole programme is **≈$1,300–1,450** and **≈70 h**.
- **`BUDGET_CAP_USD = 1500`** — the user may change this line.
- At Checkpoint A, project the total from measured costs and **stop and ask the
  user** if it exceeds the cap.

### 3.8 Everything regenerable
Every number in the report comes from scripts in `reports/analysis/` reading
`reports/data/`. One command rebuilds all tables and figures. No hand-typed numbers.

---

## 4. The work, step by step

### 4.1 Phase 1 — preparation (no evaluation rollouts yet)

1. **Back up** D0 (`cortex-lab`, `lab/state/`, `lab/results/`, `lab/bench/`).
2. **Fix `lab/README.md`'s rounds table** to match `ROUNDS` in `scenarios.py`.
3. **Extend the tooling** (all with tests, before the freeze):
   - `autopilot`: a `--no-evolve` mode for control runs; `LAB_REPO`-safe; a
     per-call turn cap (≈40) and timeout (≈15 min), recorded when hit.
   - `bench.py`: arbitrary named arms defined by a harness directory
     (`none`, `evolved`, `none2`, `kitchen`, `ideal`, `accept-all`, `flat`,
     `desc-only`, `swapped`), plus per-rollout logging of `turns`, `tool_calls`
     and `read_contributing` (did the rollout Read `CONTRIBUTING.md`?).
   - `bin/harness.py observe` in Cortex: add `turns`, `tool_calls`,
     `read_contributing` so sweeps record them too.
   - A results exporter that writes `reports/data/*.jsonl` from D0's existing
     runs, sessions and journal, so D0 is analysed by the same scripts.
4. **Write the 15 new holdout scenarios** (3 per family → 6 per family total).
   - Derive them **only** from `CONTRIBUTING.md` and the family definition,
     never from the text of any evolved item. State this rule in the
     pre-registration. D0's items are already known, so this discipline is what
     keeps the holdout honest: say so openly in the report's threats section.
   - New ids continue the existing scheme (`HA4…HA6`, `HB4…`, …). **Do not add
     them to `ROUNDS`**, or they would be run as training sessions.
   - Each needs: teammate commit, prompt, reference fix (`solve`) and, for
     A/B/C/E, a rule-breaking fix (`naive`).
   - They must touch code that no training fix touches, so they still fail on
     each run's final code.
   - `lab validate` must pass for all 56.
   - Validity check only: replace a scenario if the test does not fail, the
     reference fix does not pass, or the environment errors. **Never** replace
     one because the agent already follows the rule. Log every replacement.
5. **Write the fixed harnesses** (§4.4) and the gate candidates (§4.5) and
   prune plants (§4.6). Commit them.
6. **Write the pre-registration** (§3.6). Commit. Record the hash.
7. **Freeze Cortex** (§3.2).

### 4.2 Phase 2 — pilot

Run **round 1 only** with the frozen Cortex on a scratch copy, through
`autopilot`, and confirm: harvest validity (`lab audit`), lesson quality,
`/evolve` behaviour, the new logging fields, and measured cost per session and
per rollout. Fix the tooling if needed (re-tag if Cortex changed).

**Checkpoint A** → `reports/CHECKPOINT-A.md`: what was built, pilot results,
measured unit costs, projected total vs `BUDGET_CAP_USD`. Stop and ask if over.

### 4.3 Phase 3 — the runs

| Run | How | Count |
|---|---|---|
| **R1…Rn** evaluation | `autopilot round 1…10`, frozen Cortex, fresh repo each | **3** min, **5** target |
| **C1…Cm** control | the same sessions with `--no-evolve` | **1** min, **2** target |

Run them one at a time or two at a time (each has its own sandbox root; sweeps
already use 12 workers internally). After each round, append the round's facts
to `reports/RUNLOG.md`. Log every autopilot FINDING. If a sweep's invalid rate
exceeds 10%, investigate before continuing.

### 4.4 Phase 4 — the benchmark

For **every** run (R1…Rn, C1, and D0 re-measured on the expanded holdout), with
`bench.py`, on that run's own final code, `.evolve/` excluded from sandboxes,
arms interleaved, oracle judge.

| Arm | Harness | Which runs | Holdout k | Train k |
|---|---|---|---|---|
| `none` | nothing but `cortex init`'s minimal `CLAUDE.md` | all | **5** | 3 |
| `evolved` | what that run kept | all | **5** | 3 |
| `none2` | **identical to `none`** (A/A check: the true difference is 0) | R1 | 5 | — |
| `kitchen` | `none` + all of `CONTRIBUTING.md` in `CLAUDE.md` | R1 | 5 | — |
| `ideal` | hand-written: A always-on skill, B rule on `shop/billing/**`, C gated skill on `shop/plugins/**`, E always-on skill | R1 | 5 | — |
| `accept-all` | `evolved` + every buried candidate of that run (D0 has 7; R1 likely similar) | R1 | 5 | — |
| `flat` | `evolved`'s texts with scope removed: gated skills lose `paths`, path-scoped rules become path-less rules | R1 | 5 | — |
| `desc-only` | `evolved`'s skills keep their `description` and `paths`, but the body is replaced by neutral filler of similar length; rules unchanged | R1 | 5 | — |
| `swapped` | `ideal`'s items in the other form (A and E as path-less rules; B as a gated skill; C as a rule on `shop/plugins/**`) | R1, **target plan only** — add it if `desc-only` shows an effect | 3 | — |

`desc-only` and `swapped` exist because of D0's two most interesting findings
(H12, H11). Before benchmarking a run, verify on its final code that each
holdout test fails and its reference fix passes; exclude any that do not,
identically in every arm, and report them.

### 4.5 Phase 5 — gate calibration (H5)

**Testbed:** a copy of C1's final repository (tasks harvested, no items live).
Reset it to the same commit before every candidate, and **never `cortex promote`** there.

| Type | Min | Target | What |
|---|---|---|---|
| Placebo, topic | 5 | 10 | plausible, irrelevant advice, topic description |
| Placebo, moment | 5 | 10 | irrelevant body, but a description that will be invoked ("Use before reporting that a change is complete") |
| Harmful | 3 | 5 | contradicts a house rule ("float is fine in billing"; "skip `make lint`"; "update the test to match the code") |
| Positive | 4 | 4 | the four `ideal` items, one at a time |

Placebos: 300–1,500 characters, and they must not mention tests, lint,
CONTRIBUTING, changelog, docs, money, time or exporters.

**Procedure per candidate** (`/evolve`'s rules, applied with the CLI so it is deterministic):
1. screen: `cortex sweep --candidate <c> --tasks "<screen tasks>" --phase screen --k 2`;
2. stop if `gain ≤ 0` or it never fired → KILL (screen);
3. otherwise confirm at k=3 on all valid tasks; run the recheck when asked;
4. record the verdict and every field of `cortex score`.

Screen tasks: a family's currently failing tasks for positives and harmful
candidates; for placebos, a fixed rule written in the pre-registration.

Report: false-KEEP rate per placebo type and pooled, with Clopper–Pearson
intervals (0/20 → ≈14% one-sided upper bound); KILL rate for harmful; KEEP rate
for positives; fire rates; and **Fisher's exact test** for positives vs placebos.

### 4.6 Phase 6 — the prune experiment (H10)

**Testbed:** a copy of R1's final repository. Raise `prune.max_items` to cover
every live item.

| Planted | Count | Expected |
|---|---|---|
| placebo always-on skills with a *moment* description | 2 | fire, cost nothing → **ACCEPT** (deleted) |
| gated skill whose `paths` match no file any task touches | 1 | **skipped** by the plan; never deleted |
| always-on skill whose description matches no moment here | 1 | never fires → **UNMEASURED**; not deleted |
| R1's evolved items | as kept | **REJECT** (kept) |

Run `/prune` through `autopilot prune`. Record the plan, its estimate, which
items Haiku chose, every verdict, and whether it matches the expectation. Add a
second pass (`cortex prune plan --items …`) for any planted item it skipped.

**Target:** also plant B as an always-on skill instead of a rule, and see
whether `/prune` proposes and measures the narrowing.

### 4.7 Checkpoint B (after §4.8 and §4.9, when all data is in)
`reports/CHECKPOINT-B.md`: data complete, what is missing and why, spend so far.
Phases run in this order: 3 (runs) → 4 (benchmark) → 5 (gates) → 6 (prune) →
7 (model change) → 8 (second repository) → **Checkpoint B** → analysis.

### 4.8 Phase 7 — the model-change study (required)

A reviewer will ask whether anything here is specific to Haiku. Answer it.

1. **Cost pilot:** 10 rollouts with the stronger model (Sonnet) to measure its
   per-rollout cost and time. Record it before committing to the rest.
2. **Benchmark:** the holdout, arms `none` and `evolved` (R1's harness), **k=3**,
   with the stronger model. Same tasks, same oracle, same sandboxes.
   - Report the gain and compare it with Haiku's.
   - A smaller gain is the expected result (the stronger model may already
     follow some house rules), and it is a finding, not a failure.
3. **`/prune` under the new model:** on a fresh copy of R1 with the stronger
   model pinned, run `/prune`. Cortex detects the model change and tests
   **every** item, largest always-on cost first.
   - Record each verdict: does an item the weaker model needed become
     removable for the stronger one?
   - This is the only direct test of Cortex's "re-measure after a model
     upgrade" mechanism (H14).

Add **H14** to §2: *after a model upgrade, re-measurement changes which items
earn their place.* Verdict from step 3, supported by step 2's gain difference.

### 4.9 Phase 8 — a second, real repository (required)

This answers the hardest question in the paper: *"you built the repository, the
house rules and the tasks, so of course it works."* One external repository is
worth more than another five runs of the lab.

1. **Choose a repository** (record the selection rule in the pre-registration
   before looking at candidates):
   - Python, permissively licensed, self-contained tests that run in under
     about two minutes, no network or credentials;
   - a real convention a newcomer breaks, visible in its CONTRIBUTING, linter
     configuration or review comments;
   - at least 200 commits of history;
   - **not** a repository used in common agent benchmarks, to limit
     contamination.
2. **Mine 8–12 tasks from its own history** (the Skill Issue and SWE-smith
   approach): find commits whose tests go from failing to passing, revert the
   implementation at a frozen base commit, keep the tests as the check, and
   write the user's prompt from the issue or commit message **without** naming
   the fix.
   - Validate each one exactly as the lab does: fails on the broken state,
     passes with the reference fix, and still passes with the fix minus its own
     test edits.
   - Split: **6–8 train**, **4 holdout**, fixed before any run.
3. **Corrections:** the lab's scripted corrections do not exist here. Use the
   repository's own CI output (test failure, linter message) as the correction
   text, verbatim. Record exactly how each correction was produced.
4. **Run the loop once** with `autopilot` on the frozen Cortex: sessions on the
   train tasks, `/harvest` after each, `/evolve` when a theme recurs.
5. **Benchmark** `none` vs `evolved` on the 4 holdout tasks, k=5, judged by the
   repository's own tests plus its linter.
6. **Report it as its own section**, with its own threats: fewer tasks, a
   single run, real-world noise, and possible contamination. Do **not** pool it
   with the lab's numbers.

Expected: 8–12 h, ≈$150–250. If task mining yields fewer than 6 valid train
tasks, stop, report what happened, and say the external check was not possible.
That is itself worth reporting.

### 4.10 Numbers and budget

Unit costs measured in D0: $0.105/rollout; ≈$130 per run (sweeps + sessions);
sessions ≈$0.40 each. **MIDDLE is the default.**

| Block | Minimum | **MIDDLE (default)** | Target |
|---|---|---|---|
| New holdout scenarios | 15 | **15** | 15 |
| Evaluation runs | 3 × ≈$130 | **4 × ≈$130 = $520** | 5 × ≈$130 |
| Control runs (no sweeps) | 1 × ≈$15 | **1 × ≈$15** | 2 × ≈$15 |
| Benchmark `none`+`evolved` (30 holdout + 26 train) | 4 runs, k=3 ≈$140 | **5 runs, k=5 ≈$235** | 6 runs, k=5 ≈$282 |
| Extra arms on R1 | 7 arms, k=3 ≈$66 | **7 arms, k=3 ≈$66** | 8 arms, k=5 ≈$126 |
| Gate calibration | 17 candidates ≈$110 | **29 candidates ≈$230** | 29 candidates ≈$230 |
| Prune experiment | planted only ≈$57 | **full ≈$95** | full + narrowing ≈$95 |
| **Lab subtotal** | ≈$800 | **≈$1,050** | ≈$1,400 |
| Model change (§4.8) | — | **≈$120** | ≈$150 |
| Second repository (§4.9) | — | **≈$200** | ≈$250 |
| **Total** | **≈$800** | **≈$1,370** | **≈$1,800** |
| Wall time (12 workers) | ≈2–3 days | **≈3–4 days** | ≈4–6 days |

Cut in this order if needed: prune to planted items only; holdout k 5→3;
evaluation runs 4→3; placebos 20→10 (keep both types).
**Never cut:** the control run, the holdout expansion, `none2`, the placebos,
the primary `none`/`evolved` arms, or the second repository (§4.9) — it is the
single most valuable block in the programme.

---

## 5. Analysis

**Primary endpoints** (evaluation runs only; D0 reported beside them, never pooled):
- **P1 (H1):** holdout `evolved − none`, families A+B+C+E pooled. Paired by
  task within run. CI from a **two-way (crossed) bootstrap**: resample runs and
  tasks independently, 10,000 times, 95% percentile. Supported if the lower
  bound is above 0.
- **P2 (H2):** family D holdout, same method; supported if the lower bound is
  above −10 points, and no spurious item was kept.

**Also required:**
- a **permutation test** for P1 (shuffle arm labels within task, 10,000 times)
  as an assumption-free p-value;
- a **mixed model** as robustness: `pass ~ arm * family + (1|task) + (1|run)`,
  crossed random effects (R `lme4`, else `statsmodels`; say which, and note
  that 3–5 runs estimate the run variance poorly);
- **Wilson intervals** only as description, labelled as ignoring clustering;
- **Holm** correction across the four rule families;
- **Clopper–Pearson** for candidate and run proportions; **Fisher's exact** for
  positives vs placebos;
- **H4:** compare corrections per session after an item went live against the
  **same scenarios** in the control runs, by permutation over runs; present the
  full curve too, and keep D0's caveat that scenarios differ between rounds;
- **H3:** the pre-registered tier rubric, plus each item's fire rate on its own
  family versus others;
- **H11, H12:** differences with CIs against pre-registered margins;
- **A/A (`none2`):** report the observed difference and its CI. If it excludes
  zero, treat every other result as suspect until explained;
- **invalid rollouts:** excluded, counted, listed by reason;
- **efficiency:** always-on characters, tokens, cost, wall time and turns per
  rollout, per arm (D0 saw +23% cost, +14% wall clock for `evolved`);
- **failure taxonomy:** the oracle's verdicts among failures, per arm,
  including D0's observation that `none` tampered with tests more often;
- **noise:** per-task pass-rate spread in `none`, and the D-family difference
  distribution;
- **H14 (model change):** the same harness's gain under each model, side by
  side with CIs, plus `/prune`'s per-item verdicts under the stronger model.
  Analyse the two models separately; never pool them;
- **H15 (second repository):** its own paired analysis over its 4 holdout
  tasks at k=5, with a bootstrap CI. With so few tasks the interval will be
  wide: report it as corroboration, not as a second primary result.

---

## 6. The report: `Cortex/lab/reports/`

```
reports/
  REPORT.md            the comprehensive report (below)
  PREREGISTRATION.md   committed before the replicate runs
  DEVIATIONS.md        every departure, with reasons
  RUNLOG.md            chronological log: runs, rounds, FINDINGs, costs
  CHECKPOINT-A.md, CHECKPOINT-B.md
  data/                rollouts.jsonl, sessions.jsonl, cycles.jsonl, runs.jsonl,
                       gates.jsonl, prune.jsonl, manifest.json (tags, hashes, models,
                       CLI, dates, environment, permissions)
  analysis/            scripts + requirements; one command rebuilds everything
  figures/             PNG (300 dpi) + SVG
  tables/              CSV + Markdown
  appendix/            every scenario, prompt and correction; every kept and buried item's
                       text; journals; the fixed harnesses; gate candidates; prune plants
```

### REPORT.md structure
1. **Summary**: thesis, hypothesis scorecard (H0–H15), headline figure.
2. **Setup**: lab, families, scenarios, runs, arms, k, versions, environment, pre-registration hash.
3. **Calibration (H0)**.
4. **What Cortex did**, per run: trace, kept, buried, unmeasured changes (CLAUDE.md edits), harvest quality, protocol FINDINGs.
5. **Main result (H1, H2)**: holdout and train, per family and pooled, every run shown, with the A/A check.
6. **Corrections (H4)**: evaluation vs control.
7. **Tiers, firing and form (H3, H11, H12)**: including the description finding.
8. **Ablations (H6–H8)**.
9. **Gates (H5)**.
10. **Pruning (H10)**.
11. **Reproducibility (H9, H13)**: runs against each other, and against D0.
12. **A stronger model (H14)**: the benchmark and what `/prune` decided under it.
13. **A repository we did not build (H15)**: its own section, with its own threats, never pooled with the lab.
14. **Why failures remain**; **noise and cost**.
15. **What the lab found in Cortex**: the defect catalogue (T16), as a contribution in its own right.
16. **Threats to validity**: one synthetic repo (answered in part by §13), one main model (answered in part by §12), lintable rules only, scripted corrections, the holdout written after D0's items were known, Cortex changing during D0, environment, multiple comparisons.
17. **Deviations**, and **how to reproduce**.

### Figures (PNG + SVG, matplotlib, readable in grayscale, n in every caption)

| # | Figure |
|---|---|
| F1 | Calibration: `none` pass rate per family, initial vs final code |
| F2 | **Headline:** pass rate by family × {none, evolved}, holdout, CIs, one dot per run |
| F3 | Forest plot: paired difference per family and pooled, train and holdout, with D0 marked separately |
| F4 | Per-task heatmap: holdout tasks × arms (and runs) |
| F5 | Corrections per session over the run, evaluation vs control, with "item live" markers |
| F6 | Items kept vs round, one line per run (D0 dashed) |
| F7 | Replicate matrix: runs × families → learned? (round, form) |
| F8 | Always-on characters vs holdout pass rate, one point per arm |
| F9 | Firing heatmap: items × task families (visible vs invoked) |
| F10 | Gate calibration: verdicts per candidate type + placebo `net_runs` histogram |
| F11 | Gain vs regression per `/evolve` cycle, coloured by verdict, all runs |
| F12 | Failure taxonomy: oracle verdicts among failures, per arm |
| F13 | Noise: per-task pass-rate spread in `none`; the D-family difference distribution; the A/A result |
| F14 | Cost: tokens, $, wall time, turns per rollout, per arm |
| F15 | The description test (H12): `evolved` vs `desc-only` vs `none`, per family |
| F16 | Model change (H14): the holdout gain under Haiku vs the stronger model, side by side |
| F17 | Second repository (H15): pass rate per arm on its holdout tasks, with CIs |

### Tables

| # | Table |
|---|---|
| T1 | The lab: families, rule, typical mistake, check, expected form, task counts |
| T2 | Scenario inventory, with exclusions per run |
| T3 | Hypothesis scorecard: test, estimate, CI, margin, verdict |
| T4 | Main results: family × arm × split, n tasks, n rollouts, rate, Wilson CI, paired difference, bootstrap CI, permutation p, Holm-adjusted p |
| T5 | Evolution trace per run: round, sessions, corrections, harvest, `/evolve` path, candidate, form, tier match, rollouts, cost |
| T6 | Kept and buried items across runs: name, family, form, `paths`, chars, verdict, gates failed, fire rates |
| T7 | Ablations: arm, always-on chars, pass rate (rule families, D), tokens and cost per rollout |
| T8 | Gate calibration: type, n, verdicts, rate + CI, fire rate, Fisher's p |
| T9 | Corrections: family × {evaluation, control}, before/after, difference with CI |
| T10 | Prune: item, planted role, verdict, expected, match, chosen by Haiku or added |
| T11 | Harvest quality: tasks, audit results, quarantined, lesson accuracy, cap hits |
| T12 | Protocol FINDINGs by type and count, per run |
| T13 | Invalid rollouts by reason, arm, run |
| T14 | Cost by phase and run |
| T15 | Model change (H14): family × {none, evolved} under the stronger model, and `/prune`'s verdict per item |
| T16 | **Defect catalogue:** every Cortex defect the lab found (D0's 39 plus anything new), one row each: class (task validity / scoring / isolation / attribution / tooling), symptom, how it was detected, why it would corrupt a measurement, the fix, the regression test, and which runs it affected. This is a contribution, so write it for an outside reader |
| T17 | Second repository (H15): repo, mined tasks, split, pass rates per arm, gain with CI |
| T18 | **Claims table:** every sentence the paper will assert → the figure or table that supports it → the exact number and interval. Flag any sentence without evidence and delete it |

---

## 7. The artifact package

A reviewer who cannot re-run anything will discount everything. Prepare a
package that a stranger can use, in `Cortex/lab/reports/` plus the repository root.

1. **A public repository** containing Cortex, the lab, the scenarios, the
   analysis scripts and the raw data. Add a `LICENSE` (MIT or Apache-2.0) and a
   `CITATION.cff`.
2. **A tag for the paper** (`v1.0-paper`) on the exact commit the numbers come
   from, and the evaluation tag (`v1.0-eval`) it used.
3. **`reports/REPRODUCE.md`**, written for someone who has never seen this
   project:
   - prerequisites (Claude Code version, model access, Python, RAM, cores);
   - how to rebuild the lab repository from `seed/`;
   - how to run **one round**, **one benchmark arm** and **the analysis**, each
     with its expected wall time and cost;
   - how to regenerate every figure and table from the shipped data, with no
     API access at all. This is the part most reviewers will actually try, so
     it must work offline;
   - what is **not** reproducible and why (model versions change, agents are
     stochastic), with the expected spread from your own noise data.
4. **Raw data, shipped:** `reports/data/*.jsonl` plus `manifest.json` (tags,
   commit hashes, model ids, CLI versions, dates, environment, permissions,
   costs). Strip anything personal: absolute home paths, user names, tokens.
5. **A Zenodo DOI** for the tagged release, cited in the paper.
6. **A one-page `reports/SUMMARY.md`** for people who will not read the report:
   the claim, the headline numbers with intervals, and the three limits.

## 8. Definition of done

- [ ] H0–H15 each have a verdict, a number with an interval, the pre-registered margin where one applies, and a pointer to a figure or table.
- [ ] Every figure (F1–F17) and table (T1–T18) exists and regenerates with one command from `reports/data/`.
- [ ] The claims table (T18) contains no sentence without evidence.
- [ ] The defect catalogue (T16) is written for an outside reader.
- [ ] `PREREGISTRATION.md` was committed before the first replicate rollout; `DEVIATIONS.md` lists every change.
- [ ] Every evaluation, control, gate, prune, model-change and second-repository process ran on the frozen Cortex tag; the manifest proves it.
- [ ] D0 is reported and analysed by the same scripts, clearly marked as the development run on an unfrozen version.
- [ ] The A/A arm's result is reported, whatever it shows.
- [ ] The second repository is reported in its own section, never pooled with the lab.
- [ ] D0's data and `results/FINAL.md` are untouched and still reproduce.
- [ ] The artifact package (§7) is complete, and the offline figure regeneration works on a clean machine.
- [ ] Spend is within `BUDGET_CAP_USD`, or the user approved going over.
- [ ] `REPORT.md` stands on its own for a reader who has never seen the lab.
