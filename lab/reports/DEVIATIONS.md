# Deviations

Every departure from `PREREGISTRATION.md` and from the brief, in the order it
happened, with the date, the reason, and **whether any outcome data had already been
seen** when the decision was taken. A deviation taken before any data exists is a
design decision; one taken after is a threat, and the difference is the only thing
that makes this file worth keeping.

---

## D-01 · The Jev key is refused by its gateway

**When:** 2026-09-20, Phase 1, before any evaluation rollout.
**Data seen:** none.

`jev/validate.py` (J0) asked its 104 questions and got 0 answers:

```
jev: scope: refused — AI Gateway requires a valid credit card on file to service
requests. — falling back to the deterministic path
no answers at all: J0 cannot report a result it did not measure.
  answered 0/104  ·  fell back 104  ·  0 input tokens  ·  model typesafe-ai/jev
```

So `jev/RESULTS.md` does not exist, and the semantic half of `cortex scope` is
**unvalidated**.

**What this does not affect.** Nothing that feeds H0–H15. Every primary number runs
with Jev off by design (`PREREGISTRATION.md` §3), and the gates contain no Jev code
at all — Cortex's own suite asserts the string appears nowhere in `score.sh`,
`preflight.sh` or `sweep.sh`. D0 itself ran before Jev existed.

**What it does affect.**

- **H16** is reported from its deterministic half only: glob **breadth**, which is
  the free alternative the judge would have to beat. `scope-replay` runs and reports
  it without a key. The brief anticipates exactly this case and says a non-separating
  free check is publishable on its own.
- **H17** (predicted against measured fire rate) is **NOT TESTABLE** and is reported
  as such, with this entry cited.
- **H18** (census against sample) is **dropped**. It was already the first thing to
  cut under budget pressure.

**If the key starts working before the analysis** the judge half is added, and the
report states that it was added after the runs had finished — which is fine for H16
and H17, because both are scored *against verdicts that already exist* and neither
can steer a run.

---

## D-02 · `HA3` and `HE3`'s reference fixes were re-anchored

**When:** 2026-09-20, Phase 1, before any evaluation rollout.
**Data seen:** none from any new run. D0's finished data was read, but only to
discover that the two scenarios could not be *validated* on it — not to compare
outcomes.

**What was wrong.** `PREREGISTRATION.md` §5 requires every holdout scenario to be
validated on each run's **final** code: the test must fail and the reference fix must
apply and pass. Running that check against D0 for the first time showed two of the
fifteen original holdout scenarios failing, both for the same reason:

```
FAIL HA3 list --category
     solve: cannot apply: cli.py: expected the anchor exactly once, found 0:
     '    p.add_argument("--sort", choices=["name", "price"], defa'
FAIL HE3 stale stock
     solve: cannot apply: catalog.py: expected the anchor exactly once, found 0:
     'from datetime import date\n'
```

`HA3`'s reference fix was anchored on `cmd_list`'s body and on the `--sort` line,
both of which the **training** scenarios A01, A04 and A05 rewrite. `HE3`'s was
anchored on both of `catalog.py`'s import lines, which training scenario E04
rewrites. So on the final code of any run that trained on those scenarios — which is
every run — the reference fix could not be applied, and the scenario could not be
validated.

**What was changed.** The anchors only, to lines no training fix touches:

- `HA3` filters the printed rows instead of the product list, anchored on the
  `print(format_table(...))` line, and adds `--category` anchored on
  `sub.add_parser("list", ...)`.
- `HE3` adds its imports after `from __future__ import annotations`.

**What was not changed.** Not the prompt the agent sees, not the teammate's commit,
not the test, not the oracle, not the family, not the `naive` fix's *behaviour*. The
reference fix is used to validate a scenario and to prove it is solvable; it is never
shown to the agent and never used to judge a rollout.

**Why this is a validity fix and not tuning.** The change cannot move any hypothesis
in either direction: it makes two scenarios *measurable* that would otherwise have
been excluded from every run by §5.1's exclusion rule. Both now validate on both a
fresh repository and D0's final code. The alternative — excluding them — would have
left family A and family E with five holdout tasks instead of six, in every run.

This is the discipline the brief demanded for the fifteen **new** scenarios ("each
one touches code no training scenario touches"), applied retroactively to two old
ones that predate the rule.

---

## D-03 · `bench.py report`'s gain column is a per-task mean

**When:** 2026-09-20, Phase 1, before any evaluation rollout.
**Data seen:** none.

D0's `bench.py report` computed each arm's gain as a difference of pooled rollout
rates. The generalised version computes the mean **per-task** difference against the
reference arm, which is what `PREREGISTRATION.md` §11 pairs on.

The guarantee that made the original correct is kept: a task whose arms were not
measured the same number of valid times is **left out of the comparison and named**,
so "incomplete" stays visible rather than being averaged away. `lab/bench/test_bench.sh`
asserts both halves.

On D0's own data the two agree to the point: holdout 36 % → 76 %, A +67, B +89,
C +44, D 0, E 0 — the same numbers `results/FINAL.md` reports.

---

## D-04 · D0's `lab/bench/REPORT.md` was overwritten once, and restored

**When:** 2026-09-20, Phase 1.
**Data seen:** none — the file was regenerated from D0's own unchanged
`results.jsonl`, so the overwrite could not have changed a number.

While testing the new report writer, `bench.py report` was run with `BENCH_OUT`
unset, which defaults to `lab/bench/` and rewrote D0's `REPORT.md` in the new format.
The guard did not catch it: it protected the *files* listed in
`lab/D0-PROTECTED.txt` but was being asked about the *directory*.

Restored byte-for-byte from `cortex-eval/backup-D0`, which is why the backup is taken
first. The guard now protects the exact file each command writes
(`tasks.json`, `results.jsonl`, `arms.json`, `REPORT.md`), and refuses:

```
lab: refusing to have `bench.py report` write .../lab/bench/REPORT.md
```

`lab/bin/verify-d0` was added to make the claim checkable at any point, and reports
`1393 file(s) checked … UNCHANGED`.

---

## D-05 · `~/.local/bin/cortex` repointed at the frozen worktree

**When:** 2026-09-20, Phase 1, before any evaluation rollout.
**Data seen:** none.

The brief's §3.2 asks that every run put the frozen checkout's `bin/` first on
`PATH`. Asserting it turned out to be the interesting part: prepending the frozen
`bin/` to a run's own `PATH` is **not** enough, because `/harvest` and `/evolve`
reach `cortex` from inside a rollout through a **login** shell, and a login profile
re-prepends `~/.local/bin` — which symlinked into the live working copy:

```
run-eval: `cortex` resolves to /home/samuele/.local/bin/cortex
  expected the frozen checkout: .../cortex-eval-v1.0/bin/cortex
  Refusing to run: a run measured with a different Cortex than it records is worthless.
```

So the symlink was repointed for the duration of the programme:

```
before: ~/.local/bin/cortex -> .../Cortex/bin/cortex          (the live checkout)
after:  ~/.local/bin/cortex -> .../cortex-eval-v1.0/bin/cortex (the frozen tag)
```

The original target is recorded in `cortex-eval/cortex-symlink-before.txt` and is
restored when the programme ends. `run-eval`'s assertion now checks **all three**
ways `cortex` can be reached — the run's own PATH, a login shell's PATH, and the
bare PATH — and refuses to start unless all three land in the frozen checkout.

This is the deviation that matters least and was found the most usefully: without
it, every run would have been driven by whatever the working checkout happened to
contain that hour, and nothing in the data would have shown it.
