---
description: One evolution cycle - find the recurring problem, propose one fix, measure it, keep or kill
---

# /evolve — one cycle, one change, measured

You are the **experimenter**, not the subject. You propose a change, you
measure it in an isolated clone, and you keep it only if the numbers say so.

**The rule that makes this work:** a change must help something **and** break
nothing. Not "help on average" — break nothing. A change that wins one task and
quietly loses another is how skill folders rot.

**One change per cycle.** Test two and you cannot tell which one moved the score.

---

## Step 0 — WHERE AM I?

This command spans several turns. Cortex works out the phase from the files —
do not work it out yourself from the newest results: they may belong to a cycle
that has already ended.

```bash
cortex phase
```

| It prints | Go to |
|---|---|
| `phase A` | **Phase A** — a fresh cycle. Results already in `.evolve/runs/` belong to finished cycles: ignore them |
| `phase B` | **Phase B** — the candidate is written and was never swept |
| `phase C` | **Phase C** — its sweep is running: poll |
| `phase relaunch` | its sweep died (killed, crashed): launch the **same** sweep again — same `--phase`, `--tasks`, `--k` as printed — dry run first |
| `phase D` | **Phase D** — its sweep ended. `sweep screen` → D2; `sweep confirm` or `recheck` → D3 |
| `phase prune` | a `/prune` sweep or replacement owns the lab: **stop**, say so, try later |
| `phase error` | more than one candidate: stop and tell the user |

`cortex score` reads the newest results file unless you pass a path; in Phase C
and D, pass the file `cortex phase` printed.

---

# PHASE A — prepare

## A1. Preflight

```bash
cortex preflight
```

Zero tokens, pure shell. For each task it checks the broken state **fails** and
the fixed state **passes**. Anything else is quarantined to `.evolve/tasks/_broken/`.

*Why:* tasks rot. The repo moves on, patches stop applying, a check that used to
be red goes green for unrelated reasons. Evolving against a rotten task is
optimising noise, and you would never know.

Exit code 2 = fewer than `min_valid_tasks` survived. **Stop the cycle.** Say:
`only N valid tasks — run /harvest more before evolving`.

Then check the routing — every skill and rule, which tier each is in, what is
always in context:

```bash
cortex skills
```

- `error:` lines (exit 1) — a name that is both a skill and a rule, or a symlink
  pointing outside the repository. **Stop the cycle** and tell the user; no
  sweep can be trusted until it is fixed.
- `DEAD glob` warnings — a path-gated skill or rule whose `paths` match no file
  any more (usually a renamed directory). It can never load, so it cannot be
  measured. If the warning prints `repair: '<old>' -> '<new>'`, apply exactly
  that edit to its `paths`, run `cortex skills` again to see it live, and
  journal it as `kind: path-repair`. Any other change to a live item is a
  `/prune` operation.
- Other warnings: report them in one line and continue.

## A2. Baseline — still valid?

```bash
cat .evolve/baseline.json 2>/dev/null
cortex status | grep '^harness'
```

```bash
jq -r '{model, baseline_max_age_days, lookback_days, min_theme_occurrences,
        transcripts_dir, min_valid_tasks}' .evolve/config.json
```

Reuse it **only if all four hold**:
- same `model` as today,
- newer than `baseline_max_age_days`,
- `hash_v` is `2`,
- `skills_hash` equals the `harness` line printed by `cortex status` (it covers
  skills, rules and `harness_files`, paths included).

`cortex baseline --model <id>` writes all of them. `cortex score` alone does not —
it emits only the arithmetic. A valid baseline's `failing` field lists the tasks
the live harness does not solve every time.

No valid baseline (the first cycle, or a stale one) blocks nothing: the screen
measures its tasks under the current harness anyway (its `base` arm), and the
confirm re-measures every task. Tasks harvested after the baseline have never
been measured — treat them as possibly failing.

*Why the model check:* a new model may already do what an old skill teaches. A
baseline measured on the previous model silently flatters every skill you own.

## A3. Find the ONE theme

Read, in this order (`lookback_days` and `transcripts_dir` come from the config
above — do not assume 7 days or a default path):

```bash
tail -40 .evolve/lessons.md
ls .evolve/graveyard/          # ideas already tried and killed — do not repeat
tail -60 .evolve/journal.md    # what past cycles concluded
```

Then count what recurs, instead of remembering it:

```bash
cortex themes
```

It reports one row per theme with a count, and marks the ones that clear
`min_theme_occurrences`. **Read its `source:` line and follow the matching
branch — they are not the same amount of evidence:**

- **`source: census`** — every lesson and every transcript of the window was
  classified and counted. The counts are complete: use them, and skip the
  transcript reading below.
- **`source: areas (jev off)`** — the counts cover only the lessons that named a
  task, grouped by that task's `area:` line. Treat them as a **floor**, and read
  the transcripts as before:

  ```bash
  cortex harness transcripts
  ```

  Look for repeated corrections, tool denials and retry loops. Read **only** those
  files: `transcripts_dir` holds every project on this machine, and other projects'
  sessions are none of this cycle's business.

Either way, also read the **failing** tasks from the baseline.

Look for **one** thing that recurs. Requirements:

- appears **`min_theme_occurrences`** or more times in lessons, **or**
- explains **2 or more** currently-failing tasks.

Write down the theme's tasks: the `task NN` ids on its lesson lines, plus any
task whose `notes.md` describes the same problem. Those are what the screen runs.

If nothing clears that bar: run `cortex cycle BARREN` (it writes the journal's
`nothing to learn` line itself) and **STOP**.
This should happen often. A cycle that changes nothing is a correct outcome.

## A4. Choose the layer and the tier — say it out loud

Not everything is a skill, and not every skill should sit in context on every
turn. Claude Code loads things in tiers; pick the narrowest one that is still
loaded **before** the mistake happens. State your reasoning in chat.

| The problem is… | Put it in | Loaded |
|---|---|---|
| a short hard rule for one area, and the fixes **edit** at least one existing file there | **rule** — `RULE.md` + `paths:` | injected in full when a matching file is **Read** — and an Edit always Reads the file first. No choice by the model |
| a procedure for an area where the fixes only **create** new files | **path-gated skill** — `SKILL.md` + `paths:` | offered when a matching file is Read or Written; the model must then **choose** to invoke it |
| a *moment* ("before reporting done", "before committing") with no area | **always-on skill** — `SKILL.md`, no `paths` | description every turn; the model must choose it |
| a fact an agent breaks during **unrelated** work | root **CLAUDE.md** | every turn — ration it |
| a command I always approve | **settings.json** permission | — |
| a rule that must ALWAYS run, no judgement | **hook** | — |
| a capability I lack entirely | **tool / MCP server** | — |

**A theme a live skill or rule already covers is not a new theme.** If tasks in its
area still fail, that is evidence about the live item — its trigger, its wording, its
tier — and `/prune` Step 5 is what tests a change to it (as a **replacement**:
`--candidate <new> --replace <live>`). Adding a second item that says the same thing
leaves both of them loading. `cortex skills --candidate <name>` warns when a live
item covers exactly the same files; if that is your theme, stop and leave it to
`/prune`, and look for a theme nothing covers yet. If you sweep a replacement
anyway, its verdict is `/prune`'s to execute: write it in the journal and stop —
**never bury a live item from `/evolve`**, and never read a *screen* as a decision
about one (a screen of a replacement says CONFIRM or KILL, never ACCEPT).

Evidence decides the area: the files the failing tasks' fixes touched
(`grep '^--- a/\|^+++ b/' .evolve/tasks/<id>/fix.patch`). If they cluster in one
directory, the tier is a rule or a path-gated skill; if they are all over, it is a
moment.

**A skill is only offered; a rule is injected.** Measured over 486 recorded
rollouts (Haiku 4.5), counting only the runs where the item was actually visible:

| Tier | Runs | Visible | Fired | **Fired given visible** |
|---|---|---|---|---|
| rule | 410 | 62.9% | 62.9% | **100.0%** |
| path-gated skill | 66 | 72.7% | 19.7% | **27.1%** |
| always-on skill | 10 | 100% | 0% | **0.0%** |

**A rule that is visible always fires.** That is the argument for a rule — and it
is also what makes an over-scoped rule the most destructive object in the system:
it fires in every task it reaches, including the ones it is not about, and gate 3
charges you for each one. In the same recorded data, three candidates that were
injected into tasks they were not about cost 694 rollouts and $77.70 and landed
nothing. Breadth is not the danger; **irrelevant** breadth is. `cortex scope` in
A5 is what measures it before you pay.

Within a tier, a skill is invoked when its description names **the task the agent
is doing**, and rarely when it names a **side duty** of that task ("When
implementing a new exporter plugin…" was invoked in 5 of 6 visible rollouts;
"Before finishing changes to shop/ code, verify CHANGELOG.md was updated" in 1 of
18). So:
- a side duty tied to an area — a changelog line, a docs row, a registry entry, a
  house helper to use — is a **rule** on that area, as long as the fixes edit an
  existing file there (its `paths` must match that file);
- a procedure for the task itself can be a skill, with a description that names
  the task ("When adding a new exporter…"), never the duty ("verify X was updated").

If you cannot justify the layer in one sentence, you have picked the wrong one.

**A second opinion, when one is available.** This is optional and never decides
anything on its own:

```bash
cortex jev tier --theme "<what recurs, in one sentence>" --files "<the paths the fixes touch>"
```

- **exit 0** — it picked a layer with enough confidence to be worth hearing. Weigh
  it against the table above and say which you chose and why. It is one input, not
  a verdict: a wrong pick is killed by the gates, which is the only reason it is
  safe to ask at all.
- **exit 3** — no answer, or below `jev.confidence_floor`, or Jev is off. Decide it
  yourself from the table, exactly as you would have anyway. A low-confidence pick
  is not a pick, and this is the normal keyless outcome.

**If the layer is a rule, run `cortex scope` on the draft `paths` in this same
turn** (A5 shows how). A rule fires in every task it reaches; seeing that number
*before* writing the candidate is the feedback the worst theme in the recorded
history never got, four cycles running.

Skills and rules go through the sweep below. For the other layers, make the
change, write it in the journal, and stop — there is nothing to A/B.

## A5. Write the candidate

A skill:

```
.evolve/candidate/<name>/SKILL.md
```

```markdown
---
name: <kebab-case>
description: <when this should fire — this line is what triggers it>
paths:                        # ONLY for a path-gated skill; omit for a moment
  - "<dir>/**"
---

<the procedure, as numbered steps>
```

A rule (one file, nothing else in the directory):

```
.evolve/candidate/<name>/RULE.md
```

```markdown
---
paths:
  - "<dir>/**"
---

# <area>
- NEVER <the plausible wrong move>. <what to do instead, with the path>.
```

**Not** in `.claude/`. It is not live and must not affect this session. On KEEP,
`cortex promote` puts a SKILL.md in `.claude/skills/<name>/` and a RULE.md at
`.claude/rules/<name>.md`.

Globs: take the directory from the failing tasks' `fix.patch` — `--- a/` paths
for a rule (the file must exist before the fix to be Read), `a/` or `b/` for a
skill. Prefer the narrowest directory that covers them. Always quote globs
(`"src/**"`): an unquoted `*` is YAML syntax and the item silently never loads.
How Claude Code matches them: a glob without `/` (`"*.sql"`) matches at any
depth; a glob with `/` is anchored at the repo root; a glob that matches a
**directory** covers everything below it (`"db/migrations"` or `"db/*"` load for
`db/migrations/0042.py`), while `"db/*.py"` does not reach into sub-directories.

Then check it — zero tokens:

```bash
cortex skills --candidate <name> --tasks "<failing ids>"
```

Exit 1 = fix what the `error:` lines say before launching anything. In
particular `could never load` means no task in that set touches a file matching
`paths`: every rollout would measure nothing.

Then check its **scope** — what it will be injected into across the whole suite,
which is what the confirm will actually charge you for:

```bash
cortex scope --candidate <name>
```

It always prints the deterministic half (`injected into N of M tasks`). With Jev
it also prints how many of those tasks are **about** the candidate's subject, and
warns below `jev.scope.relevance_floor`; with Jev off it prints
`relevance: unavailable` and you carry on — that line is not an error and never
blocks anything.

Read the warning as a question about `paths`, not about the idea. A rule injected
into 21 tasks it is not about carries 21 chances to break something gate 3 will
charge you for, and the usual fix is a narrower glob, which the command suggests
when it can compute one. **Nothing here blocks the sweep and no gate reads it** —
you decide, and the measurement still rules. It is the same category as the
existing `DEAD glob` warning.

For a **skill** it also predicts, per task, whether an agent would invoke it from
its description alone. That is advisory and thin evidence: use it to reword a
description before paying for a screen, never as a reason to skip one.

Rules:
- **Additive only.** Never edit an existing skill or rule in the same cycle as
  adding one. Changing a live item's tier or `paths` is a `/prune` operation.
- **A new name**, lowercase letters, digits and `-` only. If a live skill or
  rule already has it, the sweep refuses the candidate: rewriting a live item is
  a `/prune` operation (`--replace`). If the graveyard has it, the sweep refuses
  too: a revised version of a killed idea gets its own name (`<name>-v2`).
- For a skill, the `description` matters more than the body; for a gated skill
  or a rule, the `paths` matter as much. A perfect skill that never loads is
  worse than no skill.

The writing contract — a skill or rule **constrains an agent about to act**; it
is not documentation:
- **Prohibitions first**: what looks right and is wrong. The agent's default
  already covers the rest.
- **Checkable by reading a diff.** "Handle errors properly" is a mood, not a rule.
- **Anchored to real paths** that exist today; examples are complete copy
  targets, no `...` or "your logic here".
- **No** framework defaults, rationale essays, in-flight process (branch names,
  "we are migrating"), or anything copied from elsewhere in the repo — point at it.
- Under ~200 lines.

---

# PHASE B — launch the sweep

## B1. Screen first: only the theme's tasks

Cheap filter. If the candidate does not help the tasks it was written for,
nothing else matters and you stop without paying for the regression check.

`<failing ids>` below = the theme's tasks from A3, minus any the baseline shows
the live harness already solves every time. If that is more than
`max_runs_per_cycle / (2 × k.screen)` tasks, keep the ones with the most recent
lessons.

First a dry run, in the **foreground** — it runs every check that can refuse
the sweep (names, CLI version, reachability, budget, lock) and spends nothing:

```bash
cortex sweep --candidate <name> --tasks "<failing ids>" --phase screen --k 2 --dry-run
```

`sweep: REFUSED: …` → report the reason and **stop**. Do not launch, and do not
poll: `cortex score` would read the *previous* sweep's results as if they were
this one's. The usual causes: `needs N rollouts but max_runs_per_cycle is M`
(ask the user to raise it, or screen fewer tasks), `could never load` (fix
`paths`), a CLI older than `min_claude_version` (update Claude Code).

`sweep: OK — N rollouts, W at a time …` → launch it for real, in the **background**.
It takes about N ÷ W minutes (a rollout is about a minute; W run at once). Use
`--detach`, not `nohup … &`: a job started with `&` dies with the shell that
started it, and yours ends when this session does. `--detach` repeats every check,
starts the sweep in a process session of its own, and returns at once:

```bash
cortex sweep --candidate <name> --tasks "<failing ids>" --phase screen --k 2 --detach
```

Progress is in `.evolve/runs/sweep.log`.

## B2. Report and sleep

```
theme:     <one line> (N lessons, M failing tasks)
layer:     <always-on skill | path-gated skill | rule> — <why not the others>
candidate: <name>  paths: <globs, or "none">
screening: <k> runs x <n> failing tasks, in background
back in ~<N ÷ W> min
```

Then schedule a wake-up that far out (at least 300 s) and end the turn.

---

# PHASE C — poll

```bash
cortex score | jq -c '{finished,truncated,running,scorable,rollouts,invalid}'
```

- `finished:false, running:false` → the sweep **died**: nothing will ever finish
  it. Launch the same sweep again (dry run first) and poll that one.
- `finished:false, truncated:false` → still running. Report `N rollouts so far`,
  sleep again. One line; this is a quiet tick.
- `truncated:true` → the sweep hit `max_runs_per_cycle`. **Do not score it.**
  Go to Phase D and follow the `scorable:false` branch.
- `finished:true` → Phase D.

---

# PHASE D — decide

## D1. Read the numbers

```bash
cortex score
```

```json
{ "scorable": true, "blocked_because": [],
  "invalid": 0, "invalid_rate": 0.0, "unmeasured": [],
  "per_task": [...], "gain": 1.34, "regression": 0.0,
  "net": 1.34, "worst_drop": 0.0, "protected_broken": [] }
```

### Read `scorable` FIRST

```
scorable: false  ->  STOP. Decide nothing. Read blocked_because, fix the cause,
                     re-run the sweep. A verdict from partial or infra-poisoned
                     data looks exactly like a real one in the journal.
```

`blocked_because` names the cause: a truncated sweep, an invalid-rollout rate
over `max_invalid_rate`, tasks not measured under both variants at full `k`,
**firing unknown** (a rollout's output could not be read, so whether the
candidate loaded is unknown — never treat that as "it did not"), or the Claude
Code CLI changing mid-sweep.

**`invalid` is not `fail`.** A rollout is invalid when the agent process died for
reasons that are not about capability — auth expiry, rate limit, a 5xx, or a
sandbox that could not be reset. Those are excluded from the scores rather than
counted as failures, because counting them would make an API outage look like a
regression (or, if it lands in the other arm, like a gain).

## D2. If this was the SCREEN

**A screen never keeps a candidate.** It only decides whether the confirm is
worth paying for, and `cortex score` says which: its `verdict` for a screen is
`CONFIRM`, `KILL` or `RERUN` — never `KEEP`. `cortex promote` refuses a candidate
that no confirm has kept.

```bash
cortex score | jq -c '{phase, verdict, gain, candidate_fired_runs, verdict_because}'
```

```
verdict KILL,  gain <= 0  →  KILL now. Do not pay for the confirm phase:

              cortex bury <name> --from candidate --why "screen: gain <= 0"

verdict KILL,  gain > 0 but candidate_fired_runs == 0
           →  KILL now too (gate 5): the candidate never loaded, so the gain
              was not its doing, and a confirm sweep could only KILL it:

              cortex bury <name> --from candidate --why "screen: never loaded — <notes>"

verdict CONFIRM  (gain > 0, candidate_fired_runs > 0)
           →  the candidate helps something. Now find out what it costs.
              Dry-run the CONFIRM sweep over ALL tasks at full k, and
              launch it only on `sweep: OK` (same rule as B1):

              cortex sweep --candidate <name> --phase confirm --dry-run
              cortex sweep --candidate <name> --phase confirm --detach

              then sleep and return to Phase C.
```

*Why two stages:* most candidates are bad. Killing them on a screen of a few
rollouts (failing tasks only, k=2) instead of a confirm over every task is most
of your budget saved.

## D3. If this was the CONFIRM (or its RECHECK) — read the verdict

**The gates are applied by `cortex score`, not by you.** Thresholds a model
applies by hand get rounded, misread or forgotten; thresholds the scorer applies
cannot be. Your job is to report the verdict and act on it, not to recompute it.

```bash
cortex score | jq -c '{verdict, verdict_because, net_runs, gates_failed}'
```

```
verdict: "KEEP"     all gates passed
verdict: "KILL"     gates_failed says which, and why
verdict: "RERUN"    the data was never trustworthy — see blocked_because
verdict: "RECHECK"  the ONLY failures are per-task regressions (gate 2 / 3) on
                    recheck_tasks — maybe one unlucky run, maybe real
```

**RECHECK is not a KILL: do not bury.** At k=3 one lost run on a task that went
3/3 in base looks exactly like a broken task, and over a suite of fifteen tasks
that happens to good candidates by chance. Re-measure just those tasks — dry run
first, then launch, then return to Phase C:

```bash
cortex sweep --candidate <name> --tasks "<recheck_tasks>" --phase recheck --dry-run
cortex sweep --candidate <name> --tasks "<recheck_tasks>" --phase recheck --detach
```

`cortex score` then pairs the recheck with its confirm and gives the final
verdict: the regression must fail the same gate again on the fresh runs to
KILL; if it does not, the candidate is KEPT.

Also read `notes`, together with `candidate_visible_runs` and
`candidate_fired_runs`. `the candidate never fired in any rollout` means the
body was never tested at all; the rest of the note says which half to fix:

```
it never became visible          a path-gated skill whose paths never matched a file
                                 the agent read or wrote       -> fix `paths`
visible in N rollout(s) but      it was offered and not chosen -> if the tasks' fixes
never invoked                                                     edit an existing file in its
                                                                  area, make it a RULE (a new
                                                                  name); else fix `description`
no rollout read a matching file  a rule                        -> fix `paths`, or harvest
                                                                  a task that reads that area
```

Say which in the journal: next time the fix is the trigger, not the procedure.

`task(s) NN never passed in any rollout of either arm` → put it in the D6 report,
word for word. Either the task is too hard for the agent, or its `check.sh` accepts
only the harvested fix (its class names, its wording: /harvest rule 6), and then no
candidate can ever gain there. The user reads those checks; you do not edit tasks.

For reference, the gates it applied (from `config.yaml`, echoed in `thresholds`):

```
0. scorable                              is this data trustworthy AT ALL?
1. gain > 0                              did it win anything?
2. worst_drop <= regression_tolerance    did any single task collapse?
3. protected_broken == []                is the protected set intact?
4. net * k >= min_net_runs               is it more than one lucky run?
5. candidate_fired_runs > 0              did the candidate load at all?
```

Gate 3 is the preserve-and-extend contract: tasks the current harness solves
perfectly are the protected set, and nothing may cost you those. Gate 4 is the
noise guard — a net of one run is a coin flip. Gate 5 refuses a "win" from a
candidate that never loaded: whatever moved the score, it was not the candidate.

Gates 1–4 read only **exposed** tasks: those where the candidate entered the
agent's context in at least one cand rollout. On the others (listed in
`unexposed`) both arms ran the same harness, so their differences are noise. An
always-on skill is in context everywhere; a gated skill or a rule only where the
agent touched a matching file.

**If `verdict` is `RERUN`, do not bury the candidate.** It was never measured;
a graveyard entry would be a verdict you did not earn. Fix the cause named in
`blocked_because` and sweep again. The usual causes and what they ask for:

```
the sweep recorded N of M rollouts      its job queue broke (a full disk under
                                        sandbox_root, a `cortex clean` mid-sweep)
planned task(s) with no rollout          same: some tasks never ran
the machine was oversubscribed           the rollouts ran several times slower than
                                         alone: raise measurement.parallel.cpus_per_rollout
                                         (the line suggests a value) or lower rollouts
invalid rate … timeout_under_load        agents ran out of time on a loaded machine;
                                         same fix, then sweep again
firing unknown / CLI changed mid-sweep   as before
```

## D4. Execute

**KEEP** (only a confirm, or its recheck, can say it):
```bash
cortex promote <name>                                 # SKILL.md -> .claude/skills/, RULE.md -> .claude/rules/
cortex skills                                         # the routing table, with the new item in it
cortex baseline --model <the model you are running>   # new score to beat
cortex clean                                          # sandboxes only; keeps evidence
```

**KILL:**
```bash
cortex bury <name> --from candidate --why "<gates_failed, in one line>"
cortex clean
```

Keep the graveyard, so that Phase A3 can see this idea was already tried and not
propose it again. `cortex bury` never overwrites: a second idea with the same
name gets its own dated entry, with its reason in `BURIED.md`.

## D5. Journal, then record the cycle — always, kept or killed

Write the journal entry below first. Then record the cycle:
`cortex cycle` refuses a KEEP or KILL whose entry is not in the journal yet.

```bash
cortex cycle KEEP <name>     # or KILL <name>
```

**One cycle per `/evolve`.** After recording it, report (D6) and stop. A killed
idea is retried in the next `/evolve`, which reads its reason in the graveyard
and the journal: "never invoked" → a better `description`, or another tier.

This maintains the barren-cycle counter. It exits non-zero once
`stop_after_barren_cycles` is reached: **stop the loop and tell the user**
rather than scheduling another week of spending.



If Jev was used anywhere in this cycle, add its one line to the entry too:

```bash
cortex jev journal --candidate <name>
```

Paste what it prints **as an indented detail line inside the entry**. It never
begins with `## `, and it must not be made to: `cortex cycle` counts `## `
headings to refuse a cycle whose entry was not written, and a `jev:` line that
looked like a heading would let a cycle through that recorded nothing. Exit 3
means there is nothing to say — write the entry without the line, which is the
normal keyless case. "Jev was unavailable" and "Jev agreed" must not look the same
a month from now, so when it prints `jev: fallback`, keep that too.

```markdown
## YYYY-MM-DD  <candidate name>

kind:       skill | gated-skill | rule
paths:      <globs, or "none">
theme:      <what recurred, and how many times>
layer:      skill  (hook rejected: <why>)
screen:     gain +1.34 on tasks 02, 04
confirm:    gain +1.34 | regression 0.00 | worst_drop 0.00 | net +1.34
            jev: theme=exporters · tier=rule conf=0.84 · scope 100% (3/3 tasks) · model=jev-1.13.0
recheck:    (only if asked) task 05: confirm 100%->67%, recheck 100%->100% — noise
protected:  task 01 held at 3/3
DECISION:   KEEP
suite:      1.33 -> 2.67
```

The journal is the only durable record of *why* the skills folder looks the way
it does. Six months from now it is the difference between a curated toolkit and a
pile of files nobody dares delete.

## D6. Report

```
KEEP verify-before-done
suite 1.33 -> 2.67   task 01 held 3/3, nothing regressed
task 09 never passed in either arm: read its check.sh (/harvest rule 6)   ← only when score said so
next cycle in 7 days
```

---

# Guards — stop yourself

| Condition | Action |
|---|---|
| fewer than `min_valid_tasks` valid | stop — harvest more |
| no theme with 3+ occurrences | stop — `nothing to learn` |
| `max_runs_per_cycle` hit | stop, judge on partial data, note it |
| `cortex cycle` exits non-zero | barren streak hit the limit — stop, tell the user |
| any rollout needs an interactive permission | stop — the sweep is unattended |

The last one matters. A headless rollout that hits a permission prompt hangs
until the timeout and scores a false FAIL, poisoning the measurement.

---

# Never

- Never run the sweep in the user's working copy. The sandbox clone only.
- Never load the candidate skill into **this** session. You are the experimenter.
- Never keep a change you did not measure.
- Never test two changes in one cycle.
- Never let a timeout count as anything but a failure.
