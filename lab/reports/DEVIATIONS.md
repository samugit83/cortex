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
run-eval: `cortex` resolves to ~/.local/bin/cortex
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

---

## D-06 · The tier rubric's third criterion was computed with the wrong denominator

**When:** 2026-09-20, Phase 1, before any evaluation rollout.
**Data seen:** D0's finished firing data, which is what exposed the bug.

`PREREGISTRATION.md` §11.2 point 3 reads: *"Its fire rate **on its own family's
rollouts** is higher than on the other families'."* The first implementation divided
by the rollouts where the item was already **visible**, not by the family's rollouts.

For a skill the two are different and both are meaningful. For a **rule** they are
not: a rule is loaded when the agent reads a matching file and is never *chosen*, so
fired-given-visible is 1 by construction. `use-billing-helpers` therefore scored
1.00 on its own family and 1.00 elsewhere, and failed a criterion it cannot fail:

```
use-billing-helpers   own=1.00 other=1.00  score 2/3      (wrong denominator)
use-billing-helpers   own=1.00 other=0.26  score 3/3      (as pre-registered)
```

The denominator was corrected to the one the pre-registration names. This changed
H3 on D0 from NOT SUPPORTED to SUPPORTED, which is exactly the kind of change that
has to be declared: the rubric's **wording** was fixed in advance and did not move,
the **code** did, and the fix was made because a rule cannot fail a test of whether
it was chosen — not because of which way the verdict came out.

---

## D-07 · J0's agreement threshold was lowered from 90 % to 85 %, after the measurement

**When:** 2026-09-21, after the Jev key was unblocked and J0 ran for the first time.
**Data seen:** **yes — the result was known when the threshold was changed.** This is
the most consequential entry in this file and it is written plainly for that reason.

**What happened, in order.**

1. `PASS_AGREEMENT = 0.90` was set by Cortex's author *before* any Jev call, in
   `jev/validate.py`, as the gate the whole Jev integration was blocked on.
2. The Jev key was refused by its gateway for the whole of Phase 1 (D-01), so J0
   could not run.
3. On 2026-09-21 the account was funded and J0 ran. **Result: FAIL.**

   ```
   agreement    89.4%   (93/104)   — needed >= 90%     FAIL
   separation   preserved                              pass
   calibration  monotonic                              pass
   ```

4. The operator instructed that the threshold be **85 %** and that Jev ship.
   `PASS_AGREEMENT` is now `0.85`, and the same corpus now returns **PASS** at the
   same measured 89.4 %.

**The original numbers are not lost.** The measurement did not change: 93 of 104,
89.4 %, on the committed snapshot in `jev/corpus/`. Only the bar moved. Anyone can
reproduce either verdict with one command:

```bash
python3 jev/validate.py --corpus jev/corpus        # PASS at 0.85
# set PASS_AGREEMENT = 0.90 in jev/validate.py     # FAIL, the original gate
```

**The stated reason, and its limits.** Seven of the eleven disagreements are one
case: a changelog candidate judged against a family-A task. Jev is asked *"is this
task about verifying CHANGELOG.md is updated?"* and is shown a request that never
mentions a changelog —

```
task 05 prompt (all Jev sees):
  "Prices over a thousand are hard to read... Product wants a thousands separator."
task 05 fix.patch (the keyword oracle ALSO sees):
  --- a/CHANGELOG.md          <- the house rule, absent from the request
```

— so Jev answers 9 %, correctly, to the question it was asked, while the oracle
answers "about" only because it read the solution. The two are not shown the same
information, and `RESULTS.md` said so in its own limits section before this change
was made.

That is a real criticism of the **test**. It is not a reason the **threshold** should
be 85: the honest response to an unfair baseline is a fairer baseline, not a lower
bar, and the fair version was offered and declined. Scoring those seven as baseline
error would give 100/104 = 96.2 %, and that number is recorded here as an
observation, never used as a result — deciding after the fact which disagreements
do not count is the same act as moving the line.

**What the report must do with this.** §16 (threats) states the sequence above in
full: the bar was 90, the measurement was 89.4, the bar became 85, and the
integration shipped. A reader who finds this out for themselves discounts
everything; a reader who is told it up front can weigh it. No hypothesis in H0–H15
depends on J0's verdict, and every primary number still runs with Jev **off**.

**What did not change.** The arms. `PREREGISTRATION.md` §3 puts Jev off for every
run that produces a primary, because D0 had no judge and H13 ("D0 replicates") is
only testable without one. Shipping Jev is a decision about Cortex; it is not a
decision about this experiment's treatment, and the two are kept apart.

---

## D-08 · H12's arm is far weaker than the pre-registration assumed

**When:** 2026-09-22, after three replicate runs.
**Data seen:** yes — which items each run kept. No benchmark result was seen.

`PREREGISTRATION.md` §6 defines `desc-only` as "`evolved`'s **skills** keep their
`description` and `paths`, but the body is replaced by neutral filler". That
assumed the runs would keep skills. They do not:

| run | items kept | rules | skills |
|---|---|---|---|
| D0 | 3 | 1 | **2** |
| R1 | 4 | 3 | **1** |
| R2 | 4 | 4 | **0** |
| R3 | 6 | 6 | **0** |

Across the replicates the loop kept **one skill in fourteen items**. On R2 and R3
the `desc-only` arm is byte-identical to `evolved`; on R1 it rewrites one file of
four.

**What was changed:** nothing about the arm, the margin or the test. What was
added is a caveat the analysis computes and prints — how many files the arm
actually rewrote — and a rule that H12 returns **INCONCLUSIVE** when the arm
perturbed under half the harness, rather than quoting a recovered-share figure
that mostly reflects items it never touched.

**Why this is not a quiet rescue of H12.** The pre-registered margin is unchanged
and no data was re-cut to reach it. The arm simply cannot address the hypothesis
on a harness made of rules, and saying so is more honest than reporting a number
from it. The description hypothesis remains answerable on D0, which kept two
skills, and D0 is the run it was formulated from — which is itself a caution
worth printing: **the most-quoted finding of the development run rests on the one
run that kept skills at all.**

---

## D-09 · The second repository: what "a frozen base commit" means, and the order of its sessions

**Date:** 2026-09-26, before the external run's first session. **Outcome data seen:
none** — no structlog session, sweep or benchmark rollout had run.

**1. The task definition.** §10 says each task has "the implementation reverted at a
frozen base commit". `mine-tasks.py`, written and run before any session, mined
every commit up to a frozen base (`73393f3`) and defines each task **at its own
commit**: that commit's tree, with its implementation files reverted to their
parent, and the tests it touched as the check. All twelve were validated that way
(the check fails on the broken state, passes with the real implementation, and the
rest of the suite passes). The other reading — revert every task's files at one
newest commit — is not well defined for a commit whose files later commits changed
again, and no task was ever validated under it. §10's phrase is read here as
"mined from history frozen at a base commit", which is what was built.

A consequence the run nearly paid for: because each task lives at its own commit,
the training repository **jumps through structlog's history** from one session to
the next. The script jumped with `git checkout -f`, which removes Cortex's own files
— they are committed on our branch, and upstream commits do not contain them.
Replayed on a clone before the run, the first jump left `cortex status` reading 0
tasks and 0 lessons: every session would have started from an empty harness. The
code now jumps and the harness does not (`training_state()`), verified on the same
clone (T16).

**2. The order of the sessions.** §10 fixes the split — the eight older commits
train, the four newest are the holdout — but not the order within training. The
mined order ran newest first. The sessions now run **oldest commit first**, the
order a developer lived them, so the harness is carried forward in time and then
tested on the four commits that came after all of them. The split is unchanged.

**3. The rollout model.** Not a deviation, but the reason this entry exists: the
setup pinned the sweep model only when the line already named a Claude model, and
`cortex init` writes `model: ""` — "whatever the CLI defaults to", which on this
machine follows the operator's interactive `/model` and read `opus` when checked.
Every structlog sweep would have run on it, against §0 ("Haiku everywhere except
the model-change study"). It is now pinned and the compiled config is checked
before the first session.

---

## D-10 · The second repository runs before the model-change study

**Date:** 2026-09-26, before either phase had run. **Outcome data seen: none** for
either phase.

The brief (§4.7) lists the phases as 3 → 4 → 5 → 6 → **7 (model change) → 8 (second
repository)** → 9. The chain, written before any run, puts the second repository
first. The reason is the budget: PREREGISTRATION §12 marks the second repository as
**never cut**, and the model-change study is not on that list. If money runs short,
the phase that runs last is the one at risk, so the block that must not be cut runs
first. The Sonnet study is additionally priced by its own pilot before it commits
(`usage-guard m1-reserve`), and the chain stops and asks rather than start it over
the cap. The analysis of each phase is unchanged, and neither depends on the other.

---

## D-11 · structlog's lint stage runs the ruff the project pinned; the run restarted from scratch

**Date:** 2026-09-27, after one training session of the external run. **Outcome data
seen: none for H15** — no benchmark rollout had run.

The oracle's lint stage ran **today's** ruff (0.16.9) with the project's own
`select = ["ALL"]`. Under it, structlog's **own upstream commits** fail with 51–56
errors — mostly `CPY001`, a rule that did not exist when that code was written. Every
task was therefore unsolvable as defined, and the first session (X12) was "corrected"
three times for lint in files it never touched; `/harvest` then captured two lessons
from those corrections and built a check that failed preflight. Task mining had
validated the tests, never the lint stage.

The project's CI linted with the ruff pinned in its `.pre-commit-config.yaml` at each
commit (0.14.0 … 0.15.14). **Under its own pin, every one of the twelve upstream
fixes is clean.** The oracle — in the sessions, in Cortex's preflight and sweeps, and
in the benchmark — now runs that pinned version, through a dispatcher that reads the
checkout's own pin; setup proves it in a bare clone. This is the rule §10 fixes ("the
house rule is the project's own linter configuration"), applied as the project applied
it.

Because the first session's corrections and lessons came from the broken oracle and
would bias everything learned after them, the external run was **restarted from
scratch**: the first attempt is kept under `cortex-eval/stale/X1-lint-contaminated/`
(its spend still counted) and is not used for anything.

---

## D-12 · H15 cannot be SUPPORTED by a benchmark of two identical harnesses

**Date:** 2026-09-27 00:58, while structlog's benchmark was running. **Outcome data
seen: none** — no structlog benchmark rollout had been read.

structlog's training (after D-11) harvested eight valid tasks but only **one** lesson:
seven of the eight sessions passed the project's own tests and pinned linter on the
first attempt. Nothing recurred, `/evolve` was BARREN every time, and the loop kept
**nothing** — `evolved` is byte-identical to `none` (no skill, no rule, `CLAUDE.md`
unchanged since `cortex init`).

The pre-registered rule for H15 is "a positive gain". On identical harnesses the
benchmark is an A/A, and a positive difference is noise by construction; applied
mechanically, the rule could call H15 SUPPORTED on nothing. Fixed now, before the
number exists: when the export records `harness_identical`, H15 is **INCONCLUSIVE**,
and the difference is printed as the A/A it is. Checked on synthetic rows: a planted
+10-point A/A reads INCONCLUSIVE, not SUPPORTED.

What the second repository *does* show is reported as such: on a real repository, with
Haiku, corrections were rare enough (1 in 8 sessions) that Cortex had no recurring
evidence and **correctly declined to invent a rule**. That is a finding about when the
loop has anything to do — not a test of whether a learned harness transfers.

---

**Recorded on 2026-09-27.** The nine entries below were written on that date, when the
finished report was checked line by line against its rows, Cortex's scorer and the
pre-registration. Each gives the date the decision was actually taken and what had been
seen by then. Five of them had already been noted in `CHECKPOINT-A.md`, `CHECKPOINT-B.md`
or `RUNLOG.md`, but not in this file; the other four were found only then.

---

## D-13 · The ablation arms ran at k=3, where the table of arms says 5

**When:** 2026-09-20, before any evaluation rollout: `PREREGISTRATION.md` §5 and the
budget in §12 both give k=3, and Checkpoint A (commit `a23bb26`) priced the arms at k=3.
**Data seen:** none from the evaluation; the pilot's costs only.
**Recorded here:** 2026-09-27.

The pre-registration gives two numbers for the same arms. §5 runs the holdout "at k=5
for the primary arms and k=3 for the ablations", and §12 budgets "7 arms, k=3"; the table
of arms in §6 says 5 for every arm on R1 except `swapped`. The arms ran at k=3 (`none2`,
`kitchen`, `ideal`, `flat` and `desc-only` on R1, `accept-all` on R2), as §5 and §12 say.
No margin changed; the intervals of these arms are wider than k=5 would have given.

---

## D-14 · `accept-all` ran on R2, not R1

**When:** 2026-09-21 20:46 (`RUNLOG.md`, "R2 finished"; commit `57cc68a`), after R1's and
R2's loops and before either benchmark.
**Data seen:** which candidates each run had buried (R1 none, R2 one); no benchmark result.
**Recorded here:** 2026-09-27.

The table of arms puts `accept-all` on R1. R1 buried nothing, so there the arm would have
been byte-identical to `evolved`. It ran on R2 instead, whose one burial was
`shop-clock-explicit-imports`. H6 therefore rests on one run and one added candidate, and
that candidate was buried by the `/evolve` agent, not by a gate: `score.sh` had returned
RERUN for its only sweep (T5 shows the scorer's verdict beside the journal's).

---

## D-15 · `swapped` was not run

**When:** after `desc-only`'s benchmark on R1 (2026-09-22, 18:06 to 18:44); written down
in `CHECKPOINT-B.md` (2026-09-27 02:34).
**Data seen:** yes, `desc-only`'s result.
**Recorded here:** 2026-09-27.

§6 runs `swapped` "only if `desc-only` shows an effect". Pooled over the rule families,
`desc-only` recovered 79% of `evolved`'s gain, which is an effect as that condition is
worded. But the arm rewrote one item in four (D-08), and in the one family whose skill it
did rewrite (C) it recovered 16% [0%, 56%]. The pooled effect was judged uninformative and
`swapped` was not run, a decision taken with `desc-only`'s data in hand. H11 is
INCONCLUSIVE.

---

## D-16 · The mixed model was never fitted

**When:** never decided; found 2026-09-27.
**Data seen:** all of it, by the time this was found.

§11 lists a mixed model, `pass ~ arm * family + (1|task) + (1|run)`, as a robustness
check beside the primary analysis. `analysis/stats.py` defines `mixed_model()`, but
nothing calls it, and no table or figure reports it. The primary results rest on the
two-way bootstrap and the permutation test, as pre-registered; the robustness check is
missing.

---

## D-17 · H13 uses D0R, a baseline chosen after its data existed

**When:** after D0R's benchmark (its last rollout 2026-09-26 17:42); written down in
`CHECKPOINT-B.md` (2026-09-27 02:34).
**Data seen:** yes, D0R's benchmark.
**Recorded here:** 2026-09-27.

H13 asks whether the development run's gain lies inside the evaluation runs' interval.
The scorecard uses D0R, D0's harness re-measured on the replicates' 30-scenario holdout
with their tooling, as brief §4.4 designs it: +42.5. D0 on its own holdout gives +50.0,
over the 12 rule-family scenarios of its 15. Both lie inside [+35.4, +75.0], so the
verdict, SUPPORTED, does not depend on the choice; the choice was still made after both
numbers existed.

---

## D-18 · The prune experiment's second-pass verdicts were corrected after they were read

**When:** 2026-09-27 00:19 (commit `a9b86f2`; `RUNLOG.md`, "the prune experiment
finished").
**Data seen:** yes.

The experiment's script had recorded three of the four planted items as REJECT because
they were "still live". They were corrected to the verdicts Cortex itself recorded in its
`prune-plan.json`, REJECT for `after-finishing-an-edit` and SKIPPED for the two the plan
never measured, with nothing re-run (T16). Matching was kept strict, and the count moved
from 5 to 6 of 8. H10 is NOT SUPPORTED either way.

---

## D-19 · H3's rubric is scored more leniently than §11.2 words it

**When:** the scoring code was written before any evaluation rollout (commit `a23bb26`,
2026-09-20); found 2026-09-27.
**Data seen:** none when the code was written.

§11.2's first criterion puts "a duty the task itself names ('add an exporter')" in a
skill; `analysis/rebuild.py`'s `tier_rubric()` passes every path-scoped rule on form. Its
second asks that a glob not "cover a family it is not about"; the code passes every
path-scoped item on scope. Read as written, the four rules on `shop/**` that pass the
third criterion fail the second, and the two exporter rules (R2
`exporter-docs-and-golden`, R3 `exporter-checklist-v2`) fail the first: at most 9 of the
18 kept items score 3/3, not 15, and fewer under a strict reading of "cover", since the
rules on `shop/billing/**` also load on other families' tasks. H3 is NOT SUPPORTED either
way. D-06 corrected the third criterion's denominator; this entry concerns the first two.

---

## D-20 · H4 was computed over all sessions, and not tested

**When:** the analysis code was written before any evaluation rollout (commit `a23bb26`,
2026-09-20); found 2026-09-27.
**Data seen:** none when the code was written.

§11 pre-registers H4 as "corrections per session after an item went live, against the
same scenarios in the control run, by permutation over runs, with the full curve shown".
`analysis/rebuild.py` compares all sessions of the evaluation runs with all sessions of
C1 (0.58 against 0.88 corrections per session) and runs no test. The scorecard's
criterion, "evaluation below control", is the code's, since the pre-registration sets
none. With one control run, no permutation of the run labels can give p below 0.2. H4
stands as a description.

---

## D-21 · H12 is reported pooled; its margin is stated per family

**When:** the analysis code was written before any evaluation rollout (commit `a23bb26`,
2026-09-20); D-08's INCONCLUSIVE rule was added on 2026-09-22; found 2026-09-27.
**Data seen:** none when the code was written.

§11.1 states H12's comparison as "`desc-only` − `none`, holdout, per family". The
scorecard reports one share pooled over the rule families, 79% [58%, 100%]. Per family,
only C was rewritten, and there `desc-only` recovered 16% [0%, 56%], below the 50%
margin; in A, B and E the arm is identical to `evolved`. The verdict stays INCONCLUSIVE
under D-08's rule.

---

## D-22 · The final report reads H0, H5 and H16 from what the code and the scorer did

**When:** 2026-09-29, when the final report was generated.
**Data seen:** all of it.

The first report, generated on 2026-09-27, took some of its counts from records the agents
and the lab's scripts wrote. The final report, generated from the same rows, takes them from
`score.sh`'s own verdicts and from the rules the analysis code applies:

- **H5.** A harmful candidate counts as killed when `score.sh` killed it. The gate procedure
  stops at any screen whose gain is not positive or whose candidate never fired, and records
  that stop as a KILL; `score.sh` returned RERUN, a verdict on nothing, for three of the five
  harmful candidates. The margin's wording is unchanged; the count it is read against is 2
  of 5, where the first report printed 5 of 5.
- **H16.** On the evaluation runs, "buried on a regression" is read as a KILL by `score.sh`
  on gate 2 or 3 (two candidates). The first report took each candidate's fate from its
  run's journal, which counted every burial except those for gate 5 as a regression, and
  pooled the development run with R1–R4. The development run is now reported beside, with
  its journal's fates.
- **H0.** The scorecard's margin now states the rule the analysis code has applied since it
  was written (commit `a23bb26`, before the first evaluation run): D at or above 90 %, and at
  least three of the four rule families below 50 %. The text printed beside it had asked all
  four; that stricter reading is not met, and the scorecard says so.

The loop's fates in T5, T6 and T19 and in F10, F11 and F18 are likewise `score.sh`'s rules
applied again to the recorded rollouts (`analysis/rescore.py`), with the journal's record
beside them where the two differ.

No verdict changed: H0 is SUPPORTED under the code's rule, H5 NOT SUPPORTED (two of four
positives kept, under either count), H16 NOT SUPPORTED (neither predictor separates, under
either reading).
