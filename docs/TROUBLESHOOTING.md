# Troubleshooting

Ordered by how likely you are to hit it.

---

## 1. Every task gets quarantined

```bash
cortex preflight
```

```
task    broken-state  fixed-state  verdict
01      fail          pass         ok            <- correct
02      PASS          pass         QUARANTINE
03      fail          FAIL         QUARANTINE
```

A valid task must **fail before the fix** and **pass after it**.

### `broken-state = PASS`
Your `check.sh` passes even without the fix. Almost always because it's too broad:

```bash
pytest -q                                  # BAD  - whole suite, passes trivially
pytest tests/test_broker.py::test_t2 -q    # GOOD - the specific test that was red
```

### `SKIP (environment not ready)` — exit code 3

`precondition.sh` says a service the task needs is not running. **Nothing was
quarantined.** Start the stack and run preflight again. If the precondition
itself is wrong, fix or delete it — a task with no services needs no
`precondition.sh` at all.

### `fixed-state = FAIL`
One of:
- the patch no longer applies (repo moved on) — re-harvest the task
- the patch is missing a file the fix **created**: it was written with
  `git diff`, which leaves out untracked files. Re-write it with
  `cortex harness fixpatch --base <base_sha> > .evolve/tasks/NN/fix.patch`
  (new tasks: `cortex task new` writes it for you)
- `check.sh` can't run at all — missing dependency, wrong path, tool not installed
- the check depends on a service that isn't up — record it in `services:`

Test it directly:
```bash
bash .evolve/tasks/01/check.sh; echo "exit=$?"
```

### `QUARANTINE (the check needs the fix's own test code …)`
The fix added or changed test code, and `check.sh` runs **that** test. Preflight
passed the fixed state (the patch brings the test along) but fails it without the
fix's test code — a rollout agent never writes that same file. Test data the fix
adds (a golden file, a fixture) is not stripped: an exporter's golden file is part
of the job, not the fix's own test. Copy the test
into the task folder, run the copy from `check.sh`, then move the task back and
preflight again:
```bash
cp tests/test_new.py .evolve/tasks/_broken/07/test_check.py
# check.sh:  cp "$(dirname "$0")/test_check.py" tests/test_cortex_check.py
#            python3 -m pytest -q tests/test_cortex_check.py
mv .evolve/tasks/_broken/07 .evolve/tasks/07 && cortex preflight
```

---

## 2. Scores that don't make sense (stale build caches)

**Suspect this first.** It is silent and it poisons everything downstream.

An edit of identical byte length within the same second can leave Python reusing
the **old** `.pyc`: bytecode invalidation compares (mtime, size), and `a - b` →
`a + b` matches on both.

Cortex handles Python (`PYTHONDONTWRITEBYTECODE=1` + purging `__pycache__`), but
if your project has its own cache, clear it inside `check.sh`:

```bash
rm -rf .next/ target/ dist/ node_modules/.cache
```

Symptom: preflight says `fixed-state FAIL` even though applying the patch by
hand clearly works.

---

## 2b. `cortex score` says `scorable: false`

Read `blocked_because` — it names the cause. **Do not decide anything on an
unscorable sweep.** Re-run it after fixing the cause.

| `blocked_because` says | Means | Fix |
|---|---|---|
| `sweep was truncated at the run budget` | hit `max_runs_per_cycle` (sweeps now refuse up front, so this means an old results file or a bug) | raise the budget, or lower `k`/task count |
| `invalid rollout rate N% exceeds limit` | agents died for non-capability reasons | check `invalid_reasons`: `agent_rc_*` = API/auth/rate-limit; `broken_state_passes_check` = the task's `check.sh` is too broad; `reset_failed` = disk or git trouble |
| `tasks not measured under both variants` | asymmetric data | re-run; the listed tasks have fewer than `k` valid rollouts in one arm |
| `sweep did not finish` | still running, or it crashed | `tail -f .evolve/runs/*.log` |
| `no task was measured` | the results hold no rollouts at all | check `--tasks` named real task ids; re-run |

---

## 2c. A skill disappeared

Measuring never moves a live skill: `cortex sweep --replace` builds both arms
from a snapshot. A skill only leaves `.claude/skills/` through `cortex bury`,
and then it is in `.evolve/graveyard/`, with the reason in `BURIED.md`:

```bash
ls .evolve/graveyard/
cat .evolve/graveyard/<name>*/BURIED.md
```

To bring one back, copy it to `.evolve/candidate/` and measure it like any new
skill, or move it back by hand if you are sure.

If `cortex status` prints `!! N SKILL(S) PARKED FOR ABLATION AND NOT RESTORED`,
the repo was set up by an older Cortex, which moved skills out to measure them.
The skill is intact in `.evolve/ablation/`:

```bash
cortex restore <name>
```

## 2d. A sweep refused: `needs N rollouts but max_runs_per_cycle is M`

The sweep counted `tasks × k × 2` before starting and it did not fit the budget.
Nothing was spent. (`nothing to measure` is the same refusal for the opposite
reason: none of the `--tasks` exists.) Raise `measurement.max_runs_per_cycle` in
`.evolve/config.yaml`, or pass fewer `--tasks`.

## 2e. `/prune` says `UNMEASURED`

The skill never fired in any rollout, so no task exercises it and the suite
cannot tell whether removing it costs anything. The skill is kept. To make it
measurable, `/harvest` a task where it should fire.

If `verdict_because` says the results file does not record which skills fired,
the sweep was run by an older Cortex. Run it again.

---

## 2f. Every rollout failed and the candidate was killed

Check whether your stack was up for the whole sweep:

```bash
cortex score | jq -c '{verdict, invalid, invalid_reasons, blocked_because}'
```

- `precondition_failed` → the environment was down. The verdict will be `RERUN`,
  not `KILL`, and nothing was decided. Start the stack and sweep again.
- `invalid: 0` but everything failed in **both** arms → you have no
  `precondition.sh`, so a dead service was recorded as a capability failure.
  Add one (`templates/task/precondition.sh`) before trusting that verdict.

A sweep that fails identically in both arms is almost always the environment,
not the candidate. Candidates rarely make things uniformly worse.

---

## 2g. `sweep: REFUSED: …`

The sweep stopped before spending anything, and the line says why. Every
pre-spend check prints this marker; `cortex sweep … --dry-run` runs them all
without launching anything.

| The line says | Do |
|---|---|
| `could never load` | no task in this sweep touches a file matching the candidate's `paths`. Widen `paths`, or sweep tasks from that area (a screen on failing tasks only sees those tasks) |
| `older than min_claude_version` / `cannot read claude --version` | update Claude Code, or fix `claude` on PATH. Path-gated loading was verified on a specific version |
| `is both a live skill and a live rule` | rename one; firing could not be attributed |
| `points outside the repository` | a symlink in `.claude/skills` or `.claude/rules` leaves the repo; replace it with the file itself |
| `invalid task id` / `not a commit id` | a task folder name or its `base_sha` is malformed |
| `lock held` | another sweep is running. It is left untouched — a refused sweep never deletes the running one's sandbox (a preflight has its own lock and does not block sweeps) |
| `--parallel must be auto or a number` / `cannot size the parallel workers` | `--parallel` or `measurement.parallel.rollouts` is not `auto` or 1–64 |

## 2h. `cortex skills` reports a DEAD glob

An item's `paths` match no tracked file any more — usually a renamed directory —
so it can never load, and nothing else would tell you. When git history explains
it, the warning prints the fix:

```
warning: rule api: DEAD glob 'services/api/**' matches no tracked file — repair: 'services/api/**' -> 'services/backend/**' (renamed in 3f2a9c1e04)
```

Apply exactly that edit to the file's `paths`, run `cortex skills` again, and
journal it as `kind: path-repair`. Never bury a dead item as "unused": it never
had the chance to be used.

## 2i. A skill or rule never loads, and `cortex skills` says `quote it`

`paths:` entries and values starting with `*`, `{`, `[`, `&` or `!`, or
containing `": "`, are YAML syntax. Claude Code's parser rejects the whole
frontmatter and the item silently never loads (or a rule loads everywhere).
Quote them: `- "src/**/*.py"`.

## 2j. `/prune` stops at a plan and does nothing

A pass waits for your approval by design. `cortex prune status` shows the plan
with its rollouts, time, tokens and cost. Answer "yes" in the session (or run
`cortex prune approve`), or `cortex prune cancel`. `cortex prune next` refuses
to hand out a sweep until then.

## 2k. `/prune` marks items `skipped` or `blocked`

- `skipped` — no task can load the item, so a removal could only come out
  `UNMEASURED`. `cortex usage` shows where it is used; harvest a task there.
- `blocked` — it needs more rollouts than `measurement.max_runs_per_cycle`.
  Raise it, or leave that item for another pass.

## 2l. `/prune` tested more than `prune.max_items`

The pinned model changed since the last pass (`cortex prune plan` says
`MODEL UPGRADE`): then every item is tested. `max_items` limits routine passes
only. `cortex prune cancel` if you want to run it later.

## 2m. The verdict is `RECHECK`

Not a KILL — do not bury. Every gate passed except a per-task regression (gate 2
or gate 3) on the tasks in `recheck_tasks`, and at k=3 that is as likely to be
one unlucky run as a real break. Sweep just those tasks again:

```bash
cortex sweep --candidate <name> --tasks "<recheck_tasks>" --phase recheck --dry-run
cortex sweep --candidate <name> --tasks "<recheck_tasks>" --phase recheck --detach
```

`cortex score` then reads the recheck together with its confirm (`confirm_file`)
and gives the final verdict. `RERUN` after a recheck means the recheck itself
could not be trusted (invalid rollouts, a flagged task missing) or no confirm
with the same candidate and harness precedes it.

## 2n. `cortex promote` refuses: "no confirm has kept it"

A candidate goes live only after a **confirm** sweep (every task at `k_confirm`),
or its recheck, says KEEP, or after a `/prune` swap says ACCEPT. A screen's verdict
is `CONFIRM` at best: it means "run the confirm". Run it (`/evolve` does). Use
`--force` only if you know why the measurement does not apply, and write why in the
journal.

## 2o. A task shows `exposed: false`

The candidate never entered the agent's context in any `cand` rollout of that
task: a path-gated skill that never became visible, or a rule whose files were
never Read there. Both arms ran the same harness, so its delta is noise and no
gate reads it (`unexposed` lists them). Expected for tasks outside the
candidate's area. If it is a task the candidate was *written for*, the trigger
is wrong — compare its `paths` with the files the task's fix touches.

## 2p. `task(s) NN never passed in any rollout of either arm`

Neither arm solved that task even once. Either it is too hard for the agent, or its
`check.sh` accepts only the fix that was harvested: it greps for the class name that
fix picked, or the exact wording of its docs row or changelog line. A rollout agent
writes different but correct code and fails such a check in both arms, so no
candidate can ever gain there. Read the check against /harvest rule 6: check the
behaviour and run the project's own tools (the linter, the test), never grep for one
fix's wording.

---

## 2q. Sweeps after raising `measurement.parallel`: invalid rollouts, a slow machine

Running rollouts at once changes only the speed, never the scores (the same jobs,
the same interleaved order). What it can hit:

| What you see | Why | Do |
|---|---|---|
| `invalid_reasons` like `agent_rc_1`, verdict RERUN | too many agents at once met the API's rate limits (or your plan's usage limit) | lower `max_rollouts`, or set `rollouts` to a number (e.g. 4) |
| `invalid_reasons: {"timeout_under_load": N}` | agents ran out of time while the machine had more runnable work than CPUs. Those rollouts are **invalid**, never failures — the candidate is not blamed for a slow machine | raise `cpus_per_rollout` (the score suggests a value), or lower `rollouts` |
| verdict RERUN, `the machine was oversubscribed in N of M rollouts` | several times more runnable work than CPUs: every rollout ran slowed down, so timings say nothing | as above. A *note* instead of a verdict means it was mild: time lost, nothing else |
| the machine gets slow or swaps during a sweep | `auto` saw a lot of free RAM at the start, then you opened something heavy; or your checks are heavier than `ram_per_rollout_mb` | lower `ram_percent`, or raise `ram_per_rollout_mb` |
| a task with a `precondition.sh`, or one marked `exclusive: true`, runs one rollout at a time | by design: it needs something machine-wide | set `with_services: true` only if each rollout gets its own services; `exclusive: false` in its task.yaml if you know it is safe |
| `sweep: 8 rollouts, 1 at a time — auto: available RAM unknown…` | `auto` could not read the free memory on this system | set `rollouts` to a number |

`cortex doctor` prints what `auto` resolves to right now; every sweep logs it on its
first line and records it in its results (`workers`, `parallel`).

### `sweep INCOMPLETE: N of M rollouts recorded`
Every job writes exactly one row; fewer rows than jobs means some never ran — the job
queue was deleted (a `cortex clean` during the sweep, a full disk under `sandbox_root`)
or a worker died. The sweep ends `incomplete`, **not** done, `cortex score` refuses it
(RERUN) and names the planned tasks with no rollout. Fix what broke and sweep again.
A file that ends `done` has every planned task in it: that is what makes a verdict
readable at all.

### `ok (exclusive: …)` — preflight marked my task
Its check failed when two copies ran at the same moment, or while other checks ran
beside it, and passed alone: it holds something machine-wide (a fixed port, a fixed
path outside the repository, a shared database). `exclusive: true` went into its
`task.yaml`, and its rollouts now run one at a time. Write `exclusive: false` there
if you know better — nothing overrides a value you wrote.

### `SKIP (busy: a running sweep holds the machine-wide resources it needs)`
A task that runs alone could not be checked because a sweep was using the same
services or port. Nothing was quarantined; run preflight again when the sweep is done
(exit code 3, as for a stopped service).

### A quarantined task, and why
`.evolve/tasks/_broken/<id>/QUARANTINED.txt` holds the table line and the diagnosis,
written when it was moved. `.evolve/runs/preflight.log` holds every decision of the
last preflight, written as it was made — so an interrupted run (a command timeout,
Ctrl-C) still leaves its reasons behind.

### `preflight: another preflight is already running`

Only one preflight runs at a time (they move tasks into `_broken/`). It no longer
waits for sweeps: a `/harvest` can check its task during a sweep. A sweep that
starts while a preflight is running waits for it before copying the tasks.

## 3. Rollouts hang until the timeout

A headless `claude -p` that hits an interactive permission prompt waits forever,
then gets killed and scores a **false FAIL** — which silently corrupts the score.

- Check `permission_mode` in `.evolve/config.json` covers what the task needs.
- Watch the live log: `tail -f .evolve/runs/sweep.log`
- **Never** use `bypassPermissions` for unattended fan-out. These rollouts have
  real tool access in a real sandbox.

---

## 4. Did a rollout touch my repository?

It cannot. Sandboxes are `git clone --no-hardlinks` with their own object store,
and `origin` is removed right after cloning, so a rollout has no path back.
This is asserted by `./test/run-tests.sh git_isolation`.

If you suspect otherwise:

```bash
git branch -a && git tag -l && git stash list && git log --oneline -5
cortex clean               # remove sandboxes under /tmp
```

`cortex clean` refuses a `sandbox_root` that is too shallow, and only ever
deletes its own named subdirectories inside it.

Historical note: earlier versions used `git worktree`, which **shares `.git`** —
a rollout could delete a branch in the real repo. Sandboxes are now clones with
their own object store and no `origin`. If you are on an old copy, upgrade before
running a sweep.

---

## 4b. A task always scores the same no matter what the agent does

Your `check.sh` is almost certainly testing a **shared running service** instead
of the sandbox's code.

```bash
curl http://localhost:8000/health        # BAD — that server runs MASTER's code
pytest tests/test_thing.py::test_x -q    # GOOD — runs the sandbox's code
```

The agent edits files in `/tmp/cortex-evolve/cand`. A daemon started from your
master checkout has never seen those files, so the check returns the same answer
either way and the task measures nothing.

Cortex isolates **code**, not **runtime**. Prefer hermetic tasks; if a task needs
a service, keep it read-only and assert it in `precondition.sh`.

---

## 5. Nothing ever gets kept

In order of likelihood:

1. **Tasks don't discriminate** → `cortex preflight`
2. **The candidates never fire** → `cortex score` shows `candidate_fired_runs: 0`,
   `gates_failed` names `gate5`, and `notes` says why. Compare
   `candidate_visible_runs`:
   - **never became visible** (a path-gated skill) → its `paths` match no file the
     rollouts read or wrote. Compare them with the tasks' `fix.patch`.
   - **visible but never invoked** → the `description` does not name the moment.
   - **a rule, never fired** → no rollout **Read** a matching file. Rules are not
     triggered by Write, nor by `cat` through Bash.
   Fix the trigger, not the procedure — the body was never tested.
   `candidate_fired_runs: null` is different: firing is **unknown** (the output
   could not be read) and the verdict is `RERUN`.
3. **Real gains die on one task's drop** → the verdict should be `RECHECK`, not
   `KILL` (2m). If you see `KILL` with only `gate2`/`gate3` in `gates_failed`,
   it came from a screen, or the recheck replicated the drop.
4. **The noise band is wider than the gains** → raise `k_confirm` to 5 and see if
   the baseline itself is stable between runs. If it isn't, no amount of
   machinery will help.
5. **The skills folder is already good** → a correct and common outcome
6. **The model already does it** → run `/prune`; you may be able to delete some
7. **The rollouts can read the answers** → they cannot: sweeps hide `.evolve/`
   from the sandbox. If your tasks' checks or fixes live elsewhere in the
   repository (a `solutions/` folder, a committed transcript), both arms read
   them and the gain vanishes. Keep the answers out of the tracked tree.

After two consecutive cycles with no KEEP, `/evolve` stops and says so. Believe it.

---

## 6. `/evolve` says "nothing to learn" every week

The bar is 3+ occurrences of one theme. If you're not hitting it:

- you may not be running `/harvest` (check `cortex status`)
- your `lessons.md` entries may be too specific to cluster — write *what you did
  wrong*, not the full context
- genuinely nothing recurring may be happening, which is a good sign

---

## 7. `cortex: command not found`

```bash
ls -l ~/.local/bin/cortex
echo $PATH | tr ':' '\n' | grep -c '.local/bin'
```

If 0, add to `~/.bashrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## 8. Checking the environment

```bash
cortex doctor
```

Needs `git`, `jq`, `claude`, `timeout`. All four are required by `sweep.sh`.
It also reports whether Jev is reachable and whether this repo's command files
are current — see section 11.

---

## 11. Jev

Jev is optional. **Every row below leaves Cortex behaving exactly as it does with
no key at all**, and none of them can change a verdict: the gates, `cortex score`,
`check.sh` and preflight contain no Jev code path. Full contract in
[`JEV.md`](JEV.md).

### `relevance: unavailable`

Not an error. `cortex scope` printed its deterministic half (`injected into N of
M tasks`) and could not compute the semantic half. The reason is in the
parentheses:

| It says | Meaning |
|---|---|
| `(jev disabled)` | `JEV_ENABLED` is 0, or no `.env` sets it. The built-in default is off |
| `(no key)` | the switch is on but `JEV_API_KEY` is empty |
| `(invalid key)` | a 401. Three causes, indistinguishable from the status alone: the key is wrong; the key is for the **other route** (a `vck_` gateway key sent to `api.typesafe.ai`, or the reverse); or the TypeSafe account is **waitlisted** — TypeSafe is invite-only and an unprovisioned key is rejected exactly like a bad one. Check `cortex config` for the effective `jev.base_url` before assuming a typo |
| `(refused — …)` | a 403. On TypeSafe direct: no key was sent at all. On AI Gateway: usually `customer_verification_required` — it needs a credit card on file before routing anything, even though Jev is free. Add one at [vercel.com/account/ai](https://vercel.com/account/ai) |
| `(malformed request)` | a 422. A bug — please report it with the `.evolve/jev/` line |
| `(rate limited)` | a 429 that outlived its retries |
| `(overloaded)` | a 529 |
| `(timeout)` / `(unreachable …)` | network. `jev.timeout_s` bounds it |
| `(… max_requests_per_cycle …)` | the census refused to start rather than become a sample. Raise the budget or narrow the question |

Exit code is 0 in every case, and A5 continues.

### "Which endpoint should my key go to?"

Two routes, the same model, the same request and response format:

| Key from | `JEV_BASE_URL` | `JEV_MODEL` |
|---|---|---|
| Vercel AI Gateway (`vck_…`) | `https://ai-gateway.vercel.sh/typesafe/v1/systemone` | `typesafe-ai/jev` |
| TypeSafe console | `https://api.typesafe.ai/v1/systemone` | `jev-latest` |

Crossing them gives `401 invalid key`, which reads exactly like a typo. Check
with `cortex config` — it prints the effective value and where it came from.

Two quick probes that cost nothing:

```bash
# is the key good at all? (no model call, no billing)
curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $JEV_API_KEY" \
  https://ai-gateway.vercel.sh/typesafe/v1/models      # 200 = a good gateway key

# can it actually route a request?
cortex jev doctor
```

### "I set a key and nothing happened"

A key alone does not turn Jev on: the default is `enabled: false`. Put
`JEV_ENABLED=1` in your `.env`. `cortex doctor` says so explicitly when it finds a
key with the switch off:

```
jev        off — jev.enabled is false (a key is present — set JEV_ENABLED=1 in .env)
```

### "The Jev steps do nothing" / `cortex scope: unknown command`

Your repo's command files predate this Cortex, so `/evolve` is still running the
old A3/A4/A5. `cortex doctor` names it:

```
commands   evolve.md is older than this Cortex (yours is customised) — Jev steps inactive
           run: cortex init /path/to/repo
```

Re-run `cortex init` in **every** repo after upgrading Cortex. If you edited a
command file, `init` keeps your copy as `<name>.md.bak-<timestamp>` and installs
the new one — merge your edits back from the `.bak`.

### "I turned Jev off and my old `.evolve/` still works"

It does, by design. Jev writes one optional `jev:` line in `.evolve/journal.md`
(prose to every keyless reader), an optional `jev_rank` field in
`.evolve/prune-plan.json` (ignored when absent), and `.evolve/jev/*.jsonl` (a new
directory nothing requires). Skills, rules, tasks, results and baselines have no
Jev in them at all — a skill promoted with Jev on is byte-identical in form to
one promoted without it.

### "I turned it on mid-cycle"

Also fine, in both directions. No Jev code runs inside a sweep, so a verdict can
never be affected. Every Jev contribution is written at the moment it is made and
is optional to every later reader: if A3 ran with Jev and D5 without, D5 simply
writes a journal entry with no `jev:` line. A `/prune` plan built with Jev and
executed after a switch-off runs the same approved items, in the order it printed.

### `jev: answering model is X, J0 validated Y`

The `jev-latest` alias moved. Jev's calibration was validated against a specific
version, so this warns once per run and keeps going — a stale calibration
degrades a hint, never a verdict. Either re-validate:

```bash
python3 jev/validate.py --corpus jev/corpus
```

or pin the old version with `JEV_MODEL=jev-1.13.0` in your `.env`.

### The session-end hook got slow or noisy

That outranks the feature. Lower `JEV_TIMEOUT_S` (the hook takes the smaller of
that and its own 5-second ceiling), raise `JEV_HARVEST_THRESHOLD` to make it
nudge less, or set `JEV_ENABLED=0` to return it to `git status | wc -l`. A hung
endpoint already falls back to that line on its own.

### Is my key about to end up in a rollout?

No. `.env` is gitignored, and `make_sandbox()` clones the repo, so an untracked
file cannot follow it. The one path that could is
`environment.harness_files`, which copies arbitrary repo paths into **both**
arms — and `cortex config --check` refuses a `.env` there by name.

---

## 9. Reading a sweep while it runs

```bash
tail -f .evolve/runs/sweep.log                    # live rollout log
wc -l .evolve/runs/results.jsonl                  # progress
cortex score                                      # partial scores, any time
```

`cortex score` works on partial data — `"finished": false` tells you the sweep
is still going.

---

## 9b. Running the test suite

```bash
./test/run-tests.sh              # every assertion (642 at the time of writing), ~5 min
./test/run-tests.sh -j auto      # the same, 8 test functions at a time: ~45 s
./test/run-tests.sh locking      # just one group
CORTEX_TEST_ROLLOUTS=4 CORTEX_TEST_PREFLIGHT=4 ./test/run-tests.sh -j auto
                                 # every sweep and preflight inside the tests 4 at a time
```

No API calls — rollouts are driven by a stub agent each test controls, and Jev's
call sites by `test/jev-stub.py`. `test/jev-contract.py` additionally checks both
of them against the published TypeSafe schema vendored at `test/jev-openapi.json`,
so the stub cannot drift into answering in a shape the real API never sends. The suite sets `JEV_ENV_FILE=/dev/null` so it
cannot read your own key or your own settings. If you change anything in `bin/`,
run this first. The tests pin `measurement.parallel` to
1 so each sees one fixed order; the last line runs them all again in parallel.

---

## 10. Starting over

```bash
cortex clean                    # sandboxes only, evidence kept
cortex clean --runs             # also discard past results
mv .evolve/tasks/_broken/* .evolve/tasks/    # un-quarantine to repair by hand
```

Never delete `journal.md`. It's the only record of why your skills folder looks
the way it does.
