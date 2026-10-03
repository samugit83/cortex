# T12 · What the lab's checks flagged, by run

Counted from sessions.jsonl. The autopilot never repairs anything by hand: when a step does not do what the protocol says, it records the finding and goes on, or stops. A harvest that produced no task can be right: a check that needs the fix's own test is deleted by design.

| run | finding | count |
|---|---|---|
| D0 | a correction with no lesson written | 1 |
| R1 | a harvest recorded the previous session's commit as the task's base (WRONG START) | 1 |
| R1 | a correction with no lesson written | 1 |
| R1 | a session that harvested no task | 1 |
| R2 | a harvest recorded the previous session's commit as the task's base (WRONG START) | 1 |
| R3 | a correction with no lesson written | 1 |
| R4 | a session that harvested no task | 1 |
| R4 | a session turn stopped at the turn cap | 1 |
| C1 | a harvest recorded the previous session's commit as the task's base (WRONG START) | 1 |
| C1 | a correction with no lesson written | 1 |
