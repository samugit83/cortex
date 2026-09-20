# Run log

Chronological. One entry per run, per round and per protocol FINDING, with what it
cost. Appended as things happen, never rewritten.

| | |
|---|---|
| Pre-registration | `PREREGISTRATION.md`, commit recorded at the freeze |
| Frozen Cortex | `v1.0-eval` |
| D0 | read-only throughout; `lab/bin/verify-d0` proves it |

---

## Phase 1 — preparation (no evaluation rollouts)

2026-09-20

- D0 backed up to `cortex-eval/backup-D0` (1,393 files) and verified UNCHANGED.
- `lab/bin/guard.py` + `lab/D0-PROTECTED.txt`: the tools refuse to write to D0.
- `observe` records `turns`, `tool_calls`, `read_contributing`; sweep row schema 2 → 3.
- `bench.py`: nine named arms, per-arm always-on accounting, generalised report.
- `autopilot`: `--no-evolve`, a 40-turn cap and a 15-minute per-call timeout.
- 15 new holdout scenarios written; **56 scenarios, all valid**.
- `lab/bin/export-run` reproduces every headline number in D0's `results/FINAL.md`.
- 29 gate candidates and 4 prune plants generated and committed.
- `test/run-tests.sh`: **653 passed, 0 failed**.

FINDINGs raised in Phase 1: see `DEVIATIONS.md` D-01 (no Jev key), D-02 (`HA3`/`HE3`
re-anchored), D-04 (D0's `REPORT.md` overwritten once and restored).
