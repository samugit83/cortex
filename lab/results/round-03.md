# Round 3 — exporters (C01, C02, C03), run by the autopilot

## Sessions

| Session | First attempt | Corrections | Task | Lesson | Audit of the harvested check |
|---|---|---|---|---|---|
| C01 XML | exporter right, **no docs row, no golden file** | 1 | 09 (late: re-harvested after fix 1) | ✔ (two lines, see fix 5) | **WEAK**: greps for its own docs wording |
| C02 Markdown | exporter right, **no docs row, no golden file** | 1 | 10 (late: re-harvested after fix 1) | ✔ (late) | **WEAK**: greps for its own docs wording |
| C03 TSV | exporter right, **no docs row, no golden file** | 1 | 08 | ✔ (late, after fix 4) | discriminates |

Three of three forgot the docs row and the golden file, so this rule cannot be learned from
the code either.

## Findings, all fixed (Cortex: 386 tests)

| # | What happened | Fix |
|---|---|---|
| 1 | **Preflight quarantined every exporter task.** Its third state strips "the fix's own tests" and counted everything under `tests/` as tests, including the golden file `tests/golden/order.xml` that the house rule requires. Stripped, lint failed, and the task was quarantined as "needs the fix's own test edits". C01 and C02 lost their tasks | only test **code** is stripped: a source file with a test name, or a source file in a test folder. Test **data** (golden files, fixtures, snapshots) stays. Tests: a golden file is kept, and a non-test-named helper in `tests/` is still stripped |
| 2 | Both harvests ran `git stash` in the user's working copy to "see the broken state" | `/harvest`: never stash, checkout or reset the user's working copy; preflight already shows that state |
| 3 | C02 made 4 repairs, cloned the repo to `/tmp` and applied the patch by hand (caused by 1) | `/harvest`: one repair is one edit of `check.sh` plus one preflight run |
| 4 | C02 skipped its lesson as "already captured" by C01. C03 skipped Step 3: Step 1 defined a correction as "two or more times about the same thing", which contradicted Step 3 | Step 1 B is now "any correction, once is enough"; one lesson line per correction, even when a similar line exists (a repeat is the recurrence `/evolve` counts); the report always states the lesson count |
| 5 | Re-running `/harvest` in C01's chat added a second lesson line for the same correction (the first said `no task`) | `/harvest`: on a re-run in the same session, update your own line's `no task` to the new id |
| 6 | A late harvest after other sessions would have swept their commits into `fix.patch` | `cortex task new --head <sha>`: exactly the commits base..head. Tests: later commits and uncommitted work stay out; a head before the base or off HEAD's history is refused |
| 7 | Tasks 09 and 10 grep for their own docs wording (`"XML document"`, `"table with one row"`), so a different correct fix fails them. The linter already checks that the row exists | `/harvest` rule 6: a check passes any correct fix: run the project's own tools, never grep for one fix's names or wording. `cortex score` names tasks that no rollout of either arm passed, and `/evolve` reports them. That is how a real user, with no oracle, finds such a check |
| 8 | lab: `lab done --late` counted other sessions' lessons, and could not record a lesson-only late harvest | lessons are counted from the last recorded session event; lesson-only late harvests are accepted |
| 9 | autopilot: an undefined variable in the BARREN branch would have crashed it | fixed |

Cost of round 3: $8.2 of sweeps (screen $1.92 + confirm $6.28), $3.1 of sessions and
re-harvests, 63 min of sweeps — the last round that runs its rollouts one at a time.

How round 3 was repaired: the autopilot's `/evolve` was stopped before it launched
anything. The Cortex bugs were fixed and installed with `cortex init`. Then each session was
re-harvested the way a user would do it (`bin/autopilot reharvest`): the same chat, `/harvest`
plus a note saying why, then `lab done --late`.

## /evolve

| Cycle | Candidate | Result |
|---|---|---|
| 5 | `complete-exporter-setup` — **path-gated skill** on `shop/plugins/**`, "When implementing a new exporter plugin in shop/plugins/, verify all four files are updated" | screen (08, 09, 10, k=2): **CONFIRM**, gain 1.5, loaded in 5 of 6 rollouts, $1.92 / 14 min. Confirm (9 tasks, k=3): **KEEP** — 08 0→0.33, 09 0→0.33, nothing regressed, net exactly 2 runs (the gate-4 minimum), loaded in 6 of 27, $6.28 / 49 min |

Live after round 3: **1 rule + 2 gated skills**, 0 always-on characters.

Reading: the third weak-but-real KEEP in a row. Two things stand out.

- **A skill gets invoked when its description names the task.** Round 2's changelog
  skill ("verify CHANGELOG.md was updated") was invoked in 1 of 18 rollouts; this one
  ("when implementing a new exporter plugin") in 5 of 6 on the screen. Side duties are
  ignored, the task at hand is not — which is why `/evolve`'s tier guidance now sends
  side duties to rules.
- **The screen overstated the gain** (1.5 at k=2, 0.67 at k=3). That is what the
  confirm is for.

`/evolve` also reported, unprompted: *tasks 04 and 10 never passed in either arm —
read their check.sh files.* Task 10 is the weak check this round produced (it greps
for its own docs wording); task 04 is A02's check, which has the same fault. The
note that found them was written after the round-2 audit; it works.
