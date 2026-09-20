# Round 1 — money (B01, B02, B03)

Sessions run by the user in VS Code (Haiku 4.5); the /evolve cycle finished by the
autopilot. Raw numbers: `round-01-check.md`.

## Outcome

| Session | First attempt | Corrections | Task | Lesson |
|---|---|---|---|---|
| B01 tax | `Decimal` → lint ✘ | 1 | 01 | ✔ |
| B02 discount | **right first time**: copied `percent_of()` from B01's fix in `tax.py` | 0 | 02 (check without lint) | — |
| B03 FX | `float()` → lint ✘ | 1 | 03 (late harvest) | ✔ |

`/evolve` → theme "billing arithmetic" (2 lessons, 3 tasks) → **rule** `use-billing-helpers`
on `shop/billing/**`:

| Sweep | Verdict | 01 tax | 02 discount | 03 FX | Cost |
|---|---|---|---|---|---|
| screen, k=2 | CONFIRM | 0 → 1 | 1 → 1 | 0 → 1 | $0.85, 7 min |
| confirm, k=3 | **KEEP** | 0 → **1** | 1 → 1 | 0.33 → **1** | $1.34, 11 min |

The rule was in context in every cand rollout and never in base. Without it Haiku wrote
`Decimal`/`float` in 5 of 6 screen rollouts; with it, the house helpers every time. No
rollout could read `.evolve/`.

## Findings, all fixed before round 2 (Cortex: 357 tests, all green)

| # | What happened | Fix |
|---|---|---|
| 1 | Claude committed its own fixes, sometimes twice (first attempt + corrected) | `/harvest`: base_sha is below **all** of the session's commits; `lab done` flags a wrong start |
| 2 | `/harvest` wrote `fix.patch` with `git diff` and a hand-picked file list | `cortex task new --base <sha>` writes `fix.patch` (new files included) and `task.yaml`; refuses a base outside HEAD's history |
| 3 | B02 learned the rule from B01's fix in the code: no correction, no lesson | a real effect ("the code teaches"); rounds regrouped by family |
| 4 | the user forgot `/harvest` in B03; `lab done` only warned | `lab done` refuses without a task; `lab done --late` attaches a later harvest |
| 5 | the late `/harvest` wrote `cd "$(dirname "$0")/../.."` in `check.sh`; preflight quarantined it with no reason; Haiku debugged in the working copy, then `rm -rf .evolve/tasks/_broken` and skipped the lesson | check rule 0 (never `cd`); preflight runs checks from a copy like a sweep and prints why; one repair, then delete only that task; the lesson is written whenever the user corrected |
| 6 | `/evolve` promoted straight from the **screen**: `cortex score` said KEEP for a screen | a screen's verdict is CONFIRM / KILL / RERUN; `cortex promote` refuses without a confirm KEEP; `cortex baseline` refuses a screen |
| 7 | `cortex status` said "0 skills live" with a live rule | counts rules |
| 8 | a sweep launched with `nohup … &` dies when the agent's session ends (headless, or a closed chat) | `cortex sweep --detach` (own process session); `/evolve` and `/prune` use it |
| 9 | a dead sweep would be polled forever | `cortex score` reports `running`; a dead sweep says so and `/evolve` relaunches it |
| 10 | `lab commit` mangled the first path of `git status` | fixed |
