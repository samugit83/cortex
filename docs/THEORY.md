# Theory: why Cortex is built this way

This document explains the reasoning behind Cortex's design. It describes only
what the code actually does. Every principle names the file that implements
it, so you can check it. The [guide](GUIDE.md) tells you how to use Cortex; this document
tells you why it works the way it does. Ideas that come from other work are
credited in [Where the ideas come from](#where-the-ideas-come-from).

---

## The question Cortex answers

> Does this piece of text in my harness change what my agent achieves on **my**
> work, and is it worth the place it takes in the agent's context?

A *harness item* is a skill (`.claude/skills/<name>/SKILL.md`), a path-scoped
rule (`.claude/rules/<name>.md`), or a constant file such as `CLAUDE.md`. The
model is fixed; you cannot change it. The harness is plain text you can edit,
diff and review, so it is the one thing you can improve. Cortex only ever
changes those text files.

Cortex answers the question with three operations, each measured the same way:

| Operation | Command | What changes |
|---|---|---|
| **add** one item | `/evolve` | the harness gains one skill or rule |
| **remove** one item | `/prune` | the harness loses one skill or rule |
| **move or merge** an item | `/prune` (narrowing, collisions) | same knowledge, different loading tier, or two items become one |

---

## 1. A harness item has a cost that depends on *when* it loads

Claude Code does not load every item all the time. When an item enters the
context decides what it costs:

| Tier | What sits in context | When |
|---|---|---|
| root `CLAUDE.md` | the whole file | every turn |
| always-on skill | its `description` line (the body loads when the model picks it) | every turn |
| path-less rule | the whole rule | every turn |
| path-gated skill (`paths:`) | its `description` | only after a matching file is Read or Written |
| path-scoped rule (`paths:`) | the whole rule | only after a matching file is Read |

So an item's cost is not just its length. It is its length multiplied by how
often it is present. Cortex counts the characters present on every turn and
compares them with `always_on_budget_chars` (`cortex skills`, `bin/harness.py`).
The objective Cortex works towards is:

```
value(harness) = solve_rate − λ · always_on_context
```

This objective is not computed as a single number. It is enforced by two
rules: add only what raises `solve_rate` (§5), and remove or narrow only what
does not lower it (§6, §7).

An item that never loads is worse than no item at all: it takes context and
gives nothing back. That is why §4 exists.

---

## 2. A measurement needs a ruler that still works

**Principle.** A task can only measure something if its check tells a broken
state from a fixed one. A task that stopped discriminating does not just add
nothing: it pulls every average towards zero, and nothing warns you.

**In the code** (`bin/preflight.sh`, run before every cycle and every prune pass):

```
broken state (base_sha)              → check.sh must FAIL
broken state + fix.patch             → check.sh must PASS
fix.patch without its test files     → check.sh must PASS   (only if the fix edits tests)
```

- The third check catches a check that runs a test *written during the fix*.
  No rollout agent writes that exact test, so the task would fail in both arms
  forever.
- A task that fails any of these checks is **quarantined**
  (`.evolve/tasks/_broken/`). A task whose environment is down
  (`precondition.sh` fails) is **skipped**, not quarantined. An outage is not a
  bad task.
- Every state is checked the way a sweep sees it: without `.evolve/`, and with
  build caches purged.

**Where tasks come from** (`commands/harvest.md`). Tasks are taken from your own
sessions, at the end of the session, and only when something went from broken
to working:
- the prompt is your **original words**, not a cleaned-up version that includes
  hints you only knew afterwards;
- the check also verifies the corrections you made during the session, so that
  a skill aimed at a mistake can actually show an effect;
- `fix.patch` is never shown to the agent. It exists only to prove the task is
  real.

Most sessions produce nothing. That is the filter working: a few trustworthy
tasks are better than many that fail for random reasons.

**A judge may propose; it may never score.** Cortex can call a calibrated
judgement model (Jev) to help decide *what to try*: which theme recurs, which
tier a change belongs in, how much of the task suite a candidate is actually
about. Nothing it says reaches `cortex score`, the gates, `check.sh` or
preflight, and no Jev code runs inside a rollout sandbox, where it would become
part of the harness under test. The ruler stays a command that exits `0` or
non-zero. §12 is the argument for why that line is defensible rather than
convenient, and [`JEV.md`](JEV.md) is the audit: every question, verbatim, with
exactly what state each one sends.

---

## 3. Compare against a live control, not against a memory

**Principle.** The same agent on the same task does not always give the same
result. So the only fair comparison is between the two versions of the harness,
measured at the same time, under the same conditions.

**In the code** (`bin/sweep.sh`):

- **Two arms in every sweep.**
  - `base` is your harness as it is now.
  - `cand` is the same harness plus the one change under test (or minus it, for
    a removal).
  - Both arms load **every** existing skill and rule, so what is measured is
    the change's *marginal* value on top of what you already have. A
    near-duplicate of a skill you own correctly shows no gain.
- **Base is re-measured in every sweep.** `baseline.json` is a cache used only
  to decide which tasks are currently failing. It never enters the gain
  calculation.
- **Interleaved order:** task → run → `base`, `cand`. An API slowdown or a model
  deployment at 09:30 hits both arms equally, instead of landing entirely on
  whichever arm ran second. With several workers (`measurement.parallel`) the
  jobs start in that same order, so both arms of a run go side by side, each in
  a sandbox clone of its own — tighter pairing, not looser.
- **Snapshots:** the harness and the task definitions are copied once, at the
  start of the sweep. Editing a skill while a sweep runs cannot change the
  experiment.
- **Isolation:** one full clone per sweep (`git clone --no-hardlinks`, origin
  removed), so a rollout cannot write into your repository.
- **Every reset is verified.** Before each rollout the sandbox is reset to
  `base_sha`, caches are purged, and `check.sh` is run: **it must fail**. If it
  passes, the reset did not work, and the rollout is marked invalid instead of
  counting as a free pass.
- **Nothing leaks from the experiment's notes.** `.evolve/` is committed, so at a
  later task's `base_sha` it would contain earlier tasks' `fix.patch` files and
  your lessons. The sandbox is a sparse checkout that never writes `.evolve/`.
- **Each arm runs today's harness, not the committed one.** The skills, rules
  and `harness_files` present at an old `base_sha` are replaced with the arm's
  snapshot.
- **The model is pinned** (`baseline.model`). Every sweep refuses a CLI older
  than `min_claude_version`, the version whose loading behaviour Cortex was
  verified against.

---

## 4. Credit or blame an item only where it was present

**Principle.** An item can only change a result in a rollout where it actually
entered the agent's context. Wherever it did not, both arms ran the same
harness, and any difference there is noise by construction. This single rule
shapes four decisions.

**How presence is observed** (`bin/harness.py observe`, reading
`claude -p --output-format stream-json`):

| Signal | Source |
|---|---|
| a skill was **visible** | it appears in the `init` listing or a `commands_changed` event |
| a skill was **invoked** | a Skill tool call in the stream |
| a rule **fired** | the agent Read (or `@`-mentioned) a file matching the rule's `paths` in that arm's snapshot; a rule leaves no trace of its own |
| **unknown** | the output could not be read: recorded as `null`, never as "did not fire" |

**The four decisions it drives** (`bin/score.sh`):

1. **Exposure filter.** The gates in §5 and §6 read only *exposed* tasks: tasks
   where the item under test was visible in at least one rollout. The other
   tasks are listed as `unexposed` and ignored. An always-on skill is exposed
   everywhere.
2. **Gate 5, attribution.** A candidate that never loaded in any `cand` rollout
   is never kept, whatever the scores say.
3. **UNMEASURED.** A removal whose item never fired in any `base` rollout is
   **never** accepted. If nothing in the suite used the item, removing it
   changed nothing *because nothing needed it*. That is absence of evidence,
   not evidence that the item is useless. The item stays, and the advice is to
   harvest a task that needs it.
4. **Unknown blocks the decision.** A single rollout whose firing is unknown
   makes the sweep unscorable. Otherwise a tooling failure would look like dead
   weight, and `/prune` would delete a working skill.

**Diagnosis, not just a verdict.** When a candidate never fired, `notes` says why:
- *never visible* → the `paths` are wrong;
- *visible but never invoked* → the `description` is wrong;
- *a rule whose files no rollout read* → fix the `paths`, or harvest a task in
  that area.

Rewriting the trigger is a different repair from rewriting the procedure.

---

## 5. Add only what helps and breaks nothing

**Principle.** A change must win something **and** lose nothing that matters. A
change that fixes one kind of task while quietly breaking another is the most
common way a harness rots, and an average can hide it.

**Two stages** (`commands/evolve.md`, `bin/sweep.sh`):

| Stage | Tasks | k | Purpose |
|---|---|---|---|
| **screen** | the theme's tasks that are currently failing | 2 | cheap filter: `/evolve` stops if `gain ≤ 0` or the candidate never loaded |
| **confirm** | every valid task | 3 | the decision: the verdict below |

The screen can only show that a change helps. It cannot show what the change
breaks, because it never runs the tasks that already pass. Only candidates that
survive it pay for the confirm.

**The confirm verdict is computed in code, not by the model** (`bin/score.sh`,
thresholds from `config.yaml`):

| Gate | Rule (on exposed tasks) | Why |
|---|---|---|
| 0 | the data is scorable (§8) | otherwise → `RERUN` |
| 1 | `gain > 0` | it must win something |
| 2 | worst single-task drop ≤ `regression_tolerance` (0.34 = one run in three) | no task may collapse |
| 3 | every task at 1.00 in `base` stays at 1.00 | tasks that never failed get zero tolerance |
| 4 | `net × k ≥ min_net_runs` (2) | a win of one run is a coin flip |
| 5 | the candidate loaded in ≥ 1 `cand` rollout | §4 |

- **Two standards for a drop.** A task at 0.67 is already unstable, so one run
  of movement is probably noise (gate 2). A task at 1.00 has never failed, so
  any drop may be real (gate 3).
- **RECHECK.** At k=3, one unlucky run on a truly reliable task looks exactly
  like a broken task. So a KILL that rests **only** on gate 2 or 3 is re-measured
  on those tasks, and kills only if the same gate fails again.
- **The verdict is `KEEP`, `KILL`, `RECHECK` or `RERUN`.** `RERUN` and
  `RECHECK` never send a candidate to the graveyard: a candidate that was never
  fairly measured has not earned a verdict.

A threshold that a language model applies by reading a prompt gets rounded or
forgotten. A threshold that the scorer applies does not.

---

## 6. Remove only what is measured to cost nothing

**Principle.** Deletion needs the same evidence as addition, pointed the other
way. The item must have been used in the measurement, and removing it must lose
nothing measurable.

**In the code** (`bin/score.sh` in `replace` mode, `bin/harness.py prune`):

| Verdict | Condition | Action |
|---|---|---|
| `REJECT` | the removal loses `≥ min_net_runs`, or breaks gate 2 or 3 | keep it |
| `UNMEASURED` | the item never fired in any `base` rollout | keep it (§4) |
| `ACCEPT` | it fired, and removing it lost nothing | delete it (moved to the graveyard with the reason) |
| `RERUN` | the data is not scorable | decide nothing |

- **Usage chooses what to test; it never decides.** `cortex usage` reads your
  real sessions to suggest which items to test. There is deliberately no
  "unused for N days" deletion: a skill for a twice-a-year situation is not
  dead weight in between.
- **Each item is measured only where it can load.** A path-gated item runs only
  on tasks whose files match its `paths`. An always-on skill runs on the tasks
  where it loaded in past sweeps; with no sweep history yet, it runs on every
  task. Elsewhere, removing it cannot change the result, so measuring there
  would only spend money.
- **After a model change, every item is re-tested**, largest always-on cost
  first. A newer model may already do what a skill teaches, and if the pass is
  stopped early the tests that could save the most have already run. A change
  is detected in code: the pinned model differs from the one the last pass ran
  on.
- **You approve the spending.** A prune pass is a plan with its rollouts, time,
  tokens and cost, estimated from this repo's own history. Nothing runs until
  you approve it, and `cortex prune next` refuses to hand out a sweep before
  that.
- **Deletions happen one at a time**, so each measurement starts from the
  harness as it really is.

---

## 7. Placement is an operator: narrowing and merging

**Principle.** The same knowledge can live in different tiers (§1). Moving an
item into a narrower tier lowers its always-on cost without touching what it
says. It is still a change, so it is measured like one.

- **Narrowing** (`/prune`). An always-on skill whose use is concentrated in one
  folder (`cortex usage`: "narrowing candidate") is rewritten under the same
  name as a path-gated skill, or as a path-scoped rule. The swap is measured as
  a `replace` sweep: the old item out, the narrowed item in.
- **Merging collisions.** Two always-on skills whose descriptions compete for
  the same moment, or two gated items whose paths overlap and disagree, are
  replaced by one merged item, measured the same way.
- **Choosing the tier for a new item** (`/evolve` A4). The choice is based on
  evidence: the files the failing tasks' fixes touched (`fix.patch`).
  - Fixes clustered in one directory → a path-gated skill or a rule, with the
    narrowest glob that covers them.
  - Fixes spread across the repo → an always-on skill tied to a *moment*
    ("before reporting done").
  - Some problems are not a skill at all:

    | Problem | Where it goes |
    |---|---|
    | a fact broken during unrelated work | `CLAUDE.md` |
    | an action that must always run | a hook |
    | a routine approval | `settings.json` |
    | a missing capability | a tool |

    These are made directly, because there is nothing to A/B.
- **Keeping routing true.** Routing lives in each file's frontmatter, and it can
  silently stop being true. `cortex skills` reports:
  - globs that match no file, with a repair proposed from git rename history;
  - names that clash;
  - symlinks that leave the repository;
  - descriptions over the length Claude Code truncates at;
  - a candidate that no task in the sweep could ever load. This is refused
    before any token is spent.

---

## 8. Bad data is not evidence

**Principle.** A number computed from a broken experiment looks exactly like a
real one once it is in the journal. So Cortex separates "the agent failed" from
"the measurement failed", and refuses to decide on the second.

**Invalid is not fail** (`bin/sweep.sh`):

| Event | Recorded as |
|---|---|
| the agent finished; the check decides | valid: pass or fail |
| the agent ran out of time | **valid fail**: it did not solve the task in budget |
| the agent process died (auth, rate limit, 5xx) | **invalid** |
| the check itself hung | **invalid**: the task is broken, not the agent |
| the environment was not ready (`precondition.sh`) | **invalid**, and the agent is never launched |
| the reset failed, or the broken state already passes | **invalid** |

**Unscorable → RERUN** (`bin/score.sh`, gate 0). The sweep is not scored when any
of these hold:
- it was truncated, or did not finish;
- invalid rollouts exceed `max_invalid_rate` (10%);
- a task lacks `k` valid runs in either arm;
- firing is unknown in any rollout;
- the Claude Code version changed mid-sweep, since loading behaviour may differ.

`blocked_because` names the reason. Every results file also records the hashes
of both harnesses and of the task set, so you can later tell whether two sweeps
measured the same thing.

---

## 9. Evidence comes before proposals

**Principle.** Most weeks there is nothing worth learning, and the right
response to that is to spend nothing.

- **The evidence** (`commands/evolve.md` A3):
  - the lessons you logged (`lessons.md`, one line per correction);
  - the tasks that are currently failing;
  - the last `lookback_days` of your own interactive transcripts: repeated
    corrections, tool denials, retry loops;
  - the graveyard and the journal, so a killed idea is not proposed again.
- **A bar before proposing.** A theme must recur `min_theme_occurrences` (3)
  times in lessons, or explain two or more failing tasks. Below that the cycle
  is **BARREN** and costs nothing.
- **A stop rule.** After `stop_after_barren_cycles` (2) cycles in a row with no
  KEEP, `cortex cycle` exits non-zero. By then the tasks have stopped
  discriminating, the harness is already good, or harvesting has stopped.
- **One change per cycle,** written outside `.claude/` so it cannot affect the
  session that is testing it. Two changes in one sweep can only be measured
  together.
- **Rollout traces are not kept.** `bin/sweep.sh` deletes each rollout's output
  after reading what loaded, because it contains everything the agent read. The
  consequence is that Cortex cannot learn by comparing an agent's passing and
  failing runs of the same task. Its signals are failures and *your*
  corrections.
- **A count, not a recollection.** "Recurs three times" was, until recently, a
  model's impression of a folder it could not read whole — one run's transcripts
  are 21 MB. `cortex themes` classifies every lesson line and every transcript
  chunk and then *counts in a shell script*, so `min_theme_occurrences` means
  what it says. Without a key it still counts, over the lessons that named a
  task, grouped by the `area:` line `/harvest` already writes; that is a floor
  rather than a census, and the command says which one you are reading. The
  deterministic half of this had been sitting in the repository unused.

---

## 10. Sized for one person

| Choice | Reason | What it gives up |
|---|---|---|
| one harness lineage, one change at a time | a person runs tens of cycles, not hundreds | combinations: two items that help only *together* each show no gain alone. Workaround: test them as one candidate |
| no population, no merging of alternative harnesses | nothing to merge with one lineage | related work that keeps a population reports that merging specialists can beat each of them (DarwinX); Cortex does not try |
| screen k=2 → confirm k=3, 3–10 tasks | cost: a full cycle is ~38 rollouts, ~150k tokens each | statistical power (§11) |
| one sweep at a time per repository, its rollouts in parallel on one machine (`measurement.parallel`, auto-sized from free RAM); tasks that need services one at a time | one machine, shared services | the speed of a fleet: parallelism stops at the RAM, the CPUs and the API's rate limits |
| you are the teacher (`lessons.md`) | nobody else has solved your tasks | no automated reference solver |

---

## 11. What the gates can and cannot tell you

These are the limits of the current design. They are stated plainly because
reading too much into a KEEP is the main risk.

- **Few runs, few tasks.** At k=3 a task's score can only be 0, ⅓, ⅔ or 1. For
  one noisy task (true pass rate 0.5 in both arms, so no real effect), the
  candidate still wins by two or more runs about 11% of the time
  (7/64). The gates reduce this, but they are **fixed thresholds, not a
  statistical test with a stated error rate**.
- **Effects must be large to be seen.** Published measurements of skills on
  real repositories find typical effects of a few points, which cannot be
  separated from run-to-run noise even with 20+ tasks (Skill Issue). On 3–10
  tasks, Cortex can reliably see large, repository-specific effects (tens of
  points on the tasks a skill touches) and will mostly miss small ones. A KEEP
  of a small effect is weak evidence. (Measuring it properly is planned.)
- **RECHECK is asymmetric.** Regression-only kills are replicated; marginal
  KEEPs are not. This leans towards keeping.
- **The suite is the proxy.** Cycle after cycle on the same few tasks, the
  in-suite score will saturate while work outside the suite does not improve.
  The only remedy is more and newer tasks: keep harvesting, let preflight
  retire tasks, and aim for many tasks and few skills.
- **The whole system is measured, not its parts.** Nothing here shows which
  mechanism is responsible for an improvement.
- **Your harness, your repository.** A harness tuned on one project should not
  be expected to transfer to another.

**Not established for Cortex.** Two findings reported for large-scale harness
evolution are plausible here but have **not** been measured:
- (a) the items that survive measurement are mostly *procedures*, such as
  "check the result against the requirement before reporting done", rather
  than domain knowledge;
- (b) selecting on repeated verification also removes shortcuts that game the
  checker.

Treat both as hypotheses.

---

## 12. A judge you can use without trusting it

§2 bans an LLM judge from the ruler. This section is why a calibrated judge in
the *proposal* layer is not a hole in that ban.

**The two layers are not the same job.** A proposal is a guess about what to
measure; a fitness value is the measurement. A wrong proposal costs a cycle and
is killed by the gates. A wrong fitness value corrupts every decision downstream
and nothing catches it. The rule that follows is not "never use a model" but
**never let a model near the quantity the gates compare** — and that is a line
you can check mechanically: `bin/score.sh`, `bin/preflight.sh` and `bin/sweep.sh`
contain no reference to Jev, and a test asserts it.

**But a free check would be better, so first prove one will not do.** The
expensive failure in Cortex's own recorded history is an *over-scoped* item: a
rule injected into tasks it is not about, where each irrelevant injection is a
chance to break something gate 3 then charges for. Over 984 rollouts, three such
candidates cost 694 rollouts and $77.70 and landed nothing.

The obvious free check is **breadth**: what fraction of the suite the glob
reaches. `reachable_tasks()` computes it already, for nothing. It does not work:

```
KEPT              breadth: 25%, 33%, 100%
BURIED-regression breadth: 52%, 100%, 100%     <- 100% appears in both
```

One item reaches 100% of the tasks it was swept on and is live and healthy.
Another reaches 100% and destroyed the protected set. Breadth cannot tell them
apart. What separates them is the ratio of *relevant* to total injections —

```
KEPT              relevance: 100%, 100%, 100%
BURIED-regression relevance:   8%,  16%,  20%
```

— and the numerator of that ratio requires judging what a task is *about*. That
is the only quantity in the system that needs a model, and it is the argument
for allowing one: not that a judge is convenient, but that a deterministic check
was tried and measurably cannot do it.

**Then make the judge falsifiable.** A calibrated model returns a probability,
which means it can be scored against recorded outcomes like anything else.
`jev/validate.py` does exactly that on Cortex's own corpus and refuses to pass
below 90% agreement, a preserved separation, and monotonic calibration; its
output records the model id it measured, and the client warns when a later
answer comes from a different one. A judge you can re-score after every model
change is a judge you do not have to trust.

**Finally, make it optional in a way a test can check.** Every call site has a
defined keyless behaviour, every artifact stays readable in both modes, and the
suite asserts each row of that contract rather than asking the reader to believe
it. A judge that cannot be switched off is a dependency; one that can is an
accelerator. The difference is not a promise — it is `test/run-tests.sh`.

The honest limit: the separation above is n=6 candidates, three of them the same
theme, all measured on one model. It is a strong lead, not a law, and
`jev/RESULTS.md` records the sample size next to the claim.

---

## Where the ideas come from

Cortex adapts ideas from other work and adds its own. In short:

| Idea in Cortex | Status | Source |
|---|---|---|
| evolve the harness, keep the model fixed; fitness from the task's own verifier; avg@k | adapted | DarwinX (Zhang et al., arXiv 2608.07545) |
| keep a change only if it gains and its regression stays within a bound | adapted | DarwinX ("preserve-and-extend") |
| a cheap screen, then a stricter confirmation | adapted | DarwinX (Cortex screens only currently failing tasks) |
| learning from failures and from a teacher | adapted | DarwinX (Cortex's teacher is the user's own corrections) |
| harness edits go stale when the model improves | idea from | DarwinX App. E; Anthropic, "The new rules of context engineering for Claude 5" (2026) |
| a minimum net number of wins | also in | SkillGen (arXiv 2605.10999) |
| solved tasks must stay solved | also in | HarnessX (arXiv 2606.14249), Self-Harness (arXiv 2606.09498) |
| a journal of rejected edits read by the proposer | also in | SkillHone, WikiSkill, SkillOpt, EvoSkill, AHE, Meta-Harness |
| measured deletion of skills | also in | ASSAY (arXiv 2606.15390), which, unlike Cortex, retires skills whose effect is small |
| context cost as an objective; progressive loading | also in | Meta-Harness (arXiv 2603.28052); SkillReducer (arXiv 2603.29919); Anthropic Agent Skills docs |
| credit only items that were actually used | also in | SkillMAS (arXiv 2605.09341); the inert-edit case in DemoEvolve (arXiv 2605.24539) |
| tasks that fail before the fix and pass after it | also in | SWE-bench (arXiv 2310.06770), SWE-rebench (arXiv 2505.20411), Skill Issue (arXiv 2609.12742) |
| run-to-run noise in coding-agent evaluation | from | Bjarnason et al. (arXiv 2602.07150); PACE (arXiv 2606.08106) on acceptance under noise |
| **exposure-aware gates; never delete what never fired; unknown blocks the decision** | **Cortex** | — |
| **measured tier placement (narrowing) across rules and skills** | **Cortex** | — |
| **live, interleaved control arm on top of the full library** | **Cortex** (as practice) | — |
| **tasks from one developer's own sessions, verbatim prompt, corrections in the check; three-state preflight** | **Cortex** | — |
| **refusing a verdict on incomplete or drifting data; verified resets; task store hidden from the sandbox** | **Cortex** | — |
