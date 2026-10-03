#!/usr/bin/env python3
"""collect-defects.py — build T16, the catalogue of what the lab found in Cortex.

  collect-defects.py [--out reports/data/defects.json]

D0's round reports each end with a `| # | What happened | Fix |` table of the
defects that round exposed. They were written as the run went, which is the only
time they are ever written honestly, and they are the raw material for T16.

This pulls them out, classifies each one, and adds the two things a table written
during a run never has: **why it would have corrupted a measurement** and **which
runs it affected**. A measurement instrument that has never been wrong has never
been checked; this is the list of times it was.

The classes are the brief's:
  task validity  a task that could not tell a good fix from a bad one
  scoring        the verdict itself was computed wrongly
  isolation      one measurement could see another
  attribution    the right answer, credited to the wrong thing
  tooling        the lab or the CLI, not the measurement
"""
import argparse
import json
import re
from pathlib import Path

CORTEX = Path(__file__).resolve().parents[2]
RESULTS = CORTEX / "lab" / "results"

# ordered: the first pattern that matches decides the class
CLASSES = [
    ("scoring", r"score|verdict|keep|kill|gate|regression|baseline|recheck|confirm|"
                r"screen|net_runs|promote|cycle count"),
    ("task validity", r"task|check\.sh|preflight|quarantin|discriminat|golden|fixture|"
                      r"harvest|lesson|base_sha|fix\.patch"),
    ("isolation", r"sandbox|worktree|cache|__pycache__|leak|shared|two repos|lock|"
                  r"parallel|oversubscrib"),
    ("attribution", r"visible|fired|invoked|loaded|firing|which item|credit"),
    ("tooling", r".*"),
]

# The consequence sentence for each class: what a reader needs in order to see why
# a bug in a measurement instrument is different from a bug in a feature.
WHY = {
    "scoring": "The verdict is the thing every other number rests on. A wrong "
               "verdict does not fail loudly: it keeps the wrong item, or buries "
               "the right one, and every later measurement is taken on the harness "
               "that mistake produced.",
    "task validity": "A task that cannot tell a house-rule fix from a rule-breaking "
                     "one scores both the same. The candidate then measures as "
                     "useless, and is killed for the task's defect rather than its own.",
    "isolation": "Two measurements that can see each other are one measurement with "
                 "extra steps. The symptom is a result that will not replicate and "
                 "no reason on the face of it.",
    "attribution": "Firing data is how an item's tier is judged and how gate 5 "
                   "decides. Counting 'unknown' as 'never fired' turns missing "
                   "evidence into evidence of absence.",
    "tooling": "It does not corrupt a number directly, but it costs a session, a "
               "round or an afternoon, and a run that has to be abandoned is a run "
               "that cannot be pooled.",
}

# Two shapes. The round reports use `| # | What happened | Fix |`; the calibration
# report, written before the lab ran, uses a richer
# `| # | Problem | Consequence without the fix | Fix |` — and that third column is
# already exactly the "why it would corrupt a measurement" the brief asks for, so
# it is kept verbatim rather than replaced by the generic sentence for its class.
ROW3 = re.compile(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
ROW4 = re.compile(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
HEADINGS = ("finding", "what the lab found", "cortex fixes made")


def classify(text):
    low = text.lower()
    for name, pat in CLASSES:
        if re.search(pat, low):
            return name
    return "tooling"


def from_results():
    out = []
    files = sorted(RESULTS.glob("round-*.md")) + sorted(RESULTS.glob("rounds-*.md"))
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        where = f.stem
        # only tables under a "findings" heading: the round reports have other tables
        for block in re.split(r"^##+ ", text, flags=re.M):
            head = block.splitlines()[0].lower() if block.splitlines() else ""
            if not any(h in head for h in HEADINGS):
                continue
            fixed_before = re.search(r"\((.*?tests.*?)\)", head)
            for line in block.splitlines():
                m4, m3 = ROW4.match(line), ROW3.match(line)
                m = m4 or m3
                if not m or m.group(2).lower().startswith(("what happened", "problem")):
                    continue
                if m4:
                    symptom, consequence, fix = m4.group(2), m4.group(3), m4.group(4)
                else:
                    symptom, consequence, fix = m3.group(2), None, m3.group(3)
                cls = classify(symptom + " " + fix)
                out.append({
                    "n": int(m.group(1)), "where": where, "class": cls,
                    "symptom": symptom, "fix": fix,
                    "detected": f"the lab, {where.replace('-', ' ')}",
                    "why_serious": consequence or WHY[cls],
                    "suite_note": fixed_before.group(1) if fixed_before else None,
                    "runs_affected": ["D0"],
                    "source": str(f.relative_to(CORTEX)),
                })
    return out


# Defects this evaluation programme found in its own instrument, written by hand
# because nothing recorded them at the time.
PROGRAMME = [
    {"class": "task validity",
     "symptom": "Two of the fifteen original holdout scenarios (HA3, HE3) had "
                "reference fixes anchored on source lines that the TRAINING "
                "scenarios rewrite, so on the final code of any run that trained on "
                "them the fix could not be applied at all.",
     "detected": "the first time the holdout was validated against a finished run's "
                 "code, rather than against a fresh repository",
     "why_serious": "Both scenarios would have been excluded from every run's "
                    "benchmark by the exclusion rule, silently reducing families A "
                    "and E to five holdout tasks each — and the exclusion would have "
                    "looked like a property of the scenarios rather than of their "
                    "anchors.",
     "fix": "Re-anchored on lines no training fix touches: HA3 filters the printed "
            "rows rather than the product list; HE3 adds its imports after the "
            "__future__ line. Neither the prompt, the test nor the oracle changed.",
     "test": "`lab validate` is now run against each run's FINAL code before its "
             "benchmark, not only against a fresh build (run-eval bench).",
     "runs_affected": ["D0", "R1", "R2", "R3", "R4", "C1"]},
    {"class": "attribution",
     "symptom": "`export-run` read a `task` key from the lab state that has never "
                "existed — the state records `tasks`, a list — so every session was "
                "exported as having harvested nothing.",
     "detected": "the pilot round, by the exported rows disagreeing with the "
                 "autopilot's own log",
     "why_serious": "Harvest quality (T11) and every per-session count would have "
                    "read zero, and the run would have looked as though `/harvest` "
                    "never fired while its log said otherwise.",
     "fix": "Read `tasks`; prefer the state's own `corrections` count over the "
            "derived one; carry `lessons_added`, `oracle` and `quarantined`.",
     "test": "The exporter is checked against D0's published numbers: 26 sessions, "
             "26 harvested tasks, 17 corrections, 10 right first time.",
     "runs_affected": ["D0", "R1", "R2", "R3", "R4", "C1"]},
    {"class": "isolation",
     "symptom": "Putting the frozen checkout's `bin/` first on a run's PATH does not "
                "freeze Cortex: `/harvest` and `/evolve` reach `cortex` from inside "
                "a rollout through a LOGIN shell, and a login profile re-prepends "
                "`~/.local/bin`, which symlinked into the live working copy.",
     "detected": "`run-eval`'s own assertion, before the first replicate rollout",
     "why_serious": "Every run would have been driven by whatever the working "
                    "checkout happened to contain that hour, and nothing in the data "
                    "would have shown it. The manifest would have recorded the frozen "
                    "tag truthfully and been wrong.",
     "fix": "`run-eval` checks all three resolution paths — the run's PATH, a login "
            "shell's PATH and the bare PATH — and refuses to start unless every one "
            "lands in the frozen worktree. The symlink was repointed for the "
            "programme (DEVIATIONS.md D-05).",
     "test": "The assertion runs before anything spends a token, on every run.",
     "runs_affected": ["R1", "R2", "R3", "R4", "C1", "GATE", "PRUNE", "M1", "X1"]},
    {"class": "scoring",
     "symptom": "The tier rubric's third criterion was computed as fired-given-"
                "VISIBLE. A rule is loaded when the agent reads a matching file and "
                "is never chosen, so that ratio is 1 by construction and a rule "
                "could not pass a criterion about where it fires.",
     "detected": "applying the rubric to D0's recorded firing data",
     "why_serious": "H3 would have been NOT SUPPORTED for a reason that is an "
                    "arithmetic artefact rather than a property of the item.",
     "fix": "Divide by the family's rollouts, which is what the pre-registration's "
            "wording says (DEVIATIONS.md D-06).",
     "test": "`use-billing-helpers` now reads 100% on its own family against 26% "
             "elsewhere, instead of 100% against 100%.",
     "runs_affected": ["D0", "R1", "R2", "R3", "R4"]},
    {"class": "task validity",
     "symptom": "The external task miner installed its venv editable against the "
                "ORIGINAL repository, so its import finder shadowed the work clone "
                "and every revert the miner made was invisible to the tests.",
     "detected": "all 50 mined candidates being rejected for 'the reference fix does "
                 "not pass the check' — a rate too perfect to be real",
     "why_serious": "Every external task would have been silently discarded, and the "
                    "second repository — the block the brief calls the most valuable "
                    "— would have been reported as impossible rather than as untried.",
     "fix": "The miner builds its venv against the work clone and asserts where "
            "`import structlog` resolves before it mines anything.",
     "test": "The assertion is a hard exit, not a warning.",
     "runs_affected": ["X1"]},
    {"class": "task validity",
     "symptom": "The miner's entanglement check ran the whole suite including the "
                "task's OWN tests, which are supposed to be red in the broken state, "
                "so every mined task was marked entangled.",
     "detected": "every one of twelve valid tasks carrying the same warning",
     "why_serious": "A validity signal that is always false is worse than none: it "
                    "would have been read as 'these tasks are all contaminated'.",
     "fix": "`--ignore` the task's own test files when checking the rest of the suite.",
     "test": "All twelve tasks now report the rest of the suite green on the broken "
             "state, with the tail of that run recorded per task.",
     "runs_affected": ["X1"]},
    {"class": "task validity",
     "symptom": "`/harvest` sometimes records a task's `base_sha` as the PREVIOUS "
                "session's commit rather than the teammate's commit that started this "
                "one, so the task's `fix.patch` contains a test the agent did not "
                "write. R1 and R2 logged one each.",
     "detected": "`lab done`'s own check, every time — `!! WRONG START: task NN: "
                 "base_sha X, but the session started at Y`",
     "why_serious": "A rollout then starts from a tree missing a test file the "
                    "session had, and the patch appears to add it. If the task's check "
                    "ran that test, the task would be unsolvable and would score zero "
                    "in every arm — a candidate killed for the task's defect.",
     "fix": "Not fixed in this programme, and deliberately so: incidence is 1 task in "
            "20-25, it is detected every time, preflight's third state (the fix's code "
            "WITHOUT its test edits must pass) is the safeguard, and in R1 the affected "
            "task was never swept. Four tasks per run also carry a golden file in their "
            "patch, and that is correct by design — preflight strips test source only.",
     "test": "`lab done` prints it; T12 counts it; the report states the incidence.",
     "runs_affected": ["R1", "R2"]},
    {"class": "scoring",
     "symptom": "`bench.py` used one `--k` for both splits, so `--k 5` ran the "
                "TRAINING set at k=5 as well as the holdout. For the eight-arm R1 "
                "benchmark that is 2,240 rollouts where the pre-registration asks for "
                "996.",
     "detected": "projecting the chain's cost from the planned arm list before it "
                 "reached the benchmark step",
     "why_serious": "It produces numbers that are not wrong, only far more expensive "
                    "than the plan — about $225 against $66 for that one step. A "
                    "budget overrun with correct-looking output is the kind that gets "
                    "spent before anyone asks.",
     "fix": "`--k` is the holdout's, `--train-k` the training set's, and `--split` "
            "runs one of them. The ablation arms answer 'which part did the work', so "
            "they are holdout-only at k=3.",
     "test": "`lab/bench/test_bench.sh`; the planned benchmark total is printed and "
             "checked against the pre-registration: 3,276 rollouts.",
     "runs_affected": ["R1", "R2", "R3", "R4", "C1", "D0R"]},
    {"class": "task validity",
     "symptom": "The pre-registered exclusion rule was RECORDED and never APPLIED. "
                "`run-eval bench` validated every holdout scenario against the run's "
                "final code and wrote the failures to `excluded.json` — and then ran "
                "the benchmark over all of them anyway.",
     "detected": "reading the code path while a sweep held the CPU, rather than "
                 "running it",
     "why_serious": "The worst of both: a file asserting a task was excluded, beside "
                    "a results set in which it was not. A scenario whose reference fix "
                    "cannot be applied on that run's code is one nobody can show is "
                    "solvable, and it would have scored in both arms and been quoted "
                    "as evidence.",
     "fix": "`bench.py --exclude`, passed by `run-eval` from `excluded.json`, applied "
            "identically in every arm. Read back from disk, so a re-run with "
            "--skip-validate still honours what the first pass found.",
     "test": "`lab/bench/test_bench.sh`; the run prints what it drops and the counts "
             "before and after.",
     "runs_affected": ["R1", "R2", "R3", "R4", "C1", "D0R", "M1"]},
    {"class": "isolation",
     "symptom": "The chain script is re-read by bash as it executes, so it was made to "
                "run from a pinned copy — and the copy recomputed its root from its own "
                "location, two directories above the repository. With every path wrong, "
                "`wait_for_run` found no log, treated that as 'finished', and tried to "
                "start R2 **while R1 was still running**.",
     "detected": "the driver log, immediately: it died on a permission error creating "
                 "`/home/cortex-eval` before it could launch anything",
     "why_serious": "Two runs on twelve CPUs do not go twice as fast. Cortex "
                    "invalidates a rollout that timed out while the machine was "
                    "oversubscribed, so the result would have been a primary run full "
                    "of INVALID rows and a replicate that could not be pooled.",
     "fix": "The paths travel in the environment (`PROGRAMME_CORTEX`, `PROGRAMME_EVAL`); "
            "a missing log beside an existing run directory is a FINDING rather than "
            "success; and `no_run_in_flight` refuses to start anything while a "
            "`run-eval` or `autopilot` process is alive.",
     "test": "`no_run_in_flight` runs before every `run-eval new` in the chain.",
     "runs_affected": ["R1", "R2"]},
    {"class": "tooling",
     "symptom": "`bench.py report` written with BENCH_OUT unset defaults to "
                "`lab/bench/` and overwrote D0's REPORT.md. The guard protected the "
                "files listed in D0-PROTECTED.txt but was being asked about the "
                "directory that holds them.",
     "detected": "a routine `verify-d0` check immediately afterwards",
     "why_serious": "D0 is evidence. The overwrite regenerated the same numbers from "
                    "the same unchanged rows, so nothing moved — but only because the "
                    "backup existed to prove it.",
     "fix": "The guard protects the exact file each command writes, and `report` is "
            "guarded too. `verify-d0` makes the claim checkable at any point.",
     "test": "`lab/bin/verify-d0` — 1,393 files against the backup.",
     "runs_affected": ["D0"]},
    {"class": "isolation",
     "symptom": "The gate testbed on disk had been built from R1 during a rehearsal, "
                "before C1 existed, and `gate-calibration --from C1` reused any testbed "
                "it found. H5 would have been measured on R1's repository, recorded as "
                "`from_run: C1`, with its screen tasks read from R1's sweeps.",
     "detected": "reading the testbed's own history (`cortex: evolve, round 10` — C1 "
                 "never evolves) before the step ran",
     "why_serious": "PREREGISTRATION §7 names C1's repository — no items ever live — as "
                    "the testbed. The substitution would have been invisible in the "
                    "data: every row would have carried the pre-registered label.",
     "fix": "A testbed records the run it was built from (`testbed.json`) and is refused "
            "for any other; the stale one was set aside and the testbed rebuilt from C1.",
     "test": "`gate-calibration --from C1 --dry-run` builds and checks it without "
             "spending a rollout.",
     "runs_affected": ["GATE"]},
    {"class": "task validity",
     "symptom": "C1 never ran /evolve, so its repository holds no sweep, and the "
                "baseline §7 requires — the tasks failing with no items live, "
                "\"measured once before any candidate is screened\" — had nothing to be "
                "read from. The code fell back to \"every task is fair game\", and a dry "
                "run CACHED that fallback for the real run to reuse.",
     "detected": "reading `baseline_failing()` against C1's actual repository",
     "why_serious": "Placebos would have been screened on tasks 01-04 whether or not "
                    "they fail. On a task that already passes a placebo cannot show a "
                    "spurious gain, so the false-KEEP rate — H5's headline — would have "
                    "been biased toward zero: the gates would have looked better "
                    "calibrated than they are.",
     "fix": "The baseline is measured: one confirm sweep, k=3, over every task, reading "
            "only the BASE arm, which is always the empty harness. The candidate that "
            "carries the sweep is a neutral note; a truly inert one was tried first and "
            "Cortex refused it (\"it could never load, so the sweep would measure "
            "nothing\"). Dry runs no longer cache.",
     "test": "`cortex sweep --dry-run` accepts the probe; the dry run writes no cache.",
     "runs_affected": ["GATE"]},
    {"class": "attribution",
     "symptom": "Nothing checked that a gate candidate's `cortex sweep` had run. A "
                "refused sweep (a lock, its budget, a candidate it will not load) writes "
                "no results, and `cortex score` then prints the PREVIOUS sweep's scores.",
     "detected": "reading the screen/confirm flow",
     "why_serious": "Another candidate's verdict would have been recorded under this "
                    "candidate's name with no trace that it had never been measured.",
     "fix": "Each sweep must have written a new results file that names this candidate "
            "and phase, or the testbed stops.",
     "test": "The refusal of the inert probe showed the failure mode is real.",
     "runs_affected": ["GATE"]},
    {"class": "scoring",
     "symptom": "Per-item cost and rollout counts summed every file in `.evolve/runs/`, "
                "which is never cleared. Each gate candidate would have been charged with "
                "every candidate before it, and the prune pass with R1's own nine "
                "inherited sweeps (254 rollouts, $32.76).",
     "detected": "reading the accounting while checking the testbed's inherited sweeps",
     "why_serious": "The cost columns of the gate and prune tables would have grown "
                    "monotonically down the table and overstated the prune experiment "
                    "by a third of a run's evolution.",
     "fix": "A gate candidate counts only the sweep files it added; the prune pass "
            "counts only files its source repository did not already have, a rule that "
            "survives a restart part-way through.",
     "test": "Before any prune pass the rule counts 0 of the testbed's 9 sweeps.",
     "runs_affected": ["GATE", "PRUNE"]},
    {"class": "isolation",
     "symptom": "Nothing stopped the chain when Claude usage ran out. `claude -p` fails "
                "in seconds; `bench.py` wrote the rollout as INVALID and moved on, a "
                "restart counted those rows as done, and the callers' `|| true` "
                "swallowed any failure — each step would have \"finished\" and earned "
                "its marker. The judge had the same hole: `cortex jev doctor` exits 0 "
                "when Jev is merely off, and the scope replay then reports only its "
                "deterministic half.",
     "detected": "asking, before an unattended run, what a usage limit would do",
     "why_serious": "The operator's standing instruction is to stop and ask for a "
                    "recharge. Instead the tail of the programme — gates, prune, "
                    "structlog, the Sonnet study — would have raced through in minutes "
                    "recording INVALID rows and RERUN verdicts as results.",
     "fix": "`usage-guard`: every paid step checks the measured spend against "
            "BUDGET_CAP_USD and probes Claude with its own model before starting, and "
            "a watchdog stops a step's whole session when rollouts cannot run and "
            "Claude does not answer. `bench.py` stops after five such rollouts in a "
            "row (exit 3) and a restart re-measures them. Jev must actually answer.",
     "test": "A fake failing `claude` against a scratch copy of a real bench, and the "
             "chain's `step()` under a fake guard in seven scenarios. Across the whole "
             "history the outage signature fires 0 times: no false alarm in 437 "
             "sessions and ~5,000 rollouts.",
     "runs_affected": ["D0R", "GATE", "PRUNE", "X1", "M1"]},
    {"class": "task validity",
     "symptom": "`remeasure-d0` wrote D0's holdout exclusions to `excluded.json` and "
                "never passed them to the benchmark — the bug `run-eval` had once.",
     "detected": "reading the script before restarting it",
     "why_serious": "None here: D0 validated 30/30 and excluded nothing. On a run that "
                    "excluded a task, the file and the results would have disagreed.",
     "fix": "The exclusions are passed to `bench.py run --exclude`.",
     "test": "—",
     "runs_affected": ["D0R"]},    {"class": "isolation",
     "symptom": "The structlog training loop jumped from one task's commit to the next "
                "with `git checkout -f`, which removed Cortex's own files — config, "
                "harvested tasks, lessons, evolved items, CLAUDE.md, the /harvest "
                "command — because they are committed on our branch and upstream "
                "commits do not contain them.",
     "detected": "replaying the setup and one jump on a clone before the run: "
                 "`cortex status` read 0 tasks and 0 lessons after the first jump",
     "why_serious": "H15 — the block the brief calls the single most valuable — would "
                    "have measured eight sessions that each started from nothing. The "
                    "loop could never accumulate a task or an item, and the result would "
                    "have looked like 'Cortex learns nothing on a real repository'.",
     "fix": "`training_state()`: HEAD never moves; the code is restored from the task's "
            "commit, the harness from where the loop left it, and the implementation "
            "reverted to its parent — the broken state mine-tasks.py validated.",
     "test": "On a clone: after a jump the harvested task, the evolved rule, the lessons, "
             "the config and CLAUDE.md are all present, the tests equal the task's "
             "commit, the implementation its parent, and every other file its commit.",
     "runs_affected": ["X1"]},
    {"class": "isolation",
     "symptom": "The structlog setup pinned the sweep model only if the line already "
                "named a Claude model, and `cortex init` writes `model: \"\"`. It also "
                "rewrote `sandbox_root` with a hard-coded four-space indent in a "
                "two-space file, and did not stop if `cortex config` refused.",
     "detected": "reading the setup against the frozen `cortex init` template",
     "why_serious": "An empty model means whatever the CLI defaults to, which follows the "
                    "operator's interactive `/model` — it read `opus` when checked. Every "
                    "structlog sweep would have run on a different, far dearer model than "
                    "the rest of the programme, against §0.",
     "fix": "The model is pinned whatever its value, keeping the file's indent; "
            "`cortex config` must succeed and the compiled model must be Haiku before "
            "the first session.",
     "test": "The real `cmd_setup()` against a scratch clone: the compiled config reads "
             "`claude-haiku-4-5-20251001`.",
     "runs_affected": ["X1"]},    {"class": "task validity",
     "symptom": "Cortex validates and measures every harvested task in a fresh `git "
                "clone` of the repository and runs its check as `cd <clone> && env "
                "<rollout_env> bash check.sh`. For structlog a clone has no virtualenv, "
                "this machine's `python3` has no pytest, and /harvest teaches `python3 -m "
                "pytest …`.",
     "detected": "asking how a structlog check would run inside a sweep, before the run",
     "why_serious": "Every harvested task would have failed preflight on its FIXED state "
                    "and been quarantined; with fewer than three valid tasks /evolve "
                    "refuses to run. The second repository would have reported 'no gain' "
                    "for a reason that had nothing to do with the loop.",
     "fix": "A test-tools-only Python (structlog deliberately not installed) first on PATH, "
            "with PYTHONPATH=src, for the training sessions and — through `rollout_env` — for "
            "every preflight, check and rollout; `import structlog` resolves to the clone's "
            "own source, and would fail loudly rather than import another copy.",
     "test": "Setup's own self-test before the first session: in a bare clone, `python3 -m "
             "pytest` runs and structlog imports from inside the clone.",
     "runs_affected": ["X1"]},    {"class": "scoring",
     "symptom": "The prune experiment's second pass recorded each planted item as ACCEPT if "
                "it had been deleted and REJECT otherwise. An item /prune refused to test — "
                "'never loaded — a removal can only be UNMEASURED' — was written down as if "
                "a sweep had decided to keep it.",
     "detected": "reading the recorded verdicts against Cortex's own prune-plan.json, after "
                 "the pass",
     "why_serious": "It erased the one behaviour H10 exists to test — refusing to delete what "
                    "was never seen to fire — and turned two correct refusals into two "
                    "apparent mismatches.",
     "fix": "Second-pass verdicts come from Cortex's plan (decided verdict, or SKIPPED); the "
            "four recorded rows were corrected from the same file, nothing re-run. Matching "
            "stays strict: an item pre-registered UNMEASURED that Cortex SKIPPED is still a "
            "mismatch.",
     "test": "The corrected rows equal the plan file item for item.",
     "runs_affected": ["PRUNE"]},    {"class": "task validity",
     "symptom": "structlog's oracle linted with today's ruff (0.16.9) under the project's "
                "select=[\"ALL\"]; the project's own upstream commits fail that with 51-56 "
                "errors, mostly a rule that did not exist when the code was written.",
     "detected": "the first training session: three lint 'corrections' for files the task "
                 "never touched, and a harvested check that failed preflight",
     "why_serious": "Every external task was unsolvable as defined; the loop would have "
                    "learned from corrections about unrelated files, and H15 would have "
                    "measured whether an agent can relint a codebase, not the project's rules.",
     "fix": "Lint with the ruff the project pinned at each commit (.pre-commit-config.yaml): "
            "a dispatcher reads the checkout's pin, for the oracle, the sessions, Cortex's "
            "preflight and sweeps, and the benchmark. The run restarted from scratch (D-11).",
     "test": "All twelve upstream fixes pass lint under their own pin; setup's self-test "
             "checks `ruff` and `python3 -m ruff` resolve to the pin in a bare clone.",
     "runs_affected": ["X1"]},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(CORTEX / "lab" / "reports" / "data" / "defects.json"))
    a = ap.parse_args()
    rows = from_results()
    for r in PROGRAMME:
        r.setdefault("where", "the evaluation programme")
        r.setdefault("source", "lab/reports/DEVIATIONS.md")
        rows.append(r)
    for i, r in enumerate(rows, 1):
        r["id"] = f"T16-{i:02d}"
        r.setdefault("test", "regression test added with the fix")
    Path(a.out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    per = {}
    for r in rows:
        per[r["class"]] = per.get(r["class"], 0) + 1
    print(f"{len(rows)} defects -> {a.out}")
    for k, v in sorted(per.items(), key=lambda x: -x[1]):
        print(f"  {v:3}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
