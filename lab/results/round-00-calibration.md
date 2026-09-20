# Round 0 — calibration, before the lab started

Done by the experimenter on 2026-09-19, before the user's first session. The purpose was to
make sure the lab can prove something: if Haiku already follows a house rule with no help, no
skill can show a gain, and the experiment would measure nothing.

## Cortex fixes made while designing the lab

The lab design surfaced five real problems in Cortex. All are fixed, with tests (suite:
327 passed, 0 failed), and documented in the README and TROUBLESHOOTING.

| # | Problem | Consequence without the fix | Fix |
|---|---|---|---|
| 1 | `/harvest` built `fix.patch` with `git diff`, which drops **new files** | every task whose fix creates a file (all exporter tasks) quarantined by preflight | `cortex harness fixpatch --base <sha>`: temp index, new files in, `.evolve/`, `.claude/` and harness files out |
| 2 | sweeps checked out `.evolve/` at `base_sha` | later tasks' rollouts could read earlier fixes, lessons and buried skills, in **both** arms, hiding the gain | the sandbox is a sparse checkout without `.evolve/`; preflight checks the same way |
| 3 | a check that runs a test the fix itself added passes preflight, then fails every rollout | dead tasks that cost money forever | preflight's third state: the fix's code **without** its test edits must pass; the harvest rules explain how to keep such a test in the task folder |
| 4 | gate 3 killed on **one** lost run on any task that went 3/3 in base | with ~15 tasks, most good candidates killed by chance (≈65% at p=0.95) | **exposure**: tasks where the change never entered the context are left out of the gates; **RECHECK**: a KILL resting only on per-task drops is re-measured, and must replicate |
| 5 | `/evolve` had no rule for the screen set without a baseline (first cycle) | the first cycle is ambiguous for the model driving it | lessons carry `task NN`; the screen runs the theme's tasks; `baseline.json` gains `live` / `failing` |

## Pilot: Haiku 4.5, no skills, 22 rollouts

Headless, one scenario at a time, judged by the lab oracle.

| Scenario | Runs | Result | Reading |
|---|---|---|---|
| A01 list sort | 2 | 2× forgot the CHANGELOG | discriminates |
| B01 tax, first design | 2 | 2× used `Money.percent()`, which was right there | **too easy**: the helper sat in the module every fix imports, with the test's own example in its docstring. Redesigned: helpers moved to `billing/rates.py` |
| B01 tax, redesigned | 2 | 2× `Decimal` | discriminates |
| B02 discount | 2 | 2× `Decimal` | discriminates |
| B03 FX, first design | 2 | 2× extended the existing integer code | a legitimate exact fix: **no trap**. Redesigned so the rate's decimals are ignored |
| B03 FX, redesigned | 2 | 1× `float()`, 1× test still failing | discriminates |
| B04 shipping, redesigned (weight as text) | 2 | 1× `Decimal`, 1× `float()` | discriminates |
| C01 XML export | 2 | 1× no docs row / golden, 1× complete (found CONTRIBUTING.md) | discriminates, variance band |
| C02 Markdown export | 2 | 2× no docs row | discriminates |
| D01 slugify | 2 | 2× solved | control behaves |
| E01 due date | 2 | 2× `date.today()` | discriminates |

Cost per rollout: $0.055–0.25, about $0.09 on average.

The environment, as it is: every rollout lists the user's global skills (`rushes`, bundled
`verify`, `run`, …, and `anthropic-skills:*`). One E01 run invoked `run`. Both arms see the
same set, so the comparison is unaffected.

## Rehearsal: one full session, headless Haiku

B01 on a scratch copy of the lab, with Cortex installed exactly as in round 0:

1. first fix used `Decimal`; `lab verify` → "✘ make lint: float arithmetic on money";
2. correction pasted → fix rewritten with `percent_of()` → "✔";
3. `/harvest` → `harvested task 01 + 1 lesson   area: none`;
4. the task: `base_sha` = QA's commit, verbatim prompt, and
   `check.sh` = QA's test + the tax tests + `python3 tools/lint.py`. **The correction is encoded;**
5. the lesson: `2026-09-19 | task 01 | used Decimal and float arithmetic in billing module | used percent_of() helper for exact integer arithmetic`;
6. `lab audit`: broken → fail, house fix → pass, rule-breaking fix → fail → **discriminates**.

Cost of the session: $0.44, of which $0.22 was `/harvest`.

## Scenario validation

`lab validate`: **41/41 valid**. For every scenario, the injected test fails, the reference
fix passes the oracle, and (for A, B, C and E) a plausible rule-breaking fix passes the test
but is caught by the house rule.
