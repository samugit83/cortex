# Run log

Chronological. One entry per run, per round and per protocol FINDING, with what it
cost. Appended as things happen, never rewritten.

| | |
|---|---|
| Pre-registration | `PREREGISTRATION.md`, commit recorded at the freeze |
| Frozen Cortex | `v1.0-eval` |
| D0 | read-only throughout; `lab/bin/verify-d0` proves it |

---

## Phase 1 — preparation (no evaluation rollouts)

2026-09-20

- D0 backed up to `cortex-eval/backup-D0` (1,393 files) and verified UNCHANGED.
- `lab/bin/guard.py` + `lab/D0-PROTECTED.txt`: the tools refuse to write to D0.
- `observe` records `turns`, `tool_calls`, `read_contributing`; sweep row schema 2 → 3.
- `bench.py`: nine named arms, per-arm always-on accounting, generalised report.
- `autopilot`: `--no-evolve`, a 40-turn cap and a 15-minute per-call timeout.
- 15 new holdout scenarios written; **56 scenarios, all valid**.
- `lab/bin/export-run` reproduces every headline number in D0's `results/FINAL.md`.
- 29 gate candidates and 4 prune plants generated and committed.
- `test/run-tests.sh`: **653 passed, 0 failed**.

FINDINGs raised in Phase 1: see `DEVIATIONS.md` D-01 (no Jev key), D-02 (`HA3`/`HE3`
re-anchored), D-04 (D0's `REPORT.md` overwritten once and restored).

---

## Phase 2 — the pilot

2026-09-20 22:34–22:46 · `PILOT` · frozen Cortex `v1.0-eval` (`23bd5e4`) · Jev off

| | |
|---|---|
| B01 | verdict B → correction → ok · task 01 + 1 lesson · $0.73 |
| B02 | verdict B → correction → ok · task 02 + 1 lesson · $0.36 |
| B03 | verdict B → correction → ok · task 03 + 1 lesson · $0.59 |
| `/evolve` | screen 12 rollouts → confirm 18 rollouts → **KEEP** `billing-rates-rule`, a rule on `shop/billing/**` |
| gain | +2.67 · regression 0.00 · worst drop 0.00 · 01: 0→100 %, 02: 33→100 %, 03: 0→100 % |
| invalid | 0 of 30 rollouts |
| cost | $2.02 agent + $3.02 rollouts = **$5.04**, 11 min wall |

**Confirmed:** schema-3 rows carry `turns`, `tool_calls` and `read_contributing` in a
real sweep; `read_contributing` is 0 in every pilot rollout. Jev off is visible in the
config dump (`key absent`, `jev.enabled False`).

FINDING (tooling, fixed): `export-run` read a `task` key the lab state has never had
— it records `tasks`, a list — so every session would have been exported as having
harvested nothing. Caught by the pilot disagreeing with its own log. Fixed and D0
re-exported; see CHECKPOINT-A §2.

**Checkpoint A written.** Projection ≈$1,444 against a $1,500 cap. Jev blocked on
account verification (`DEVIATIONS.md` D-01). **Stopped to ask the user**, per their
standing instruction to stop whenever the Jev key does not work.

---

## 2026-09-21 — the judge is unblocked, and the programme starts

**Jev.** The gateway account was funded. `GET /v1/credits` → `{"balance":"20"}`;
`cortex jev doctor` answers in 589 ms as `typesafe-ai/jev`. Pricing from the
gateway's own model record: **$0.042/MTok in, output free**. The whole programme's
judge workload is ~594 questions, ~218k input tokens — **under one cent**.

**J0 ran for the first time.** 89.4 % agreement (93/104) against its 90 % bar,
separation preserved, calibration monotonic → **FAIL**. The bar was then lowered to
85 % on the operator's instruction and the same corpus passes at the same 89.4 %.
Both numbers are preserved; `DEVIATIONS.md` **D-07**.

**A defect found in `cortex scope --json`.** It asks Jev two questions per task and
pays for both, then omits the second (`would_fire`) from the `scope` object — it
survived only under `items`, where nothing looked. Fixed. It could not have touched
a run: Jev is off in every one.

**H16 on D0, honestly: NOT SUPPORTED.** Over all ten candidates neither the judge's
relevance nor the free control (glob breadth) separates KEPT from
BURIED-on-regression. J0's contrary result is correct too, over a smaller candidate
set; the report states both and explains the denominator.

**H17 on D0: SUPPORTED at n = 2**, rank order preserved, and the miss is the
interesting part — `check-changelog-on-shop-edits` was predicted to be invoked 64 %
of the time and was invoked 6 %.

### The runs

| | |
|---|---|
| 17:26 | **R1** launched: ten rounds, Jev off, frozen Cortex `v1.0-eval` |
| 17:38 | R1 round 1 done — `billing-rates-rule`, a rule on `shop/billing/**`, KEEP |
| 17:42 | `lab/bin/programme` launched: it waits for R1, then runs R2–R4, C1, every benchmark, D0's re-measurement, the gate and prune testbeds, the second repository, the exports and the scope replay, in sequence |
| 17:51 | R1 round 2 done — family A learned as a **rule**, where D0 chose a gated skill |

The steps are sequential on purpose: every sweep sizes itself to 12 workers on 12
CPUs, and Cortex invalidates a rollout that timed out while the machine was
oversubscribed. Two runs at once would buy a pile of INVALID rows in a primary
rather than speed.

### R1 · protocol FINDING, round 6 (logged, not repaired)

```
2026-09-21 18:39:37  FINDING C04: !! WRONG START: task 17: base_sha 55dadaa3eb2a,
                     but the session started at dce69eb35734
```

`/harvest` recorded task 17's `base_sha` as `55dadaa` — the *previous* session's
commit — instead of `dce69eb`, the teammate's commit that injected the NDJSON
test. The consequence is visible in the patch: task 17's `fix.patch` contains
`tests/test_export_ndjson.py`, a test the agent did not write.

**Why it is probably not a corrupted measurement.** Task 17's `check.sh` does not
run that unittest; it runs the CLI and counts the JSON lines it emits. At
`55dadaa` the `ndjson` format does not exist, so the check fails on the broken
state and passes on the fix — the task still discriminates, which is what
preflight's third state exists to decide. The cost is fidelity, not correctness:
a rollout on task 17 starts from a tree that lacks a test file the session had.

Nothing was repaired by hand. The autopilot logged it and continued, preflight
decides whether the task survives, and `T12` counts it. This is the same class as
D0's round-1 finding #1, which is why `lab done` prints it at all.

### R1 · round 7 FINDING, and the first real replication result

**The FINDING.** `/evolve` reported barren and did not record it:

```
2026-09-21 18:48:59  round 7: BARREN — FINDING: no `cortex cycle`/journal record
```

`.evolve/state.json` shows `cycles: 6`, `last: BARREN`, `last_at: 18:41:52` — a
timestamp from round **6**. Round 7's `/evolve` turn ran 18:47:12–18:48:54,
concluded there was not enough evidence, and stopped without calling
`cortex cycle BARREN` or writing a journal line. The agent did not follow its own
command; Cortex's records and the autopilot's check are what caught it.

Effect on the data: none that is countable. The exported cycle count reads 6,
which is what `state.json` says. The one real consequence is that
`barren_streak` under-counts, so the loop may run one cycle longer than
`stop_after_barren_cycles` intends. Logged, not repaired; `T12` counts it.

### R1 has kept an item for family E — which D0 never managed

After seven rounds R1 is carrying **four** items, one for each rule family:

| Family | R1 | D0 |
|---|---|---|
| A | `changelog-requirement` — **rule** | `check-changelog-on-shop-edits` — gated skill |
| B | `billing-helpers` — rule on `shop/billing/**` | `use-billing-helpers` — rule on `shop/billing/**` |
| C | `exporter-checklist` — gated skill | `complete-exporter-setup` — gated skill |
| E | `shop-clock-rule` — **rule on `shop/**`** | **nothing: four attempts, all buried** |

The last row is the one to look at. D0's clearest negative result was that the
clock rule was tried four times — on `shop/**`, then `shop/billing/**`, then
`shop/**` again — and was killed every time for what it broke elsewhere. R1
proposed a rule on `shop/**`, and it **passed the same gates**.

**What this does and does not mean.** It is not yet a gain: R1's benchmark has not
run, so whether the E rule actually helps on holdout tasks is unmeasured. What is
established is narrower and still interesting — the same loop, on the same
scenarios, under a frozen Cortex, produced a *different set of survivors*. That is
H9 and H13 doing their job. If the E rule also gains on the holdout, D0's "E
failed" becomes "E failed in D0", which is a materially weaker claim than the
development run made.

Family A is a second difference in the same direction: R1 chose a **rule** where
D0 chose a gated skill, for the same duty.

### R1 finished — and it is not D0

**R1: ten rounds, 1 h 38 m, $45.54.** 26 sessions, 9 cycles, 9 sweeps, 254 sweep
rollouts, 0 invalid.

| | D0 (development) | R1 (frozen `v1.0-eval`) |
|---|---|---|
| cycles | 17 | 9 |
| verdicts | 4 KEEP · **6 KILL** · 7 BARREN | 4 KEEP · **0 KILL** · 5 BARREN |
| sweep rollouts | 984 | **254** |
| items live at the end | 3 | **4** |
| cost | $155 | **$45.54** |

R1 proposed four candidates and kept all four. D0 proposed ten and killed six.

**Two of the candidates D0 killed, R1 kept — in the same form, on the same scope:**

| candidate | D0 | R1 |
|---|---|---|
| a changelog rule on `shop/**` | `changelog-rule-v2` → **KILL** | `changelog-requirement` → **KEEP** |
| a clock rule on `shop/**` | `shop-clock-usage` → **KILL** | `shop-clock-rule` → **KEEP** |

**The obvious hypothesis is in D0's own defect catalogue.** Cortex changed 39 times
during D0, and at least one of those changes is a mechanism that manufactures
spurious KILLs: `score.sh` listed confirm sweeps with an unquoted `$(ls …)`, and
this repository lives under a path with a space in it, so **every recheck in the
lab** answered "no confirm precedes this one" and degraded to RERUN. D0's own
round-9 note records a +4.33 candidate killed on a regression its recheck had just
cleared. R1 ran on the frozen tag, with that fix and 38 others already in.

If that is the explanation, then **D0's negative results are partly artefacts of
the tooling D0 ran on** — which is exactly why the brief demanded a frozen re-run,
and it is the strongest argument so far that the programme was worth its cost.

**What is not yet established.** "Kept" is not "helps". R1's benchmark has not run.
Four keeps and zero kills also raises the opposite worry — that the gates are now
too permissive — and there are three measurements designed to answer it: family D
in the benchmark (H2), the `accept-all` arm (H6), and the 20 placebos in the gate
testbed (H5), which measure the false-KEEP rate directly. None of them has run yet.

### WRONG START: the same finding in two runs, quantified

R1 and R2 each logged one:

```
R1  FINDING C04: !! WRONG START: task 17: base_sha 55dadaa3eb2a, but the session started at dce69eb35734
R2  FINDING A05: !! WRONG START: task 20: base_sha 737914b795c0, but the session started at 472382db7216
```

Two runs, same class, so it was counted rather than noted:

| | R1 | R2 |
|---|---|---|
| WRONG START findings | 1 | 1 |
| tasks whose patch contains a `tests/` path | 5 of 25 | 5 of 19 |
| …of those, **test source** (`tests/test_*.py`) | **1** | **1** |
| …of those, test **data** (`tests/golden/`) | 4 | 4 |

The distinction is the whole answer. Four tasks per run carry a golden file in
their patch, and that is **correct by design** — D0's calibration finding #3
established that preflight strips test *source* only, because an exporter's golden
file is data the fix legitimately produces. Exactly one task per run carries test
*source*, and in both runs it is the task `lab done` had already flagged.

So the incidence is **1 task in 20–25, detected every time**. In R1 the affected
task (17) was **never swept** — it was harvested after the last confirm sweep and
no measurement ever used it.

**Not treated as a defect requiring a re-tag.** `PREREGISTRATION.md` §2.5 reserves
stop-fix-retag-restart for a defect that would corrupt a measurement. This one is
detected by the lab's own check, affects a known 4–5 % of tasks, is handled by
preflight's third state (the fix's code without its test edits must still pass),
and in one of the two runs touched nothing at all. Restarting four runs over it
would cost more than it could possibly buy. It is recorded in `T12` and `T16`
with this incidence, and the report states it as a limitation rather than hiding
it inside a FINDING count.

### R2 finished — and the replicate matrix has a shape

| run | cycles | KEEP | KILL | BARREN | sweep rollouts | cost | items |
|---|---|---|---|---|---|---|---|
| D0 | 17 | 4 | **6** | 7 | 984 | $155.45 | 3 kept / 7 buried |
| R1 | 9 | 4 | **0** | 5 | 254 | $45.54 | 4 kept / 0 buried |
| R2 | 9 | 4 | **1** | 4 | 236 | $46.57 | 4 kept / 1 buried |

R1 and R2 are near-identical in shape: nine cycles, four keeps, ~245 sweep
rollouts, ~$46. D0 needed **four times the rollouts and three times the money** to
keep one item fewer.

**What each run learned, by family:**

| family | D0 | R1 | R2 |
|---|---|---|---|
| A | gated skill on `shop/**` | **rule** on `shop/**` | **rule** on `shop/**` |
| B | rule on `shop/billing/**` | rule on `shop/billing/**` | rule on `shop/billing/**` |
| C | gated skill on `shop/plugins/**` | gated skill on `shop/plugins/**` | **rule** on `shop/plugins/**` |
| E | nothing — four attempts, all buried | rule on `shop/**` | rule on `shop/**` |

**The scope replicates perfectly and the form does not.** Every run that learned a
family chose the same glob — `shop/billing/**` for money, `shop/plugins/**` for
exporters, `shop/**` for the two repo-wide duties — three times out of three, with
no exceptions. The *form* varies: family A is a skill in D0 and a rule in both
replicates; family C is a skill in D0 and R1 and a rule in R2.

If that holds through R3 and R4 it is the cleanest thing H9 can say: **the loop
finds the area reliably and the shape less so.**

R2's one burial was `shop-clock-explicit-imports`, declined not by a gate but as a
duplicate — *"overlaps with live rule shop-clock-not-datetime; refinements use
/prune"*. That makes R2's `accept-all` a real arm where R1's was degenerate, so H6
is measured on R2.

### R3 · the 40-turn cap fired, and nothing was lost

```
2026-09-21 21:17:57  turn round 2 /evolve #1: 564s $0.347 rc=1 ERROR FINDING hit the 40-turn cap
2026-09-21 21:18:02  round 2: cycle ended (cycles 3, journal entries 3)
2026-09-21 21:18:02     committed 4 change(s) from /evolve: d385041
```

The turn was cut off at turn 41 of a 40-turn budget, after 564 seconds — and the
cycle **completed anyway**: three cycles recorded, three journal entries, four
files committed.

That is the cap doing its job (bounding one message, and saying so on the record
rather than silently), and it is also an unplanned test of something Cortex claims
about itself: **the loop's state lives in `.evolve/`, not in the conversation.**
The sweep had run, the score was computed and the journal was written before the
agent was cut off, so losing the agent mid-sentence cost a summary and nothing
else. A design that kept its state in the chat would have lost the cycle.

First occurrence in three runs. Left at 40: raising it now would change the
instrument mid-programme, and the one time it fired it cost nothing.

### R3 · the 15-minute timeout fired, and the autopilot recovered by design

```
23:09:35  round 9: /evolve (cycles so far 9, candidates [])
23:24:35  turn round 9 /evolve #1: 900s $None rc=124 ERROR FINDING timed out after 15 min
23:24:40  a sweep is running: ['…231057-screen.jsonl', '…231229-confirm.jsonl']
23:24:40  sweep running… [confirm] cand task 25 run 1 -> FAIL (40s) [w1]
```

The agent was killed at fifteen minutes. **The sweep it had launched kept running**,
because a sweep is a detached process writing to `.evolve/runs/`, not something the
agent holds open. The autopilot saw the lock, waited, and will call `/evolve` again
— which reads the finished sweep off disk and scores it.

This is the second unplanned test of the same property the turn cap exercised in
round 2: *the loop's state is on disk, so losing the agent costs the agent and
nothing else.* Worth stating plainly in the report, because it is the difference
between a loop you can leave running and one you have to supervise.

One cost: the timed-out turn recorded **no cost** (`$None`), because a killed call
returns no result JSON. Its spend is real but unattributed, so `T14`'s agent
column under-counts by one turn in R3. The rollout costs are unaffected — those
come from the sweep rows.

**Something to check when this cycle ends.** The candidate under confirm is
`text-utilities-correctness`. `shop/util/text.py` is **family D** — the control
family, which has no house rule and where *nothing should be learned*. If this is
kept, it is a spurious item and bears directly on **H2**, which requires that none
be kept. If it is killed, it is the protected set doing its job. Either way it is
the first candidate in any run that points at the control family, and it gets its
own paragraph in the report.

### R3 overturns two things this log said earlier

**Correction 1 — "the frozen runs are cheaper and cleaner than D0" was an n=2 claim, and it is wrong.**

| run | cycles | KEEP | KILL | BARREN | sweep rollouts | cost |
|---|---|---|---|---|---|---|
| D0 | 17 | 4 | 6 | 7 | 984 | $155.45 |
| R1 | 9 | 4 | 0 | 5 | 254 | $45.54 |
| R2 | 9 | 4 | 1 | 4 | 236 | $46.57 |
| **R3** | **11** | **6** | **4** | **1** | **966** | **$144.64** |

R3 ran on the same frozen Cortex and came out looking like D0: four kills, 966
rollouts, $145. So "D0 was expensive because its Cortex was buggy" is not
established. What is established is that **run-to-run variance is large even with
the system frozen** — 236 to 966 rollouts, $46 to $145, for the same ten rounds on
the same scenarios. That is a result about the loop's cost predictability, and it
is a less flattering one than the two-run version.

**Correction 2 — "scope replicates 4 of 4" was also an n=2 artefact.**

R3 did not use globs. It proposed the broad rule, had it killed, and then kept a
set of **narrow per-file rules**:

| | broad version (buried) | what R3 kept instead |
|---|---|---|
| B | `use-rate-helpers` on `shop/billing/**` | two rules over five named billing files |
| C | `exporter-checklist`, gated skill on `shop/plugins/**` | rule on `shop/plugins/*_export.py` |
| E | `shop-clock-access` on `shop/**` | rule over three named files |

Pairwise scope agreement: **D0/R1 3/3, D0/R2 3/3, R1/R2 4/4 — and R3 agrees with
nobody, 0/3, 0/4, 0/4.**

So it is not general chaos: three runs agree completely and one took a different
route. The loop reliably finds the *area*; it does not reliably choose between
**one broad rule** and **several narrow ones** — and both survive the gates, so
this is a property of the proposal layer, not a gate failure. Every narrow rule R3
kept passed a sweep that the broad version had failed.

**Two more analysis defects found while rendering this.** The family classifier
read paths before names, so `shop-clock-narrow` — scoped to `shop/billing/invoice.py`
among others — classified as family B and emptied family E for a run that had
plainly learned it. And the matrix held one item per cell, so R3's six items
showed as four. Both fixed; both would have put a wrong sentence in the report.

### The turn bounds, counted rather than anecdotal

I described the 40-turn cap earlier as a "first occurrence in three runs". Counted
properly across every turn the programme has driven:

| run | turns | hit the 40-turn cap | timed out at 15 min |
|---|---|---|---|
| PILOT | 13 | 0 | 0 |
| R1 | 91 | 0 | 0 |
| R2 | 93 | 0 | 0 |
| **R3** | 109 | **2** | **1** |
| R4 (so far) | 47 | **1** | 0 |
| **all** | **353** | **3** | **1** |

**1.1 % of turns hit a bound**, and *every one of them is an `/evolve` turn* — no
session, correction or `/harvest` has ever come close. That makes sense: `/evolve`
is the turn that reads the lessons, writes a candidate, launches a sweep, waits
for it, scores it and journals it, so it is the only one doing minutes of work in
one message.

They cluster in R3, the run that proposed broad rules, had them killed, and
retried narrow — more cycles, more work per cycle, more turns per cycle.

**In every observed case the cycle completed anyway**, because the sweep is a
detached process and the verdict is computed from files on disk. The cost is one
unattributed turn cost per timeout (a killed call returns no result JSON), which
makes `T14`'s agent column under-count by one turn in R3.

Left at 40 turns and 15 minutes. Both were set before the first replicate and
changing them now would change the instrument mid-programme for a bound that has
never yet cost a result.

### The bounds, corrected again — and a harvest that was right to produce nothing

I wrote earlier that every turn hitting a bound was an `/evolve` turn. That is no
longer true, and the count has moved:

| run | turns | capped | timed out | which |
|---|---|---|---|---|
| R3 | 109 | 2 | 1 | `/evolve` ×3 |
| R4 | 89 | 2 | 0 | `/evolve` ×1, **`/harvest` ×1** |
| **all** | **395** | **4** | **1** | **1.3 % of turns** |

**But the cap did not cost the task.** The sequence is worth reading in full:

```
16:31:19  turn A06 /harvest: 128s rc=1 ERROR FINDING hit the 40-turn cap
16:31:20  FINDING A06: /harvest produced no task; asking once more, as a user would
16:31:35  turn A06 /harvest again: 16s rc=0 | task 24 deleted: the check needs the fix's own test
16:31:36  A06 recorded: 0 task(s) harvested
16:31:36  FINDING A06: !! no task was harvested in this session
```

The retry succeeded, and then **deliberately deleted the task it had built**,
because the check it had written depended on the fix's own test. That is harvest
rule 7 and D0's calibration finding #3 working exactly as designed: a check that
runs a test the fix itself added can never fail on the broken state, so the task
would have scored zero in every arm and killed whatever candidate it was used to
measure.

So A06 produced no task for the **right** reason. The cap cost one extra
`/harvest` call (about $0.40) and nothing else.

**Running total: 5 of 395 turns hit a bound, and not one has yet cost a result.**
Four were absorbed because the sweep is detached and the verdict comes off disk;
this one was absorbed by the autopilot's own retry, which exists because a user
who saw `/harvest` do nothing would ask again.

### WRONG START, across five runs: three occurrences, two on the same scenario

| run | session | task | recorded base | session actually started at |
|---|---|---|---|---|
| R1 | C04 | 17 | `55dadaa` | `dce69eb` |
| R2 | **A05** | 20 | `737914b` | `472382d` |
| C1 | **A05** | 19 | `98c7db8` | `0819e6b` |

**3 occurrences in 5 runs — about 2.4 % of the ~124 sessions driven — and two of
the three are the same scenario.** A05 is `list --limit`, a family-A session whose
fix edits `cmd_list` and the `list` sub-parser; it appears once per run, so it has
now produced a wrong start in two of the five runs it has been in.

That is suggestive, not established. n = 3 is too few to say A05 causes it, and
C04 shows it is not confined to one scenario. What can be said is that the rate is
low, the check catches it every time, and the consequence is bounded: the task's
`fix.patch` then contains a test the agent did not write, and preflight's third
state — the fix's code **without** its test edits must still pass — decides
whether the task survives.

Recorded here with its incidence rather than investigated further. The decision
taken earlier stands: this does not meet `PREREGISTRATION.md` §2.5's bar for
stop-fix-retag-restart, because it is detected every time, affects a small and
known share of tasks, and has a safeguard downstream. Chasing it now would cost
four runs to fix something that has not yet corrupted a number.

---

## 2026-09-26 — resumed after four days; six defects found before anything ran

Stopped 2026-09-22 21:50 part-way through D0's re-measurement (111 of 456
rollouts). Resumed today. Programme spend at restart, **measured**:
**$677.59** of the $1,500 cap — the sum of every session, sweep and benchmark row
under `cortex-eval/`, each counted once (`lab/bin/usage-guard spend`). D0's own
$155.45 predates the programme and is not in it.

`D0-bench` was restarted **on its own** while the rest was checked: it is
independent of everything below, and `bench.py` resumes from `results.jsonl`.
Before it ran, its arm fingerprints were saved; after `arms` rebuilt them they are
byte-identical (`none e7464384…`, `evolved eea21287…`), and `tasks.json` differs
only in its `prepared` timestamp — every task base is the same commit. The 111
rows from Sep 22 and the new ones are one measurement.

**R4's 446 of 456 is explained.** `runs/R4/excluded.json` lists exactly one
scenario, `HA6`, whose reference fix was invalid on R4's final code: one holdout
task × 2 arms × k=5 = the 10 missing rollouts. No other run excluded anything.

### What reading the remaining steps found

Everything left in the chain — gates, prune, structlog, Sonnet — had only ever run
as a rehearsal or a dry run. Reading it before an unattended day found six defects,
all now in `defects.json` (T16):

1. **The gate testbed was R1's, not C1's.** Built during a rehearsal before C1
   existed and reused by `--from C1`: H5 would have been measured on R1's
   repository and labelled C1. Its history gave it away — `cortex: evolve, round
   10`, and C1 never evolves. A testbed now records its source and is refused for
   any other; it was set aside (`cortex-eval/stale/`, not deleted) and rebuilt
   from C1.
2. **C1 has no baseline to read.** §7 screens placebos on "the four
   lowest-numbered tasks that fail at the testbed's baseline, measured once". C1
   has no sweeps, so the code fell back to "every task is fair game" — and a dry
   run *cached* that for the real run. On tasks that already pass a placebo cannot
   show a spurious gain, which would have biased the false-KEEP rate toward zero.
   The baseline is now measured: one confirm sweep over every task at k=3, reading
   only the **base** arm, which is always the empty harness. The first attempt used
   a truly inert candidate and **Cortex refused it** — "it could never load, so the
   sweep would measure nothing" — so the sweep is carried by a neutral note whose
   own arm is never read. Cost: 156 rollouts, once.
3. **A refused sweep would have been recorded as a result.** Nothing checked that a
   candidate's sweep had run; `cortex score` then prints the previous sweep's
   scores. Each sweep must now have written a file naming its own candidate.
4. **Costs were cumulative.** `.evolve/runs/` is never cleared, so each gate
   candidate would have been charged with every one before it, and the prune pass
   with R1's nine inherited sweeps (254 rollouts, $32.76).
5. **A usage outage would not have stopped anything.** See below.
6. `remeasure-d0` recorded exclusions it never applied (none this time).

### The usage guard

Every rollout runs on the operator's Claude login, and the standing instruction is
to stop and ask for a recharge if it runs out. Nothing did: `claude -p` fails in
seconds, `bench.py` wrote an INVALID row and moved on, a restart counted those
rows as done, and every caller's `|| true` swallowed the failure. The tail of the
programme would have raced through in minutes, each step earning its marker.

`lab/bin/usage-guard` now gates every paid step: the measured spend plus the
step's pre-registered reserve must fit under the cap, and a live call with the
step's **own** model must answer (the Sonnet study can meet a limit Haiku does
not). While a step runs, a watchdog counts rollouts and sessions that could not
run; at three, it probes, and if Claude does not answer it stops the step's whole
session. `bench.py` stops itself after five in a row and a restart re-measures
them. The Sonnet benchmark reserves the **whole rest** of its study at the price
its own pilot measured, so it cannot discover half-way that the second half does
not fit. Jev must actually answer before the scope replay: `cortex jev doctor`
exits 0 when Jev is merely off.

The outage signature was checked against the whole history first: it fires **0
times** in 437 sessions and ~5,000 rollouts. The failures that did happen — four
turn caps, one timeout, nine `reset_failed` sweep rows — are none of them an
agent that could not run.

### Later on 2026-09-26: three more, found while the gate testbed ran

- **D0R's export duplicated D0.** It exported D0R as a second `development` run from
  a copy of D0's repository and D0's own autopilot log: 26 sessions, 24 cycles,
  26 sweeps, 10 items and 984 sweep rollouts, twice. Re-exported as a
  **re-measurement** (`--kind remeasure --of D0 --bench-only`): 456 benchmark rows
  and nothing else. Brief §4.4 benchmarks "D0 re-measured on the expanded holdout"
  so that D0 is compared with R1…Rn like for like, and H13 now does: **D0 +42.5
  re-measured on the 30-task holdout (+50.0 on its own 15), replicates +55.0
  [+30.3, +76.4] — SUPPORTED** either way. The Sonnet benchmark would have done
  the same to R1 and exports bench-only too.
- **H14 would have passed trivially.** It counted an item as "changed" if any prune
  row named a model other than Haiku, whatever its verdict — and the Sonnet `/prune`
  step recorded no rows at all. It now follows the brief exactly: SUPPORTED if an
  item Haiku kept becomes removable under Sonnet, with the same harness's gain under
  each model (R1 against M1, not the pooled replicates) beside it.
- **structlog's tasks would all have been quarantined.** Cortex checks every task in
  a bare `git clone`, where structlog has no virtualenv and `python3` has no pytest.
  A test-tools-only Python now comes first on PATH, with `PYTHONPATH=src`, in the
  sessions and in `rollout_env`; setup proves it on a bare clone before the first
  session.

Every section of the analysis that had no real data yet — gates, prune, the model
change, structlog — was then run end to end on synthetic rows in a scratch copy.
It found two more (H15 had no interval; exact ties printed as "−0.0") and nothing
else: the planted edge cases each gave the verdict they should.

The gate baseline, measured: **22 of C1's 26 tasks fail with an empty harness**
(only 13, 14, 15, 23 pass every time). The placebos screen on 01–04, which pass
0, 1, 0 and 0 times in 3 — room for a spurious gain, which is the point.

### 18:47 — the machine rebooted mid-gates; resumed at 18:49

Uptime read one minute at 18:48: the chain was killed, not failed, part-way
through `billing-money`'s confirm sweep (it had passed its screen). By then **25 of
29 candidates were recorded, every one matching its pre-registered answer: all 5
harmful and all 20 placebos KILLED — no false KEEP.** D0 verified unchanged, the
frozen Cortex still first on every path. `cortex clean` (results kept) removed the
stale sandboxes; the partial confirm sweep stays in `.evolve/runs/` as a record —
it is not charged to the candidate's re-measurement, which counts only the sweep
files it adds. The chain resumed on its markers; the gate testbed skips the 25 and
measures `billing-money` from the start.

### 19:26 — the gate testbed finished: 27 of 29 match

All **20 placebos and all 5 harmful candidates KILLED — no false KEEP.** Of the four
known-good items, the two that can load passively were KEPT on clean confirms
(`billing-money`, a rule: +13 net runs; `complete-the-exporter`, a gated skill: +4).
The two **always-on skills** — `changelog-for-user-visible-changes` and
`use-shop-clock` — were KILLED at screen with **fired 0**: in eight rollouts each the
agent never invoked them, and a candidate that never loaded cannot be credited
(gate 5). `use-shop-clock` even showed a +0.5 screen gain it could not have caused.
Skill detection is not the cause: the gated skill fired. This is the programme's
recurring finding in its cleanest form — a rule is loaded when its files are read; a
skill must be chosen, and an always-on one often is not.

### 20:42 — Claude stopped answering; the guard stopped the prune step; resumed 23:31

Part-way through the prune pass's third sweep (`changelog-requirement`), rollouts
began failing with `agent_rc_1` and two probes a minute apart got **no answer in
180 s** — a hang, not a usage-limit message. The watchdog stopped the step at 20:42
with 5 failures counted (19 in the sweep by then), and did **not** mark it done: the
first use of the guard, and it did what it was built for. Nothing wrong was
recorded as a result. By 23:30 the probe answered again.

State at the stop: plan APPROVED; `exporter-checklist` and `billing-helpers` — R1's
own items — decided **REJECT** (removing them costs pass rate: they keep their
place, as expected); item 3's sweep cut off without its `done` event; item 4
pending. Cortex treats a sweep as running until it sees `done` or `truncated`, so
the dead sweep's file was moved to `.evolve/runs-interrupted/` (kept, and still
counted as spend) and `cortex prune next` then offered to launch item 3 afresh.
/prune chose R1's four items and none of the planted ones; the step's second pass
addresses those.

### 00:18 — the prune experiment finished: 6 of 8, nothing never-fired deleted

666 rollouts, $102.90. R1's four own items: all **REJECT** — removing any of them
costs pass rate, so each keeps its place, as pre-registered. The first pass chose
only those four; the second pass addressed the four planted items:

| planted | pre-registered | Cortex |
|---|---|---|
| `before-reporting-a-change-complete` (placebo, fires) | ACCEPT | **ACCEPT** — deleted |
| `after-finishing-an-edit` (placebo, fires) | ACCEPT | **REJECT** — kept: a genuine miss |
| `vendor-bundle-conventions` (paths match nothing) | SKIPPED | **SKIPPED** — "no task touches its paths" |
| `rotate-a-signing-key` (never fires) | UNMEASURED | **SKIPPED** — "never loaded — a removal can only be UNMEASURED" |

The script had recorded the last three as REJECT ("still live") — corrected from
Cortex's own `prune-plan.json`, nothing re-run (T16). Matching is kept strict, so
`rotate-a-signing-key` counts as a mismatch although its substance is exactly what
H10 asks: **no item that never fired was deleted**. H10 as pre-registered ("every
planted item matches") is therefore not supported, on one real miss and one label.

### 00:25 — structlog stopped after one session: its lint oracle was contaminated

The first session showed it: the agent's change passed the tests and failed lint
three times over errors in files it never touched ("54 linting errors: missing
copyright headers…"). Checked directly: structlog's own upstream commits fail
today's ruff with 51–56 errors each, and pass cleanly under the ruff the project
pinned at each commit. The chain was stopped, the oracle switched to the pinned
ruff everywhere (DEVIATIONS D-11), and the run restarted from scratch. The
environment fix from earlier held: the harvested check ran in a bare clone and
failed/passed as it should — it was quarantined for the lint contamination alone.

### 01:10 — structlog: 18/20 vs 17/20, on identical harnesses

The benchmark: `evolved` 18/20, `none` 17/20, 0 invalid. The loop kept nothing
(D-12), so this is an A/A: the two arms carry the same `CLAUDE.md` and no item. The
export first reported them as different — the bench's arm builder wrote the base
`CLAUDE.md` with one extra trailing newline (556 vs 555 bytes). The identity check now
compares content, the builder no longer adds the line, and the export was re-run:
`harness_identical: true`. H15 therefore reads INCONCLUSIVE, with the one-rollout
difference printed as the noise it is.

### 02:32 — the chain finished; Sonnet, the judge, and the package

- **Sonnet (H14).** The pilot measured $0.23 a rollout; the rest of the study was
  reserved at that price and fit. The same R1 harness gains **+66.7 under Haiku and
  +5.6 [−2.8, +13.9] under Sonnet**: Sonnet passes 91 % of the holdout with no harness
  at all. `/prune` under Sonnet — Cortex detected the model change itself and tested
  every item — found **two of R1's four items no longer needed**
  (`exporter-checklist`, `billing-helpers`), both of which Haiku's pass had kept.
  The prune step failed once on its first command (it ran in the wrong directory —
  it had never run before); fixed, restarted, clean.
- **Scoring the judge.** The first replay ran with no judge at all: `scope-replay`
  defaults Jev off and runs in a clone that cannot find the key. The row check caught
  it (33 of 36 unjudged) and stopped the step; re-run with the judge on, all 36 judged.
- **The report** was then read as a stranger would. Its spend line summed only the
  exported runs ($942 shown, $1,175 spent), two sections said arms "had not run" that
  had, and the task count and built-in-skills rate had read structlog's and Sonnet's
  rows as the lab's — all fixed, all computed from the rows.
- **The package.** `manifest.json` written; personal paths scrubbed from every
  shipped row and report page, the scorecard byte-identical afterwards; a clean
  clone with a fresh environment rebuilt all 19 figures and 20 tables in 49 s, with
  a scorecard identical to the committed one.

**Final: $1,174.96 of the $1,500 cap, 6,462 rollouts, 61 defects catalogued. D0
unchanged.**

---

## 2026-09-29 — the final report

The report, the summary, the scorecard, the tables and the figures were generated again
from the same rows, with two extracts added beside them: the prune test's sweeps, and what
each rollout read, from Claude Code's own session records. The loop's verdicts in them are `score.sh`'s rules applied to the
recorded rollouts (`analysis/rescore.py`, which agrees with `score.sh` on every sweep of
the evaluation runs), with the journal's record beside them where the two differ.

Claude Code keeps its own record of every headless session. Matched to the rows, those
records cover 7,433 rollouts (`data/transcripts.jsonl`), and they show what a rollout could
read through git that its harness did not give it (REPORT §16). They also show one prune
sweep that no file on disk records: the `/prune` agent stopped the exporter-checklist
removal sweep before its last rollout was recorded, deleted its file and ran it again.
Claude Code's records hold all 150 of its rollouts; they cost $20.79, now counted. The
readings of H0, H5 and H16 this report uses are `DEVIATIONS.md` D-22.

**Final: $1,195.75 of the $1,500 cap. D0 unchanged.**

