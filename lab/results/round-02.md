# Round 2 — changelog (A01, A02, A03), run by the autopilot

## Sessions

| Session | First attempt | Corrections | Task | Lesson | Audit of the harvested check |
|---|---|---|---|---|---|
| A01 list sort | feature right, **no CHANGELOG** | 1 | 04 | ✔ | discriminates |
| A02 thousands separator | feature right, **no CHANGELOG** | 1 | 05 | ✔ | **WEAK**: the check forgot the CHANGELOG condition |
| A03 report total | feature right, **no CHANGELOG** | 1 | 06 | ✔ | discriminates |

Each session took about 70 s and $0.28–0.38 headless. Three of three forgot the changelog,
so the rule cannot be learned from the code.

## /evolve

| Cycle | Candidate | Result |
|---|---|---|
| 2 | `check-changelog-on-shop-edits` v1 — **gated skill** on `shop/**`, "When editing shop code, verify CHANGELOG.md is updated" | screen: **KILL** — visible in 6/6 rollouts, **invoked 0/6** (gate 5: "description did not trigger") |
| 3 | v2, same name — "**Before finishing** changes to shop/ code, verify CHANGELOG.md was updated" | screen CONFIRM (04: 0→0.5, 06: 0→0.5, invoked 1/6); confirm **KEEP**: 04: 0→0.33, 06: 0→0.33, everything else held, net **exactly 2 runs** (the gate-4 minimum), invoked 1/18 |
| 4 | — | BARREN: nothing else recurs |

Reading: the classic skill failure. A skill must be *chosen*. Rewriting the description as a
moment ("before finishing…") got it chosen now and then, and the gain is real but weak. The
benchmark will show whether it holds on unseen tasks.

## Findings, all fixed (Cortex: 377 tests)

| # | What happened | Fix |
|---|---|---|
| 1 | `/evolve` read the previous cycle's finished confirm as its own, replayed its ending and recorded the same KEEP twice | **`cortex phase`**: the phase is computed from the files (A, B, C, D, relaunch, prune); `cortex cycle KEEP <name>` refuses a duplicate |
| 2 | after a KILL, `/evolve` skipped the journal entry | `cortex cycle KEEP\|KILL <name>` refuses until the journal has that cycle's entry; `cortex cycle BARREN` writes its own line |
| 3 | the retry reused the killed candidate's **name**, then `/evolve` edited the old journal entry instead of adding one, got refused, and ran `git checkout` on the records | the sweep refuses a buried name (a revised idea is `<name>-v2`); the refusal says "add a NEW heading, never edit an older entry"; records restored by hand, marked as such |
| 4 | **the test suite and the lab's live sweep shared `/tmp/cortex-evolve`**, and wiped each other's clone and task snapshot three times (the scorer caught it: RERUN) | each repository sweeps in `<sandbox_root>/<hash of its path>`; the test suite uses its own temp folder; a vanished task snapshot is recorded as `snapshot_lost`, never skipped silently |
| 5 | while reading "this project's transcripts", `/evolve` read a file from **another project** (redamon's memory) | `cortex harness transcripts` lists exactly this project's recent sessions; `/evolve` reads only those |
| 6 | task 05's check forgot the corrected CHANGELOG condition | `/harvest`: list the user's corrections **before** writing `check.sh`; each becomes a line that fails when the mistake is repeated |
| 7 | the autopilot took a cycle-counter bump as "cycle ended" | a cycle has ended when the journal has its entry and no candidate is left |

Cost of round 2's sweeps: ~$5.6 (screens $1.05 + $1.10, three destroyed confirms ~$1.5, the
valid confirm $3.06).
