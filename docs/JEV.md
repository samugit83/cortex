# Jev

Jev is a *System One* model from TypeSafe: you send it some **state** and some
**typed questions**, and it returns calibrated answers — a probability for a
yes/no question, a labelled choice with its confidence, a score against a rubric.
It does not generate text, it does not choose its own next action, and it is not
an agent.

Cortex uses it in exactly one place: the **proposal** layer. Which theme, which
tier, which scope, is there anything worth harvesting.

Cortex's founding constraint (THEORY §2) is that a verifier is a command that
exits `0` or non-zero — *"not an opinion, not an LLM judge"*. Jev **is** a judge.
So the burden of proof is on this integration, and two contracts come before
anything else in this file.

---

## Contract 1 — what runs when Jev is off

`jev.enabled: false`, or no key, or an unreachable endpoint. All three are the
same state, and Cortex does what it did before Jev existed:

| Step | With Jev | With Jev off / no key / unreachable |
|---|---|---|
| `cortex scope` | relevance ratio + the floor warning | the deterministic half only (`injected into N of M tasks`), `relevance: unavailable`, **exit 0**. A5 continues |
| the Stop hook | nudges on `Noul > threshold` | nudges on `DIRTY > 0` — byte-for-byte the old `log-session.sh` behaviour |
| `cortex themes` | full census over lessons **and** transcripts | lessons grouped by their existing `area:` lines, `source: areas (jev off)`; transcripts read by Claude as a sample, as before |
| `/evolve` A4 tier priors | — | **unaffected: it is text in `evolve.md`, no call, no key** |
| `cortex jev tier` | a `Choice` + the confidence gate | exit 3 — the same escalation a low-confidence answer takes: Claude decides from the A4 table |
| trigger prediction | a second question inside the scope request | absent from the report; A5 proceeds on `cortex skills --candidate` alone |
| `/prune` ranking | a `Score` merged into the ordering | the existing `cortex usage` hints alone |
| **gates 0–5, `cortex score`, `check.sh`, preflight** | — | **identical either way: no Jev code path exists there at all** |

Three consequences worth stating plainly:

1. **No step is Jev-only.** Every one has a defined keyless behaviour, and
   `cortex themes` keyless is *better* than the old A3, not merely equal to it.
2. **The verdict path is not merely unchanged, it is untouched.** `bin/score.sh`,
   `bin/preflight.sh` and `bin/sweep.sh` gain no import, no field and no flag —
   the test suite asserts the string `jev` does not appear in any of them.
   Turning Jev on cannot change a KEEP into a KILL.
3. **The command prose changed permanently, in both modes.** A keyless user runs a
   differently worded A3 than before, even though it reaches the same place. Each
   command file reads correctly in both branches; that is the one part of this
   contract a test cannot check.

## Contract 2 — why the artifacts are interchangeable

> Jev may change **which** candidate, theme or ordering is produced.
> It may never change **the format of what is written**.
> Anything Jev adds to an existing file is an optional, additive,
> non-load-bearing line that the keyless reader ignores by not looking for it.

| Artifact | Does Jev write it? | Readable in the other mode |
|---|---|---|
| `.claude/skills/*/SKILL.md`, `.claude/rules/*.md` | **no** — `cortex promote` is untouched | identical in both modes |
| `.evolve/tasks/NN/*` | **no** | identical |
| `.evolve/runs/*.jsonl` | **no** — `"schema": 2` unchanged, no row field added | identical |
| `.evolve/baseline.json`, `state.json`, `lessons.md`, `notes.md`, graveyard | **no** | identical |
| `.evolve/journal.md` | **yes** — one optional indented `jev:` detail line | yes: keyless code greps `^## ` and never looks at it |
| `.evolve/prune-plan.json` | **yes** — an optional `jev_rank` per item | yes: `prune next` ignores it when Jev is off |
| `.evolve/config.yaml` | block absent unless you add it | yes, both directions |
| `.evolve/jev/*.jsonl` | **yes** — new file, Jev-only | yes: its absence is the normal keyless state |

A skill promoted with Jev on is **byte-identical in form** to one promoted with
Jev off. The things Cortex exists to produce — skills, rules, tasks, verdicts —
have no Jev in them at all.

Switching mid-cycle is the sharp case, and it is safe in both directions: no Jev
code runs inside a sweep, every contribution is written at the moment it is made,
and **no artifact's validity depends on Jev having been available when the next
step runs.**

---

## Turning it on

### Which route: Vercel AI Gateway, or TypeSafe direct

The same model, two doors, **and the same wire format through both** — Vercel
implements TypeSafe's request and response shapes verbatim, so `bin/jev.py` needs
no adapter and does not know which one it is talking to. Only two settings differ.

| | Vercel AI Gateway | TypeSafe direct |
|---|---|---|
| Get a key | [vercel.com/ai-gateway/models/jev](https://vercel.com/ai-gateway/models/jev) → **Get API key** | [console.typesafe.ai/keys](https://console.typesafe.ai/keys) |
| Availability | open to any Vercel account | **invite only** — join the waitlist at typesafe.ai |
| Key looks like | `vck_…` | whatever the console issues |
| `JEV_BASE_URL` | `https://ai-gateway.vercel.sh/typesafe/v1/systemone` | `https://api.typesafe.ai/v1/systemone` |
| `JEV_MODEL` | `typesafe-ai/jev` | `jev-latest` |
| Catch | AI Gateway needs a **credit card on file** before it routes anything, even though Jev is free | a waitlisted account's key is rejected `401`, exactly like a wrong one |

`.env.example` ships the Vercel route, because it is the one most people can
actually use. The built-in default in `compile-config.py` is still TypeSafe's own
endpoint — `.env` beats it, and `cortex config` prints which one is in force.

**A key from one route will never work against the other's URL.** A `vck_` key
sent to `api.typesafe.ai` returns `401 invalid key`, which reads exactly like a
typo. If `cortex doctor` says `invalid key`, check the URL before the key.

### Then

```bash
cp $CORTEX_HOME/.env.example $CORTEX_HOME/.env   # then paste your key
cortex doctor                                     # key · endpoint · round-trip · model id
cortex config                                     # every effective value, and its source
```

A key alone is not enough: the built-in default is `enabled: false`, and
`JEV_ENABLED=1` in your `.env` is what turns it on. `cortex doctor` says exactly
that when it finds a key with the switch off.

The key is resolved from the environment, then `$CORTEX_HOME/.env` (or
`JEV_ENV_FILE`), then `<repo>/.env`. Put it in `$CORTEX_HOME/.env`: the key is a
property of the machine, not of a project, and that keeps it out of every repo
the tool touches. `cortex init` gitignores `.env` and `.evolve/jev/` in any repo
it sets up, and `cortex config --check` **refuses** a `.env` in
`environment.harness_files` — that list is copied into both rollout sandboxes,
which is the one place a secret must never appear.

---

## The question library

Every question Cortex asks, verbatim, from `bin/jev.py`. Changing the wording of
one of these invalidates the accuracy recorded for it in `jev/RESULTS.md`.

### `relevant` — is this task about the candidate's subject?

*Used by:* `cortex scope` (J1), `jev/validate.py` (J0).
*Type:* Noul — a probability. Read as "about it" at ≥ 0.5.

```
instructions: {"question": "Is this coding task about the subject below?",
               "subject": <the candidate's name, description and body>}
criteria.true:  "The task's own goal involves the subject: an agent doing this task
                 would have to read, write or reason about the subject to finish it."
criteria.false: "The subject is incidental or absent: an agent could finish this task
                 correctly without ever thinking about the subject."
```

**State sent:** that task's `task.yaml` title, its `prompt.txt` and its
`notes.md`. Nothing else — not `fix.patch`, not the repository, not your code.
A task with no `notes.md` is sent its prompt alone and reported as `(thin state)`.

**Feeds:** the relevance ratio, and `jev.scope.relevance_floor` (default 0.35),
below which it prints a warning. It never blocks a sweep and never kills a
candidate.

**Why a model at all.** The free deterministic alternative is *breadth* — what
fraction of the suite the glob reaches, which `reachable_tasks()` already
computes. Measured on 984 recorded rollouts it does not work: 100% breadth
appears in **both** the kept group and the regression-buried group. The
discriminating quantity is the ratio of relevant to total injections, and its
numerator requires judging what a task is about.

### `would_fire` — would an agent invoke this skill?

*Used by:* `cortex scope`, for **skills only** — a rule that is visible fires
100% of the time (410 measured rollouts), so for a rule there is nothing to
predict and the question is not asked.
*Type:* Noul.

```
instructions: {"question": "Would an agent doing this task choose to invoke the skill
                            below, given only its description?",
               "skill": <name>, "description": <its description line>}
criteria.true:  "The description names the task the agent is doing, so the agent would
                 open the skill before acting."
criteria.false: "The description names a side duty, or something the agent would not
                 connect to this task, so it would never be invoked."
```

**State sent:** the same task state as `relevant` — it shares the request.
**Accuracy: unproven.** The corpus holds 3 skill candidates / 76 runs. Treat it
as a reason to reword a description before paying for a screen, never as a reason
to skip one.

### `fixed` and `corrected` — the Stop hook's filter

*Used by:* `hooks/log-session.sh` (J2). One request, two answers.
*Type:* Noul ×2.

```
fixed:     "In this session, did something go from broken to working? A failing test
            went green, a build started passing, a service came up, an endpoint
            started answering."
corrected: "In this session, did the user correct the assistant? For example:
            "you forgot...", "CI still fails because...", "we never do it that way",
            or a check they pasted that the assistant had to fix."
```

**State sent:** `git status --porcelain`, `git diff --stat HEAD`,
`git log --oneline -5`, and the last **8 user turns** of the session transcript —
the user's own words only, with `<system-reminder>` blocks stripped. The
assistant's output is never sent: a correction is something the *user* said.

**Feeds:** `jev.harvest.noul_threshold` (default 0.6). Above it the hook prints
the nudge; below it the hook stays **silent**. The hook's design rule — never
slow, never noisy — outranks this feature: a call that is disabled, refused, slow
or absent falls back to the old `DIRTY > 0` line, and a 5-second ceiling stops a
hung endpoint from adding anything measurable to a session end.

### `area` — which theme is this lesson about?

*Used by:* `cortex themes` (J3), once per lesson line and once per transcript chunk.
*Type:* Choice over the live skills and rules, the graveyard entries, the `area:`
values `/harvest` recorded, and `new`.

```
instructions: "Which area is this lesson about?"
criteria:     {<each live item>: "the live <kind> on <paths>: <its trigger>",
               <each area>:      "the area '<name>', named by N task(s)",
               <each buried>:    "an idea already tried and buried: <why>",
               "new":            "This lesson is about something none of the areas
                                  above covers."}
```

**State sent:** one lesson line and its task id; or one ~12,000-character chunk of
**user turns only** from this project's transcripts in the `lookback_days`
window. Never another project's sessions, and never the assistant's output.

"This project's" is enforced, not assumed. Claude Code names a transcript folder
after the project path with every non-alphanumeric character replaced by `-`, so
`/p/myproj-other` and `/p/myproj/other` produce the **same** folder name pattern:
the name alone cannot tell a sibling project from a sub-folder. An exact name
match is taken as this repo; anything matched only by prefix is confirmed against
the `cwd` the session itself recorded, and a prefix match carrying no `cwd` is
**dropped** rather than sent. A long turn is split across chunks, never truncated,
so the census reads every word it counts.

**Feeds:** the counts `collection.min_theme_occurrences` is applied to. Counting
in a shell script is the point: it replaces a model's recollection of a folder it
could not read whole.

### `correction` — does this transcript chunk contain one?

*Used by:* `cortex themes`, paired with `area` in the same request. A chunk counts
toward a theme only when this is ≥ 0.5.
*Type:* Noul.

```
instructions: "Does this excerpt of a coding session contain the user correcting
               the assistant?"
criteria.true:  "The user tells the assistant it did something wrong, or supplies a
                 constraint it had missed."
criteria.false: "No correction: questions, new instructions, or the assistant working
                 uninterrupted."
```

### `tier` — which layer should this change live in?

*Used by:* `cortex jev tier` (J4b), from `/evolve` A4.
*Type:* Choice over the six layers of the A4 table, with confidence.

```
instructions: "Given this recurring problem and the files its fixes touch, which layer
               should the change live in?"
criteria:     rule · gated-skill · always-on-skill · claude-md · permission · hook
              (each with the A4 table's own description)
```

**State sent:** the one-sentence theme you pass on the command line, and the paths
you pass. Nothing is read from the repository.

**Feeds:** `jev.confidence_floor` (default 0.7). Below it the command exits 3 and
Claude decides from the table, which is the same escalation a low-confidence
answer already took. This is a safe site for a judge precisely because **a wrong
pick is killed by the gates** — the verifier is intact either way.

### `removable` — how likely is removing this to cost nothing?

*Used by:* `cortex prune plan` (J6), once per item.
*Type:* Score, 0–4, with confidence.

```
instructions: "How likely is removing this skill or rule to cost nothing?"
criteria:     0 "Removing it would clearly cost something: it carries a constraint the
                 tasks in its area depend on."
              1 "Removing it would probably cost something."
              2 "Unclear either way."
              3 "Removing it would probably cost nothing: the model appears to do this
                 unprompted."
              4 "Removing it would clearly cost nothing: it restates a default, or
                 nothing reaches it."
```

**State sent:** the item's name, kind, tier, `paths`, description and body, and
which tasks can measure it. No transcripts.

**Feeds:** the `DOUBT` column and the order `cortex prune next` walks. **A sort
order only** — every removal is still decided by its own sweep.

---

## What leaves your machine, in one list

- task titles, `prompt.txt` and `notes.md` (scope)
- your lesson lines (themes)
- the last 8 user turns of a session (the hook), and user turns from this
  project's transcripts in the lookback window (themes)
- `git status --porcelain`, `git diff --stat`, `git log --oneline -5` (the hook)
- the name, description and body of skills and rules you wrote (scope, prune)

Never: your source files, `fix.patch`, the assistant's output, other projects'
sessions, or your API key. With `jev.enabled: false`, nothing at all.

---

## The log

```
.evolve/jev/<UTC-date>.jsonl
```

One line per request: the call site, the question ids, each answer with its
probability or confidence, `usage.input_tokens`, **the model id the API answered
with**, the latency and the outcome (`ok | timeout | 429 | fallback`). It never
carries the state that was sent — that is the transcript, and it is not ours to
keep. It never carries the key.

It is also how an answer survives a turn boundary: `/evolve` is a resumable state
machine whose cycle spans several turns and a background sweep, so an answer from
A3 that D5 has to journal cannot live in the conversation. `cortex jev journal
--candidate <name>` reads it back.

`cortex clean` leaves it alone; `cortex clean --runs` removes it with the results
it is about. Files older than `prune.usage_days` go on the next write.

---

## Model drift

`jev-latest` is a moving alias with exactly the hazard `bin/score.sh` already
guards against for the Claude CLI, and no equivalent guard of its own.

- every logged answer records the model id that answered;
- `jev/RESULTS.md` records the model id J0 was measured against, in its first lines;
- `bin/jev.py` compares the two on every call and prints, **once per run**:
  `jev: answering model is <X>, J0 validated <Y> — re-run jev/validate.py`.

It does not block. Jev is advisory everywhere, so a stale calibration degrades a
hint, never a verdict. Pin `JEV_MODEL` to an exact version to suppress drift
entirely.

---

## Errors, and what each one degrades to

| Status | What Cortex does |
|---|---|
| no key / `enabled: false` | the keyless path of Contract 1. Silent — this is a normal state, not a failure |
| `401` invalid key | one warning line, then the keyless path. **Not retried**: retrying a bad key only makes the wait longer. Check the URL matches the key's route before assuming a typo, and note a waitlisted TypeSafe account looks identical |
| `403` refused | the keyless path. On TypeSafe direct it means no key was sent at all; on AI Gateway it is usually `customer_verification_required` — add a card at [vercel.com/account/ai](https://vercel.com/account/ai). The message says which |
| `422` malformed request | one warning line, then the keyless path |
| `429` rate limited | retried `jev.retry.attempts` times honouring `Retry-After` (including `Retry-After: 0`, which means *retry now*), then the keyless path — always inside `timeout_s` |
| `529` overloaded | the same |
| timeout, DNS, connection refused | the keyless path |
| malformed JSON, missing question id | the keyless path. Never a traceback |
| budget exceeded | the census **refuses to start** and says which ceiling it hit, rather than silently becoming a sample again |

Every one of those rows is a test in `test/run-tests.sh`, driven against
`test/jev-stub.py`. No test in the suite makes an API call.

---

## Cost

Jev is charged per input token; output tokens are free. At $0.042/MTok (Jev is
currently **free** through AI Gateway, on promotional pricing — the numbers below
are the list rate, so treat them as the ceiling):

| Call site | When | Rough cost |
|---|---|---|
| `cortex scope` | once per candidate, before a sweep | ~$0.002 |
| the Stop hook | once per session | ~$0.0002 |
| `cortex themes` | once per `/evolve` cycle | ~$0.25 at 6 MTok of transcripts |
| `cortex jev tier` | once per cycle | negligible |
| `cortex prune plan` | once per pass | negligible |

`jev.budget.max_requests_per_cycle` (2000) and `max_input_mtok_per_cycle` (12)
bound the census; `max_rps` (15) sits an order of magnitude under the published
1200/min while Jev is in early access and its limits are still moving.

Against that: on the recorded run this was measured from, three candidates that
were injected into tasks they were not about cost **694 rollouts and $77.70** and
landed nothing. `cortex scope` would have shown all three as a scope problem
before the first rollout ran.

---

## J0 — the gate

Nothing here shipped until `jev/validate.py` proved, on Cortex's own recorded
data, that Jev beats the free alternative:

```bash
python3 jev/validate.py                      # score a repo's sweep history
python3 jev/validate.py --corpus jev/corpus  # replay the committed snapshot
python3 jev/validate.py --dry-run            # the free baseline, no key needed
```

Pass needs **≥ 90% agreement** with the keyword oracle of the plan, the
KEPT/BURIED separation preserved, and monotonic calibration. `jev/RESULTS.md` is
its output and records every fact that could invalidate it — above all the
answering model id, which `bin/jev.py` reads back.

`jev/corpus/` is a committed snapshot of exactly the rows J0 scored, because
`cortex clean --runs` deletes `.evolve/runs/*.jsonl` and would otherwise make the
whole result unfalsifiable.

Re-run it after any Jev model version change, exactly as `cortex preflight`
re-proves the task suite.
