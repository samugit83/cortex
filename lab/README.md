# The Cortex lab — does it actually work?

An end-to-end test of Cortex, run the way a real user would run it: a real repository,
real Claude Code sessions with **Haiku 4.5**, real `/harvest` and `/evolve`. Ten rounds of
work, then a benchmark that compares the agent **with** and **without** the skills Cortex
evolved.

## The claim under test

> Used as documented, Cortex learns the house rules of a codebase from the user's
> corrections. It turns each recurring one into a skill or rule in the right tier, keeps only
> what measurably helps, and adds nothing that does not.

Four things have to be true for that claim to hold, and each one is measured:

| # | Question | Where it is answered |
|---|---|---|
| 1 | Do the evolved skills and rules raise the pass rate, on tasks never seen during evolution? | final benchmark, **holdout** set |
| 2 | Does each house rule end up in a sensible tier (always-on skill, gated skill, rule)? | journal + `cortex skills`, every round |
| 3 | Do they leave work that needs no house rule alone, with no regressions and no spurious skills? | control family D, benchmark + every confirm sweep |
| 4 | Does the user stop having to correct the agent once a skill is live? | corrections per session, round by round |

## The lab repository: `cortex-lab`

`/home/samuele/Progetti didattici/cortex-lab`: *shopkit*, a small Python order and
invoicing toolkit (catalog, carts, invoices, refunds, exports, reports, a CLI). It has 70 unit
tests, no dependencies, and a history of eight commits by two teammates. It is rebuilt from
`lab/seed/` with `lab build --force`.

Like most real codebases, it has **house rules**: written down in `CONTRIBUTING.md`,
enforced partly by CI (`make verify` = unit tests + `tools/lint.py`), and unknown to a model
that has not read them. Each family of work below is built around one of them:

| Family | The house rule | Where the work happens | A fresh agent's typical mistake | How a check sees it | The tier we expect |
|---|---|---|---|---|---|
| **A** user-visible change | every visible change gets a `CHANGELOG.md` line under `[Unreleased]` | all over: CLI, report, formatting | implements the feature, forgets the changelog | `git diff` of CHANGELOG.md | always-on skill (a *moment*: "before done") |
| **B** money | integer cents, scaled only with the helpers in `billing/rates.py`; never `float`, `/`, `round()`, `Decimal` | `shop/billing/` | fixes a rounding bug with `float()` | `make lint` (money) | rule on `shop/billing/**` |
| **C** new exporter | registry entry + `docs/exporters.md` row + golden file (`make golden`) | new files in `shop/plugins/` | writes and registers the plugin, stops there | `make lint` (exporters) | path-gated skill (the agent *creates* files there) |
| **D** control | none: plain bugs | `shop/util/` | — | the failing test | nothing: must not regress |
| **E** time | read the time only through `shop.clock`; never `datetime.now()` / `date.today()` | everywhere | `date.today()` | `make lint` (time) | always-on skill or `CLAUDE.md`: a repo-wide fact |

Every session starts the way work reaches a real developer: a **teammate's commit** (QA adds a
failing test, product changes a spec, a colleague writes the tests for a new feature), and the
user asks Claude to deal with it. The bugs in families B and D sit in the code from the first
commit; the test that exposes each one arrives in that session.

**Why the lab is fair:**
- The rules are written in the repository. A careful agent *can* find them, and the
  corrections point at them.
- The answers are never in the repository: scenarios, reference fixes and holdout tasks live
  here in `Cortex/lab/`, outside `cortex-lab`. Cortex itself now hides `.evolve/` from the
  rollout sandboxes, so an agent under test cannot read earlier tasks' fixes or lessons.
- Nothing is hand-tuned in the lab repo during the run: no task is edited by hand, and no
  skill is written by anyone but `/evolve`.

## Rule or skill?

What `/evolve` can create, and how Claude Code loads each one:

| | **Rule** | **Skill** |
|---|---|---|
| File | `.claude/rules/<name>.md` | `.claude/skills/<name>/SKILL.md` |
| What it is | a few lines of hard "never / always" | a procedure: numbered steps, examples, can be long |
| How it gets into Claude | **injected automatically**: Claude has no choice | Claude sees only its **name + one-line description** and **decides** to open it |
| When | when Claude **reads** a file matching its `paths` | *always-on* (no `paths`): its description is there every turn. *Path-gated* (`paths`): appears when Claude **reads or writes** a matching file |
| Cost in context | 0 until a matching file is read | always-on: the description, every turn; path-gated: 0 until triggered |
| Best for | a hard rule on **existing** files in one area | a **moment** ("before reporting done…") or a **procedure** in an area, including **creating** new files there |

In this lab:

- **Money** → a **rule** on `shop/billing/**`. Claude always *reads* the billing file it
  fixes, so the rule is injected every time, with no reliance on Claude choosing it.
  (This is what `/evolve` chose in round 1.)
- **CHANGELOG** → expected to be an **always-on skill**: it's a *moment* ("before you say
  done"), not a place.
- **New exporters** → expected to be a **path-gated skill**: Claude *creates* a new file in
  `shop/plugins/`, and a rule never triggers on writing a new file.

## One session

```text
terminal                        Claude Code (a NEW chat, Haiku 4.5)
────────                        ───────────────────────────────────
lab next      → prints prompt   paste the prompt, let Claude work
lab verify    → "✔" or a reply  paste the reply (if any), let Claude fix
lab verify    → "✔ …/harvest"   /harvest
lab done      → records + commits
```

**From round 2 the sessions run themselves.** `bin/autopilot round N` does exactly the
loop above with no one at the keyboard. Each step is a real headless Claude Code session in
`cortex-lab` (Haiku 4.5), fed what you would type: the prompt, the reply `lab verify` prints,
`/harvest`. Then it runs `/evolve` in a new session, waits for each sweep, runs `/evolve`
again until the cycle ends, and runs `lab commit`.
- Permissions are your own mode (`bypassPermissions`) minus a deny list: no sudo, no
  `git push`, no network tools, no `rm -rf` of `/` or home.
- The scheduler tool is off, so the autopilot does the waiting itself.
- Nothing is fixed by hand. A step that doesn't follow the protocol is logged as a
  **FINDING** in `state/autopilot.log`. Every turn (session id, cost, seconds, reply) goes
  to `state/autopilot.json`.
- When a FINDING turns out to be a Cortex bug, the bug is fixed (with a test) and the
  session is re-harvested the way a user would: `bin/autopilot reharvest C01 "why"`
  resumes that session's own chat, types `/harvest` with the note, and runs
  `lab done --late C01`. A late harvest after other sessions uses
  `cortex task new --head <the session's last commit>`, so no other work leaks into its
  fix.patch.

`lab verify` plays CI and the reviewer. It runs the new test, the whole suite and the linter,
and checks the changelog for family A. If something is wrong, it prints the reply a real user
would paste: *"The test passes now, but CI is still red: `make lint` rejects float arithmetic
in shop/billing/ …"*. That reply is the **correction** that `/harvest` turns into a lesson and
into the task's check. Same failure, same words, every time, so every session is comparable.

## The ten rounds

A round = its sessions, then `/evolve` in a new chat, then **you tell me** and I check.

| Round | Sessions | What should happen at `/evolve` |
|---|---|---|
| 1 | B01 B02 B03 | money: 1–2 lessons only (B02 copied the rule from B01's fix in the code) → most likely BARREN |
| 2 | A01 A02 A03 | changelog: three lessons in one round → the **first skill**, probably always-on |
| 3 | C01 C02 C03 | exporters → a path-gated skill (or a rule) on `shop/plugins/**` |
| 4 | E01 E02 E03 | time → always-on skill or `CLAUDE.md`, unless Haiku copies `clock` from E01's fix |
| 5 | D01 D02 D03 | controls: no lessons → BARREN; they become tasks nothing may break |
| 6 | A04 B04 C04 | skills live: sessions should need no correction → BARREN |
| 7 | A05 B05 E04 | same; after three quiet rounds Cortex says STOP (converged) |
| 8 | C05 D04 | same |
| 9 | A06 B06 | same |
| 10 | C06 | the last training task |

**Changed after round 1** (the first plan interleaved families): B02 needed no correction,
because Haiku found `percent_of()` in `tax.py`, fixed in B01, and copied it. A house rule that
leaves a visible trace in the code the agent reads is learned from the code; one whose trace
lives elsewhere (CHANGELOG, docs, golden files) is not. So each family's first three sessions
now run back to back, the "trace elsewhere" families first.

Prune is **not** run during the ten rounds; it comes after the benchmark.

Each round's instructions are in `rounds/round-NN.md` (round 0 is the installation).

## What I check after every round

- **Harvest quality**: each new task in `.evolve/tasks/` has the right `base_sha`, a verbatim
  prompt, a fix that includes new files, and a check that encodes the correction.
  `lab audit` runs every harvested check against the broken state, a house-rule fix and a
  rule-breaking fix. A check that passes the rule-breaking fix cannot measure the rule.
- **Preflight**: what was quarantined, and why.
- **Lessons**: one line each, with the task id, and themes that recur.
- **`/evolve`**: the theme and tier it chose, the candidate's text and `paths`, dry run first,
  the screen on the theme's tasks, the confirm on all, exposure, `RECHECK`s, the verdict and
  the journal. Also what Haiku did wrong while driving the protocol.
- **Routing**: `cortex skills`, i.e. what is always in context and what is gated.
- **Cost**: tokens, dollars and minutes per sweep, from `cortex score`.
- **Anything broken in Cortex**: fixed, with a test, before the next round.

Results go in `results/round-NN.md`.

## The final benchmark

After round 10, the lab measures what the whole loop produced.

- **Tasks**
  - *train*: the 26 training scenarios, each from its own starting commit;
  - *holdout*: 15 scenarios never seen during evolution (3 per family: HA1–3, HB1–3,
    HC1–3, HD1–3, HE1–3). They are committed at the end, onto the final code, on side
    branches.
- **Arms**, the same tasks and model, differing only in the harness:
  - **none**: no skills, no rules, the minimal `CLAUDE.md` from `cortex init`;
  - **evolved**: exactly what Cortex kept;
  - **kitchen sink** (optional): all of `CONTRIBUTING.md` pasted into `CLAUDE.md`. It shows
    what a careful user would do by hand, and what it costs in always-on context.
- **Judge**: the lab's own oracle, not the harvested checks. It is the same for every arm
  and every task: the test passes, `make test` and `make lint` are green, and for family A the
  changelog changed.
- **k = 3** rollouts per task per arm, in clean sandboxes, with arms interleaved. That is
  about 250 rollouts for two arms. `bench.py run --jobs auto` (the default) runs them
  several at a time, one sandbox per worker, sized exactly like a Cortex sweep from the
  lab's `measurement.parallel` settings and the RAM free at the start.
- **Reported, per family and per split**:
  - pass rate with a 95% Wilson interval;
  - the paired difference, evolved − none;
  - how often each skill or rule loaded, and where;
  - tokens, cost and wall time per rollout;
  - the always-on context in characters.

**Prediction:** the gain shows on A, B, C and E, holdout included, while D stays flat at
nearly 100% in both arms. If any of those fails, that is a finding, not a failure of the lab.

## Budget

Measured in the pilot: one Haiku rollout costs **$0.06–0.25**, about $0.09 on average, and
takes 1–2 minutes.

| Phase | Rollouts | Cost (Haiku) | Wall time |
|---|---|---|---|
| 26 sessions, done by you | 0 | ~$0.30–0.50 each (the rehearsal: $0.44, half of it `/harvest`), ~$10 total | 5–10 min each |
| `/evolve`, 10 rounds: ~4 KEEP cycles (screen + confirm), a few KILLs / RECHECKs, the rest BARREN (free) | ~420 | ~$35–45 | one at a time: ~10 h. **Parallel (auto, ~9 at a time on this machine): ~1.5 h** |
| benchmark, 2 arms × 41 tasks × k=3 | ~250 | ~$20–25 | one at a time: ~4–5 h. **Parallel: ~30 min** |
| **total** | ~670 | **~$65–80** | |

The config pins `max_runs_per_cycle: 200`, so no single sweep can run away. The largest
confirm is 26 tasks × 3 × 2 = 156 rollouts.

**Nothing is measured beside something it cannot share.** A task whose check needs
something machine-wide (a fixed port, a fixed path outside the repository, a shared
database) runs one rollout at a time: preflight finds those by running each check
twice at the same moment, and marks them `exclusive: true`. None of the lab's own
tasks needs it — they are plain `unittest` and `lint` runs — but the check costs one
extra check per task, once.

**Parallel rollouts.** Since round 3, Cortex runs a sweep's rollouts several at once
(`measurement.parallel`, default `rollouts: auto` = 50% of the free RAM ÷ 1 GB per
rollout, capped by the CPUs and 16). On this machine (12 CPUs, ~19 GB free) that is 9 at
a time. Measured with Haiku on a real sweep: 8 rollouts took 75 s one at a time and 16 s
eight at a time, with identical results. The cost does not change: the same rollouts
run, only side by side. The sessions themselves stay one after another (each starts from
the previous one's commit), so a round becomes ~10 min of sessions plus a few minutes
of sweeps.

## The environment, as it is

Rollouts run on this machine with your real Claude Code setup, as they would for any user.
So your global skills (`~/.claude/skills`, the bundled ones such as `verify` and `run`, and
the `anthropic-skills` plugin) are listed in **every** rollout, in both arms. Haiku sometimes
uses them. That is fair, because the arms differ only by the item under test. Cortex's firing
statistics count only the lab's own skills and rules. Permissions: rollouts always run with
`--permission-mode acceptEdits`, whatever your global default is, plus the lab's own allow
list (`.claude/settings.json`: make, python, read-only git).

## Ground rules

1. **A new chat for every session and for every `/evolve`.** `/harvest` captures "this
   session"; mixing two scenarios in one chat breaks it.
2. **Paste the prompts and replies exactly.** Don't add hints, and don't mention house rules
   Claude has not been told about. The corrections are the teaching signal.
3. **Let Haiku drive.** If `/evolve` or `/harvest` goes wrong, don't fix it by hand: tell me.
   Those are findings.
4. **Don't edit `.evolve/` or `.claude/` by hand.**
5. **Skip nothing silently.** If a session goes sideways (Claude loops, times out, fixes the
   wrong thing), note it and tell me.

## Files in this folder

| Path | What |
|---|---|
| `README.md` | this plan |
| `rounds/round-NN.md` | what to do in round NN (round 0: installation) |
| `bin/lab` | the session helper: `next`, `verify`, `done`, `commit`, `status`, `audit`, `validate`, `build` |
| `bin/autopilot` | runs a whole round unattended: sessions, `/harvest`, `/evolve` until the cycle ends |
| `bin/roundcheck` | the experimenter's check of a round, as Markdown (`results/round-NN-check.md`) |
| `bench/bench.py` | the final benchmark: `prepare`, `run`, `report` |
| `bench/test_bench.sh` | its own tests, on a clone of the lab repo with a fake `claude` (no API calls) |
| `bin/scenarios.py` | all 41 scenarios: teammate commit, prompt, reference fix, rule-breaking fix |
| `seed/` | the lab repository's source; `lab build --force` recreates `cortex-lab` from it |
| `state/state.json` | what happened in each session (written by `bin/lab`) |
| `results/FINAL.md` | **the answer**: the four claims, the benchmark, what lives and why, what it cost, what it does not show |
| `../diagram/lab.html` | the same story as a visual walk-through: one correction → a task → a measurement → a verdict |
| `results/` | my check after each round (`round-00-calibration.md`: the pilot and rehearsal), and the benchmark report |
| `bench/` | the benchmark runner (written after round 10) |
