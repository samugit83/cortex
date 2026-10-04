# Reproducing this

Written for someone who has never seen this project.

There are three levels, and they cost very different things. **Level 1 needs no API
key, no network and no Cortex** — it rebuilds every number, table and figure in the
report from the shipped rows. It is the level most readers want, and it is the one
that has to work on a clean machine, so it is the one documented most carefully.

| | What it does | Needs | Time | Cost |
|---|---|---|---|---|
| **1 · the analysis** | rebuild every table and figure from `reports/data/` | Python 3.12 | ~2 min | **$0** |
| **2 · one arm of one benchmark** | re-measure one harness on the holdout | + Claude Code, model access | ~15 min | ~$20 |
| **3 · a whole run** | ten rounds, `/harvest`, `/evolve`, the gates, then its benchmark | + 12 CPUs, ~24 GB RAM | 2–4 h + 40 min | $46–145 + ~$60 |

The Level 2 and 3 figures are **measured** on this programme's own runs (Claude Code
2.1.278, `claude-haiku-4-5-20251001`, 12 CPUs), not estimated: one holdout arm is
150 rollouts at about $0.13 each; the four evaluation runs' rounds took 101–191
minutes and $46–145 each (R3, the dearest, killed four candidates), and each run's
456-rollout benchmark 37–41 minutes and $57–75. Under Sonnet a rollout cost $0.22.

---

## Level 1 — rebuild every number, offline

```bash
git clone https://github.com/samugit83/cortex.git && cd cortex
lab/reports/analysis/run.sh
```

That is the whole thing. It creates a virtual environment on first use (with `uv`
if present, otherwise `python -m venv`), installs the five packages in
`analysis/requirements.txt`, and writes:

```
lab/reports/tables/    T1…T19, each as Markdown AND CSV from one list of rows
lab/reports/figures/   F1…F19, each as 300-dpi PNG and SVG
lab/reports/data/scorecard.json    every hypothesis, its estimate, interval and verdict
```

**Prerequisites:** Python **3.12**, about 400 MB of disk for the environment, no
network after the first install. Nothing else. To rebuild one thing while
iterating: `lab/reports/analysis/run.sh --only T4,F2`.

**What you are checking.** Every number the report asserts comes from a script in
`analysis/` reading a `.jsonl` file in `data/`. There are no hand-typed numbers in
the report, and `T17` lists every claim beside the table or figure that carries it.
If a claim in the report is not in `T17`, that is a defect in the report.

**The paper's numbers.** Every number, table and chart in the paper is computed from
the same rows by four scripts beside the analysis. Run them in a clone of the release the
paper cites, `v1.0.3` or later (`gen_numbers.py` also reads the tag `v1.0-eval`), in this
order, with the environment `run.sh` made:

```bash
PY=lab/reports/analysis/.venv/bin/python
$PY lab/reports/analysis/gen_numbers.py          # paper/generated/numbers.tex: one macro per number
$PY lab/reports/analysis/gen_tables.py           # paper/generated/tab-*.tex
$PY lab/reports/analysis/gen_diagram_data.py     # paper/diagrams/data.js
$PY lab/reports/analysis/gen_results_data.py     # paper/diagrams/results.js
```

They write into `paper/`, which is not part of this repository: compare what they write
with the paper's LaTeX source. Each script checks what it computes against the other
sources that state the same number, and stops if they disagree.

### The data you are reading

| File | One row per |
|---|---|
| `rollouts.jsonl` | one rollout: run, source (`bench` or `sweep`), arm, task, pass, verdict, tokens, cost, turns, tool calls, whether it read `CONTRIBUTING.md`, which items were in context and which fired |
| `sessions.jsonl` | one lab session: corrections, verdicts, what it harvested |
| `cycles.jsonl` | one journal entry, with `is_cycle` saying which ones `cortex cycle` counted |
| `sweeps.jsonl` | one sweep: candidate, phase, rollouts, invalid, cost, wall time |
| `items.jsonl` | one item a run produced, kept or buried, with its full text |
| `runs.jsonl` | one run: its Cortex tag and commit, its model, whether a judge was on |
| `gates.jsonl`, `prune.jsonl`, `scope.jsonl`, `external.jsonl` | the four testbeds |
| `prune-model-change.jsonl` | `/prune`'s verdict on each item under the stronger model (H13) |
| `scope-replay-<run>.jsonl` | the judge's prediction beside each candidate's fate (H15, H16) |
| `prune-sweeps.jsonl` | one rollout of a `/prune` removal sweep, both passes (the verdicts above rest on these) |
| `external-training.json` | the second repository's training: its sessions with their verdicts and corrections, the tasks and lessons they left, and the `/evolve` cycles |
| `transcripts.jsonl` | one rollout, with what it read through git that its harness did not give it (flags only), from Claude Code's own record of each session; `transcripts-coverage.json` says how many were matched, and names the one sweep whose record an agent deleted |
| `spend.json` | the programme's measured spend per block — the only source of the cost totals |

Paths in the rows are scrubbed (`<workspace>/…`); nothing in the analysis needs them —
each run's scenario exclusions travel in its own `runs.jsonl` row. To point the analysis
at another copy of the rows, set `CORTEX_REPORT_DATA=/path/to/data`.

Every row carries `run`, so a reader can separate the development run from the
replicates without knowing anything about the directory layout.

The loop's verdicts are recomputed, not read from the journals: `analysis/rescore.py`
applies `score.sh`'s rules at `v1.0-eval` to the recorded rollouts of every sweep of the
evaluation runs, and agrees with `score.sh` itself on all of them. The three extracts above
are made by `analysis/extract_prune.py`, `analysis/extract_external.py` and
`analysis/extract_transcripts.py` from data that does not ship (the raw run directories and
the session records).

---

## Level 2 — re-measure one arm

Needs Claude Code (`claude --version` ≥ 2.1.276) and access to
`claude-haiku-4-5-20251001`.

```bash
# 1. build the lab repository from its seed (no API calls)
LAB_REPO=/tmp/lab LAB_STATE=/tmp/lab-state.json lab/bin/lab build

# 2. prove every scenario still discriminates (no API calls, ~10 min)
LAB_REPO=/tmp/lab LAB_STATE=/tmp/lab-state.json lab/bin/lab validate

# 3. one benchmark arm on the holdout
export LAB_REPO=/tmp/lab LAB_STATE=/tmp/lab-state.json
export BENCH_OUT=/tmp/bench BENCH_SANDBOX=/tmp/bench-sandbox
python3 lab/bench/bench.py prepare
python3 lab/bench/bench.py arms --arms none,evolved
python3 lab/bench/bench.py run --k 1 --arms none --only HA1,HB1,HC1,HD1,HE1
python3 lab/bench/bench.py report
```

**Expected:** ten rollouts, about six minutes at twelve workers, about $1. The
`none` arm should pass family D and fail most of A, B, C. That is `H0`, and it is
the cheapest thing in this repository that tells you the lab is real.

---

## Level 3 — a whole run

```bash
git worktree add ../cortex-eval-v1.0 v1.0-eval     # the frozen system under test
ln -sfn "$PWD/../cortex-eval-v1.0/bin/cortex" ~/.local/bin/cortex
lab/bin/run-eval new R9
lab/bin/run-eval rounds R9 --from 1 --to 10
lab/bin/run-eval bench R9 --k 5
lab/bin/run-eval export R9
```

`run-eval` refuses to start unless `cortex` resolves inside the frozen worktree on
**all three** paths a call can take — the run's `PATH`, a login shell's `PATH`, and
the bare `PATH`. That check exists because prepending to the run's `PATH` alone is
not enough: `/harvest` and `/evolve` reach `cortex` through a login shell.

**Machine:** the sweeps size themselves to the host. On 12 CPUs and 24 GB free they
use 12 workers; a 138-rollout sweep takes about 11 minutes. Do not run two runs at
once — Cortex invalidates a rollout that timed out while the machine was
oversubscribed, and you will get a pile of `INVALID` rows rather than speed.

To run the whole programme unattended: `lab/bin/programme`. It is restartable — each
step writes a marker when it finishes — and it **stops rather than guesses**: before a
paid step it checks the measured spend against `BUDGET_CAP_USD` and makes one live
call with that step's model; during a step, rollouts that cannot run (a usage limit,
an outage) stop it unmarked. `lab/bin/usage-guard spend` prints what has been spent.

**The second repository** (`hynek/structlog`) needs network once, to build its
virtualenvs:

```bash
python3 lab/external/run-external.py setup     # clone, venvs, the pinned ruffs, cortex init; self-tests
python3 lab/external/run-external.py train     # eight sessions, oldest commit first (~30 min)
python3 lab/external/run-external.py bench --k 5
python3 lab/external/run-external.py export
```

Its lint stage runs the ruff version the project pinned at each commit
(`.pre-commit-config.yaml`), not the newest: today's ruff fails structlog's own
upstream commits.

---

## What is **not** reproducible, and why

**Nothing above will give you the same numbers.** It should give you the same
*conclusions*, and here is the expected spread, measured from this programme's own
data rather than asserted:

| Source of variation | What it does |
|---|---|
| **The agent is stochastic.** | The same task, the same harness, five times, does not give five identical answers. `F13a` is the per-task pass-rate spread in the `none` arm: read it before concluding that a difference is real. |
| **Model versions move.** | Every number here is conditional on `claude-haiku-4-5-20251001`. `F16` shows what changed under a stronger model, which is the honest way to say how far that conditioning goes. |
| **`/evolve` proposes, and proposals differ.** | Two runs of the same ten rounds do not propose the same candidate text, and sometimes not the same *form*. `F7` is the replicate matrix: which families each run learned, and in which form. |
| **The judge is a service.** | If `JEV_ENABLED=1`, the proposal layer consults a model on someone else's server reached through a moving alias. Every primary number here was produced with it **off**, and `T19` proves which runs had it on. |
| **Cost and wall time depend on the machine.** | Twelve workers on twelve CPUs. Fewer CPUs is not slower per rollout; it is fewer rollouts at once. |

The A/A arm (`none2`) is the calibration for all of this: it is the `none` harness
built by the same code, measured as if it were a treatment. Whatever difference it
shows is the floor under every other difference in the report. If it excludes zero,
treat everything else as suspect until that is explained — and the report says so in
its own voice, not only here.

---

## Verifying the development run is untouched

D0 is evidence. The tools refuse to write to it, and the claim is checkable:

```bash
lab/bin/verify-d0
# 1393 file(s) checked against .../backup-D0: UNCHANGED
```

## Re-running the judge's gate

```bash
python3 jev/validate.py --corpus jev/corpus     # needs a key
python3 jev/validate.py --dry-run               # the free baseline, no key, no network
```

`jev/RESULTS.md` records the verdict and the model it was measured against. Before
quoting it, note that the pass threshold was lowered from 90 % to 85 % after the first
measurement returned 89.4 % (`PASS_AGREEMENT` in `jev/validate.py`).

## The commits this report cites

The published history holds the commits up to the freeze, then the release commits
with the finished lab, report and data:

| Commit | What it is |
|---|---|
| `8014a11` | the instrument, committed before any evaluation rollout |
| `23bd5e4` | tag `v1.0-eval`: the frozen Cortex every run used (`runs.jsonl`, `manifest.json`) |
| tag `v1.0-paper` | the finished lab, report and data (release 1.0.0) |
| tag `v1.0.1` | the same, with the scripts and data that regenerate every number in the paper; `CHANGELOG.md` lists what changed |
| tag `v1.0.2` | the report numbers its hypotheses H0 to H16 and its tables T1 to T19 |
| tag `v1.0.3` | the release the paper cites: the scorecard gives H6 and H16 as inconclusive, as the paper does |

The `analysis_commit` in `manifest.json` belongs to the working history between the freeze
and `v1.0-paper`, which is not published.
