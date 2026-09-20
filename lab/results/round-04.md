# Round 4 — time (E01, E02, E03), the first parallel round

## Sessions

| Session | First attempt | Corrections | Task | Lesson | Audit of the harvested check |
|---|---|---|---|---|---|
| E01 invoice due date | feature right, **`date.today()`** | 1 | 11 | ✔ | discriminates (after repair, see fix 1) |
| E02 cart reservation | feature right, **`datetime.now()`** | 1 | 12 | ✔ | discriminates |
| E03 archive orders | feature right, **`datetime.today()`** | 1 | 13 | ✔ | discriminates (after repair) |

Three of three reached for the wall clock; `make lint` caught all three. Every session
harvested a task **and** a lesson this time: the `/harvest` fixes from round 3 hold.
Sessions: 9 min, $1.4.

## /evolve: three cycles, no keep — and the reasons matter

| Cycle | Candidate | Result |
|---|---|---|
| 6 | `enforce-shop-clock` — **rule** on `shop/**` | screen: killed on gain 0… but **the sweep could not have shown a gain**: tasks 11 and 13 were unpassable (their checks demanded a CHANGELOG entry nobody asked for) and 12 already passed. Cortex now calls that RERUN, not KILL (fix 3 below) |
| 10 | — | barren: after the repairs, only **one** clock task still fails, under the 2-task bar |
| 11 | — | barren, streak limit: *"all failing tasks are already covered by live items — this is a `/prune` situation: the changelog **skill** should be measured for replacement with a **rule**"* |

**The interesting result is the last line.** `/evolve` reached, from the data, the
same conclusion the tier evidence gave in round 3: a *side duty* belongs in a rule,
not in a skill nobody invokes. It also refused to invent a new item for a theme a
live item already covers — and said so as a `/prune` job.

**Why the clock rule never earned its keep:** once the checks tested only what the
user asked for, two of the three clock tasks passed **without** any rule. The repo
already uses `shop.clock` everywhere, so the agent copies it — the same "the code
teaches" effect that made B02 need no correction in round 1. A house rule that the
code already demonstrates does not need a skill.

## Findings, all fixed (Cortex: 482 tests)

| # | What happened | Fix |
|---|---|---|
| 1 | Both E01 and E03 put a **CHANGELOG entry nobody asked for** into their checks (they had added one on their own). No rollout could pass those tasks, so the clock rule measured 0 and was killed | `/harvest` rule 7: a check tests the request and the corrections, **nothing else the fix happened to do**. The three checks were repaired in their own chats, after `/evolve` reported the tasks as never passing |
| 2 | A KILL on tasks nobody can pass reads as "this idea does not help", and buries it | `cortex score`: when no gated task can show a gain (all never passed, or all already pass in base), the verdict is **RERUN** — "the candidate was not measured" — never KILL |
| 3 | `never_passed` counted tasks the candidate never reached. `/evolve` read it as "these tasks are broken" and dropped a theme that was fine | it counts only tasks the change actually reached; for the others, "nobody passed" merely says the live harness fails them — which is what makes them targets |
| 4 | `/evolve` proposed a **rule that duplicated a live skill** (same area, same content) as an *addition*: both would load | `cortex skills --candidate` warns when a candidate covers exactly a live item's files and names the replacement it should be; `/evolve` now says a theme a live item covers belongs to `/prune` Step 5 |
| 5 | Three older checks had the same fault (05 lost the correction it was harvested for; 09 and 10 pinned their own docs wording) | repaired in their own sessions. 11 of 12 tasks now discriminate; the twelfth (02) is from the one session that was never corrected, so it has no house rule to check |

**Experimenter's own mistake, for the record:** I stopped a running sweep without
stopping the loop that owned it. The autopilot did the right thing — a sweep that
died gets relaunched — and re-ran an 8-minute confirm I had meant to abandon (~$8).
Stop the loop first.

## Parallelism, measured

| Sweep | Rollouts | At once | Elapsed |
|---|---|---|---|
| screen (clock) | 12 | 8 | **1.4 min** (one at a time: ~14 min) |
| confirm (exporter rule) | 72 | 8 | **8 min** (one at a time: ~50 min) |

Same rollouts, same scores, and the load guard stayed quiet: a normal Haiku sweep of
8 sits at ~1.5 runnable tasks per CPU, well under the bar that marks a sweep as
oversubscribed.
