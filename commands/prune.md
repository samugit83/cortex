---
description: Monthly and after every model upgrade - measure what removing a skill costs, delete only what costs nothing
---

# /prune — the delete pass

Every **always-on** skill's `description` sits in the model's context on **every
turn of every session**, forever. Forty of them is not a richer toolkit; it is a
permanent tax plus forty descriptions competing to trigger. Path-gated skills
and rules cost nothing until Claude touches a matching file — so the other half
of this pass is *narrowing*: moving what only matters in one area out of the
always-on tier.

A benchmark does not pay a context cost. **You do.** Deletion is the half of this
system that keeps the folder honest.

**The rule:** a skill is deleted only when a measurement shows that removing it
costs nothing. Never because it has not been used lately, never on a hunch, and
never when the task suite cannot see what the skill does.

**The user decides what gets spent.** A pass is a *plan* — which items, on which
tasks, how many rollouts, how long, how many tokens, what cost — and **nothing
runs until the user approves it**. `cortex prune next` refuses to hand you a
sweep before that.

Run this monthly, and **always after a model upgrade**. It spans several turns:
each measurement is a background sweep of minutes to tens of minutes (its
rollouts run several at once — `measurement.parallel`).

---

## Step 0 — Where am I?

```bash
cortex prune status
cortex prune next --json 2>/dev/null
```

| `cortex prune status` says | Go to |
|---|---|
| `no prune plan`, or status `DONE` / `CANCELLED` | a fresh pass → **Step 1** |
| status `PROPOSED` | the plan is waiting for the user. If the user has **just approved it** in this conversation, run `cortex prune approve` and go to **Step 3**. Otherwise show the plan again (`cortex prune status`), ask for approval, and **stop** |
| status `APPROVED` — read `next --json` | `"sweep": null` → **Step 3** (launch). `"finished": false` → **Step 3** (poll). `"finished": true` → **Step 4** (decide) |
| status `APPROVED` and `next` says `nothing left to test` | **Step 6** |

---

## Step 1 — Preflight, the model check, the routing, the usage

```bash
cortex preflight
cortex status
```

Preflight: you need a valid task suite before you can safely remove anything.
Exit code 2 means too few valid tasks: **stop** and say `run /harvest more first`.

`cortex status` prints the `model` rollouts are pinned to. Compare it with the
model **you** are running on right now:

- **Pinned to a different model** → **stop.** Every measurement would run on the
  old model, so "the new model already does this" cannot show up. Tell the user
  to set `baseline.model` in `.evolve/config.yaml` to the model they use now,
  then run `cortex config`.
- **Not pinned** → rollouts use the CLI default, and a model change cannot be
  detected. Say so in one line and continue.
- **Same model** → continue.

Then the routing:

```bash
cortex skills
```

- `error:` (exit 1) — a name that is both a skill and a rule, or a symlink that
  leaves the repository or dangles. **Stop**; nothing can be measured until it
  is fixed.
- `DEAD glob` — an item whose `paths` match nothing any more. It has never had a
  chance to load, so it is **not** "unused" and is never buried for that. If the
  warning prints `repair: '<old>' -> '<new>'`, apply exactly that edit, run
  `cortex skills` to see it live, and journal it as `kind: path-repair`.
  Otherwise report it to the user.

Then the usage — how each item was used in the user's real sessions over the
last `prune.usage_days`, and which tasks can measure it:

```bash
cortex usage
```

It is **evidence for choosing, never a reason to delete.** A skill for something
that happens twice a year shows zero uses between the two times and is exactly
the one that matters when it happens. Read its hints:

| Hint | What it means for this pass |
|---|---|
| `used, but no task can load it: the suite is blind here` | do **not** test it — it can only come out UNMEASURED. Tell the user which area to `/harvest` a task from |
| `no use, no task: a removal can only come out UNMEASURED` | do not test it. It stays |
| `narrowing candidate: N% of its use is in <folder>` | a Step 5 candidate: the same skill, gated to that folder |
| `manual: only you invoke it` | nothing to measure |

---

## Step 2 — Plan the pass, show it, and wait for approval

```bash
cortex prune plan
```

- **It answers `MODEL UPGRADE`** → the pinned model changed since the last pass
  (or since the baseline). The plan already holds **every** skill and rule,
  biggest always-on context first; there is no maximum. Go to "Show it".
- **It asks you to choose** → a routine pass. Choose **at most `prune.max_items`**
  items (the command enforces it), the ones you have most reason to doubt:
  - ones that overlap another (Step 5);
  - ones teaching something the model now does unprompted;
  - ones whose journal entry won by the smallest margin;
  - the **largest always-on descriptions** (the `ALWAYS` column of `cortex skills`);
  - and none that `cortex usage` shows no task can measure.

  How recently a skill was used is **not** a reason to test it and **never** a
  reason to delete it. Fewer is fine; **none is fine** — if nothing is worth
  measuring, say so, journal `prune: nothing to test`, and stop.

  ```bash
  cortex prune plan --items "<a> <b>" --why "<a>=overlaps <x>" --why "<b>=biggest always-on (310 chars)"
  ```

The plan targets each item at the tasks where it can actually load — for a
path-gated skill or a rule, the tasks whose files match its `paths`; for an
always-on skill, the tasks where it loaded in past sweeps — so a removal costs
tens of rollouts, not the whole suite. Items that could only come out
UNMEASURED are **skipped** with the reason; items over `max_runs_per_cycle` are
**blocked**.

### Show it — and stop

Print the plan **exactly as the command printed it** — every item, the rollouts,
the estimated time, tokens and cost, and the estimate's basis — and ask:

```
Approve this prune pass? It will run <N> rollouts (~<time>, ~<tokens> tokens<, ~$cost>).
Reply "yes" to start, or name items to drop.
```

Then **end the turn. Do not approve it yourself, do not launch anything, do not
schedule a wake-up.** Only the user's answer continues the pass:

- **yes** → `cortex prune approve`, then **Step 3**.
- **drop some items** → `cortex prune cancel`, `cortex prune plan --items "<the rest>"`,
  show it again, and stop again.
- **no** → `cortex prune cancel`, and stop.

---

## Step 3 — Measure the next item

```bash
cortex prune next
```

It names the next item and prints its two commands, already targeted
(`--tasks`). Dry-run first, in the foreground:

```bash
cortex sweep --replace <name> --tasks "<ids>" --phase confirm --dry-run
```

`sweep: REFUSED: …` → report the reason and stop; nothing was spent. `sweep: OK …`
→ launch it:

```bash
cortex sweep --replace <name> --tasks "<ids>" --phase confirm --detach
```

`base` is the harness as it is now. `cand` is the same harness without
`<name>`. The live `.claude/` folders are **never touched**: the sweep builds
both arms from a snapshot, so the user's sessions keep the item while it is
being measured.

Report one line (`measuring removal of <name> — item i of n, ~N rollouts, in
background`), schedule a wake-up about N ÷ W minutes out (the `sweep: OK — N rollouts, W at a
time` line; at least 300 s), and end the turn. On waking, poll:

```bash
cortex prune next --json          # "sweep": {"finished": false|true, "file": ...}
```

Still running → one quiet line, sleep again. Finished → Step 4.

---

## Step 4 — Read the verdict

**The verdict is computed by `cortex score`, not by you.** Score the item's own
results file (the `sweep.file` from `next --json`):

```bash
cortex score <sweep.file> | jq -c '{verdict, verdict_because, net_runs, replaced_fired_runs, base_total, cand_total, tokens_total, cost_usd_total}'
```

| verdict | meaning | do |
|---|---|---|
| `RERUN` | the data was never trustworthy — including **firing unknown** (the rollouts' output could not be read) | fix what `verdict_because` names and sweep again (Step 3). Decide nothing, record nothing. Unknown is never "it did not fire". |
| `REJECT` | removing it **costs** something measurable | **keep** it. Nothing to undo. |
| `UNMEASURED` | it never fired in any rollout: no task exercises it | **keep** it. The suite cannot see it, so "costs nothing" was never measured. Suggest harvesting a task that needs it. |
| `ACCEPT` | it fired, and removing it costs nothing measurable | **delete** it: `cortex bury <name> --from live --why "prune: net_runs <n>, fired in <r> base rollouts"` |

`cortex bury` moves it to `.evolve/graveyard/` — a skill's folder as-is, a rule
as `graveyard/<name>/RULE.md` — never overwriting an older entry of the same
name, and records the reason and the kind next to it. Buried, not lost.

Then record the decision in the plan, and journal it (Step 6):

```bash
cortex prune record <name> --verdict <ACCEPT|REJECT|UNMEASURED> --results <sweep.file> --action "<buried | kept>"
```

The gates behind `REJECT` (from `config.yaml`, echoed in `thresholds`):

```
1. net_runs > -min_net_runs              does removing it lose measurable runs?
2. worst_drop <= regression_tolerance    does any single task collapse?
3. protected_broken == []                do tasks at 1.00 stay at 1.00?
```

**Delete before testing the next item.** Each measurement then starts from the
harness as it really is, so deletions are measured in sequence, never assumed
to add up. Then back to **Step 3** for the next item — the approval covers the
whole plan; do not ask again for each item.

*Why this matters most after a model upgrade:* the new model may already do what
your skill teaches. A behaviour the model has internalised leaves the
corresponding skill as dead weight. Dead weight that still costs you context on
every single turn.

---

## Step 5 — Narrow what is always on, and resolve collisions

Two kinds of change, both measured the same way: a candidate that **replaces**
live items, swept against what is live now. They are not part of the plan, so
each one is shown and approved on its own.

**Narrowing** — an always-on skill whose every use is in one area (`cortex usage`
says `narrowing candidate`) pays its context cost on every turn for nothing.
Move it into a tier that loads only there:

```bash
# the same skill, gated: a rewritten copy under the SAME name, with paths:
.evolve/candidate/<a>/SKILL.md          # + paths: ["<dir>/**"]
# or turned into a rule (short, hard, about files the agent READS):
.evolve/candidate/<a>/RULE.md           # + paths: ["<dir>/**"]
```

**Collisions** — two always-on skills whose `description` lines would trigger
on the same request, or two gated items whose `paths` overlap and say different
things, will fight; the model picks unpredictably. Merge them, or narrow one:

```bash
.evolve/candidate/<merged>/SKILL.md     # merge a and b into one
```

Check the candidate, and show the user what it will cost — on the tasks where
the items load (from `cortex usage`) — **before** anything runs:

```bash
cortex skills --candidate <merged> --replace "<a> <b>" --tasks "<ids>"
cortex prune estimate --tasks "<ids>"
```

Ask the user to approve that one swap, and stop. On **yes**, dry-run and launch —
same rules as Step 3:

```bash
cortex sweep --candidate <merged> --replace "<a> <b>" --tasks "<ids>" --phase confirm --dry-run
cortex sweep --candidate <merged> --replace "<a> <b>" --tasks "<ids>" --phase confirm --detach
```

(for narrowing: `--candidate <a> --replace <a>`.)

Then Step 3's polling and Step 4's verdicts apply, with these actions:

| verdict | do |
|---|---|
| `ACCEPT`, `candidate_fired_runs > 0` | `cortex bury <a> --from live` (and `<b>`), then `cortex promote <merged>` |
| `ACCEPT`, `candidate_fired_runs == 0` | the swap costs nothing, but the replacement **never loaded**, so it was never measured: `cortex bury <a> --from live` (removal is proven harmless) and `cortex bury <merged> --from candidate --why "never fired"` — never promote an unmeasured item |
| `REJECT`, `UNMEASURED` | `cortex bury <merged> --from candidate --why "<verdict>"`: the live items stay |
| `RERUN` | fix the cause, sweep again |

---

## Step 6 — Journal, finish, report

Append one entry to `.evolve/journal.md` for **every** sweep you decided on,
whatever the verdict. `/evolve` reads it back.

```markdown
## YYYY-MM-DD  prune

results:   .evolve/runs/20260917T101500-confirm.jsonl
model:     <pinned model, or "CLI default">
kind:      removal
tested:    json-parse-guard  (skill, tasks 02 04)
verdict:   ACCEPT  (net_runs -0.00, fired in 6/6 base rollouts)
action:    buried — the model handles it now
cost:      12 rollouts, 1.8M tokens, $2.10
```

```markdown
## YYYY-MM-DD  prune

results:   .evolve/runs/20260917T104500-confirm.jsonl
kind:      narrowing
tested:    migrations-guide: always-on -> gated  paths: ["db/migrations/**"]
verdict:   ACCEPT  (net_runs +0.00, gated copy fired in 4/6 cand rollouts)
action:    old buried, gated copy promoted — 310 chars off every turn
```

```markdown
## YYYY-MM-DD  prune

kind:      path-repair
tested:    api (rule)  paths "services/api/**" -> "services/backend/**"
evidence:  renamed in 3f2a9c1e04 (printed by `cortex skills`)
action:    edited in place; `cortex skills` shows it live
```

```markdown
## YYYY-MM-DD  prune

results:   .evolve/runs/20260917T113000-confirm.jsonl
tested:    docker-compose-subset
verdict:   UNMEASURED  (fired in 0 base rollouts)
action:    kept — no task exercises it; harvest one
```

When `cortex prune next` says `nothing left to test`:

```bash
cortex prune finish
```

It closes the plan and remembers the pinned model, so the next pass knows
whether the model has changed since. (If the user stops the pass early:
`cortex prune finish --force`.)

Then report in one block: items tested, deleted, narrowed, repaired, kept, and
unmeasured — and what the pass actually cost (`tokens_total`, `cost_usd_total`
from each sweep) against the plan's estimate.
