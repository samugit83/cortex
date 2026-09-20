---
description: Capture this session as a test case while the environment is still warm
---

# /harvest — capture, do not evolve

You are at the end of a working session. The environment still exists:
containers are up, the database is seeded, you know what broken looked like
and what fixed looks like. That state is expensive to rebuild later and free
to capture now. Capture it. **Do not** propose skills, do not run evolution,
do not spend more than a minute.

---

## Step 1 — FILTER (do this first, bail fast)

Most sessions are worth nothing. Check exactly two things:

- **A.** Did something go from broken to working? A failing test went green, a
  build started passing, a service came up, an endpoint started answering.
- **B.** Did the user correct me? Once is enough: "you forgot…", "CI still fails
  because…", "we never do it that way", a check they pasted that I had to fix.
  One correction per session is exactly how a recurring mistake shows up across
  sessions.

If **neither** is true: run `cortex skills --quiet` (zero tokens, writes
nothing), print `nothing to harvest` — plus its `check:` line if it reported any
error or warning — and **STOP**. Write no files. This is the expected outcome for
most sessions and is not a failure.

If only **B** is true: skip to Step 3.

---

## Step 2 — CAPTURE THE TASK

Pick the **single** clearest broken→working transition in this session. One task.

### 2a. Work out the two states

```bash
git status --porcelain
git log --oneline -5
```

- **Fix is uncommitted** → `base_sha` = current `HEAD` (`git rev-parse HEAD`).
- **Fix is committed** (by you or the user, during this session) → `base_sha` = the
  commit *before the first* commit of this session's work. A first attempt and a
  corrected one are two commits: `base_sha` is the commit below **both** — the state
  the user asked you to start from, not your first attempt. Uncommitted edits on top
  are part of the fix too.
- **Harvesting late** — this session's work is committed and **other work was
  committed after it** (another session, a teammate): also note the **last** commit
  of this session's work, and pass it as `--head` below. Without it, fix.patch would
  carry everything since `base_sha`, other people's work included.

`base_sha` must name the **broken** state the user started from. Get this wrong and
every later measurement is meaningless: from `HEAD~1`, a rollout would start from your
half-finished first attempt instead of the real problem.

Delete scratch files you made (debug scripts, notes) first — they would ride along.
Then let Cortex write the mechanical half of the task — **one command**:

```bash
cortex task new --base <base_sha> --title "<short title>"
# harvesting late:  cortex task new --base <base_sha> --head <last commit of this session> --title "…"
```

It creates the next free `.evolve/tasks/NN/` (it prints `NN`) with:
- `fix.patch` — every change from `base_sha` to the working tree: your commits, your
  uncommitted edits **and the files you created** (with `--head`: exactly the
  commits from `base_sha` to it);
- `task.yaml` — id, title, base_sha, timeout, today's date.

Never write these two by hand. `git diff` misses the files a fix creates, and a
hand-picked file list misses whatever you forgot; either one gives a task whose
"fix" no longer fixes anything. `task new` also refuses a `base_sha` that is not in
the history of `HEAD`.

### 2b. Write the rest of the folder

```
.evolve/tasks/NN/
  task.yaml         (written by `cortex task new`)
  fix.patch         (written by `cortex task new`)
  prompt.txt        the user's ORIGINAL request, verbatim — not your paraphrase
  check.sh          the exact command that proves it works
  precondition.sh   OPTIONAL — asserts services are up. Omit if none are needed.
  notes.md          one line: what was actually wrong
```

Write `precondition.sh` **only** if the task needs a running service. It asserts
the environment is ready, never that the code is correct, and a failure marks the
rollout *invalid* rather than failed — so a stack that dies mid-sweep cannot be
mistaken for a bad candidate. Copy the template from
`templates/task/precondition.sh`.

`task.yaml`, as `cortex task new` writes it:
```yaml
id: NN
title: <short title>
base_sha: <sha of the BROKEN state>
timeout_s: 600
harvested: <YYYY-MM-DD>
exclusive: true     # ONLY when it needs the machine to itself (see below)
```

Add `exclusive: true` yourself when the check — or the code it runs — uses
something **machine-wide**: a fixed port, a fixed path outside the repository, one
shared database. Sweeps run several rollouts at once, and two copies of such a task
would break each other; marked exclusive, its rollouts run one at a time. Preflight
also finds these on its own (it runs your check twice at the same moment) and writes
the flag, so a wrong guess here is not fatal — but knowing it saves a cycle.

Prefer tasks that need **no running services** — they are faster and cannot be
disturbed by the environment. Cortex does not start containers for you. If a task
does need one, add `precondition.sh` to assert it is up (and optionally to start
it); both it and `check.sh` must finish inside `measurement.check_timeout_s`.

**Before writing `check.sh`, list the user's corrections in this session** —
every "you forgot…", "CI still fails because…", "we never…". Each one becomes a
line in `check.sh` that fails when the mistake is repeated. The same list becomes
the lesson in Step 3. A check that tests the original request but not a
correction lets every rollout repeat the mistake you were corrected for, and the
skill that would fix it can never show a gain.

`check.sh` rules, in order of importance:

0. It runs **with the repository under test as its working directory** — in a
   sweep, a clone at `base_sha` plus the rollout agent's changes. It must never
   `cd` anywhere: not to the repo root, not relative to `$(dirname "$0")`. A copy
   of the task folder, somewhere else, is what runs; the only use of
   `$(dirname "$0")` is reaching files stored in that folder.
1. It must exit **0 = solved**, non-zero = not solved. Nothing else.
2. It checks **everything the user asked for in this session, corrections
   included.** If they said "amounts must stay integer cents" or "you forgot the
   CHANGELOG entry", the check fails when that is not done. A check that covers
   only the first symptom passes a rollout that repeats your mistake — and then
   no skill about that mistake can ever be measured.
3. It must be **specific** — `pytest path/to/test_x.py::test_y`, not `pytest`.
   A whole-suite command also fails on unrelated breakage and blurs the signal.
4. It uses only what exists at `base_sha` plus files in its own task folder. A
   sweep runs it from a **copy** of the task folder, with the repository (at
   `base_sha`, plus the rollout agent's changes) as the working directory:
   - a test that **already existed** at `base_sha` — run it by its path;
   - a test **you wrote in this session** is part of the fix, and a rollout
     agent will not write that same file. Copy it into the task folder and
     run the copy, beside the repo's own tests so it gets the same config:
     ```bash
     cp "$(dirname "$0")/test_check.py" tests/test_cortex_check.py
     python3 -m pytest -q tests/test_cortex_check.py
     ```
   - a file that **must have changed** (a changelog, a registry, docs):
     ```bash
     if git diff --quiet <base_sha> -- CHANGELOG.md; then echo "CHANGELOG.md not updated"; exit 1; fi
     ```
     (not `! git diff --quiet …`: under `set -e` a `!` line never stops the script)
5. It must not depend on anything outside the repo that you did not record.
6. It passes **any correct fix, not just yours**. A rollout agent writes different
   but correct code: other names, other wording. Check what the user asked for —
   behaviour, a test, the project's linter or CI command, a file that must exist or
   change — never your incidental choices: a class or function name you picked,
   the wording of your docs row, the text of your changelog line. When the
   project's own tool caught the mistake (the linter, a test), run that tool; do
   not re-implement it with `grep`. A check that greps for your own phrasing fails
   every other correct fix, and measures nothing.
7. It checks **the request and the corrections, and nothing else you happened to
   do.** Tidying you threw in, a changelog line nobody asked for, a rename you
   preferred: none of it belongs in the check. A rollout that does the job the user
   asked for must pass. Each extra condition is one more thing every rollout has to
   get right, and a task that nobody can pass measures nothing — `cortex score`
   reports such tasks as *never passed in any rollout of either arm*.

### 2c. VERIFY THE TASK DISCRIMINATES — non-negotiable

A task that does not fail on the broken state measures nothing. Prove it now,
in a throwaway checkout, never in the user's working copy:

```bash
cortex preflight
```

It runs every check exactly as a sweep will: from a copy of the task folder, in a
throwaway checkout of `base_sha` — first broken, then with `fix.patch` applied.
Running `check.sh` yourself in your working copy proves nothing: the fix is
already in it. Never `git stash`, `git checkout` or `git reset` the user's working
copy to "see the broken state": their uncommitted work is in it, and preflight
already shows you that state.

A task that fails only *beside other checks* is never quarantined for it: preflight
checks it again alone and, if it passes, keeps it and marks it `exclusive: true`.
Every decision is also in `.evolve/runs/preflight.log`, and a quarantined task keeps
its reason in `.evolve/tasks/_broken/<id>/QUARANTINED.txt`.

If your new task is quarantined, preflight says why, under its line. You get
**one** repair:

- `the check needs the fix's own test code` — rule 4: copy the test you wrote
  into the task folder and point `check.sh` at the copy;
- `passes BEFORE the fix` — the check does not test the problem (or it `cd`s into
  your working copy, rule 0);
- `fails WITH the fix` — the lines it prints are the check's own output: usually a
  wrong path, a `cd`, or a test name that does not exist at `base_sha`.

Fix `check.sh` (never `fix.patch`, never `task.yaml`'s `base_sha`), put the task
back with `mv .evolve/tasks/_broken/NN .evolve/tasks/NN`, and run
`cortex preflight` again. One repair is one edit of `check.sh` and one preflight
run — not a series of rewrites, and never a check that stops testing a correction
just to get through. Quarantined a second time → delete **that task only**
(`rm -rf .evolve/tasks/_broken/NN`; never the whole `_broken/`, it may hold other
tasks) and say so plainly in the report. Step 3 still applies.

A bad task is worse than no task: it will silently corrupt every score from here on.

---

## Step 3 — CAPTURE THE LESSON

Whenever the user corrected you (Step 1 **B**, even once) — whether or not a task
survived Step 2. Append **one line per correction** to `.evolve/lessons.md`:

```
2026-09-17 | task 07 | said the fix worked without running the test | run the test first
```

Rules:
- One line. No essay, no analysis.
- Write it **even when a similar line is already there**. A repeat is not a
  duplicate: it is the recurrence `/evolve` counts before it tries a skill.
  The one exception is your **own** line: when `/harvest` runs again in the same
  session, change that line's `no task` to the new task id instead of adding a
  second line for the same correction.
- Put the id of the task you harvested in this session after the date (`task 07`),
  or `no task` when there is none: `/evolve` screens a candidate on exactly the
  tasks its theme came from.
- Write what you **did**, not what you should have done differently in general.
- **Do not write a skill.** That is `/evolve`'s job, and it only earns one after
  the same lesson has appeared three times. A lesson is evidence; a skill is a
  conclusion. Do not jump.

---

## Step 4 — CHECK THE ROUTING, THEN REPORT

Two zero-token commands. The first re-validates every skill and rule (their
tiers, their `paths`); the second says which of them cover the files this
session's fix touched:

```bash
cortex skills --quiet
cortex harness touching .evolve/tasks/NN/fix.patch      # only if you harvested a task
```

Append the `area:` line it prints to that task's `notes.md` — `/evolve` reads it:
a task that still fails inside the area of a live skill or rule is evidence that
item is not working there.

Do **not** fix anything the check reports: that is `/evolve` and `/prune`'s job.
Just carry it into the report.

One line. Nothing more. It always says how many lessons you wrote; `+ 0 lessons`
after a session in which the user corrected you means Step 3 was skipped — go
back and do it:

```
harvested task 07 + 1 lesson   area: api-migrations
```
or, when the check found problems:
```
harvested task 07   check: 1 error, 2 warnings — run `cortex skills`
```
or, when the task was quarantined twice and deleted (the lesson still counts):
```
task 07 deleted: the check fails with the fix (wrong path)   + 1 lesson
```
or, only when Step 1 found nothing:
```
nothing to harvest
```
