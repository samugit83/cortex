# Status: the programme is complete

Finished **2026-09-27 02:32**; the final report was generated on **2026-09-29**. Nothing
is running. Every step of `lab/bin/programme` has its marker; the analysis, the report and
the artifact package are committed.

| | |
|---|---|
| Spent | **$1,195.75** of the $1,500 cap, measured (`lab/bin/usage-guard spend`; one prune sweep whose record the `/prune` agent deleted, $20.79, from Claude Code's session records) |
| Rollouts | **6,462** |
| D0 | verified **UNCHANGED** (`lab/bin/verify-d0`) |
| Report | [`REPORT.md`](REPORT.md) · one page: [`SUMMARY.md`](SUMMARY.md) · [`CHECKPOINT-B.md`](CHECKPOINT-B.md) |
| Rebuild | `lab/reports/analysis/run.sh` — offline, ~1 min, proven in a clean clone |

## Definition of done (brief §8)

- [x] H0–H18 each have a verdict, a number with an interval where one applies, the pre-registered margin, and a pointer
- [x] Every figure (F1–F19) and table (T1–T20) exists and regenerates with one command
- [x] The claims table (T18) and the defect catalogue (T16, 61 entries) are written for an outside reader
- [x] `PREREGISTRATION.md` committed (2026-09-20) before the first replicate rollout; `DEVIATIONS.md` D-01 to D-21
- [x] Every evaluation, control, gate, prune, model-change and second-repository process ran on `v1.0-eval`; `manifest.json` and every run row record it
- [x] Every run records whether Jev was on; every primary run is Jev-off (T20)
- [x] H16 and H17 reported for D0 and R1–R4 (H16's verdict on R1–R4, D0 beside it), with breadth as the control and the false-alarm count beside the saving
- [x] `jev/RESULTS.md` present and cited, with J0's failed 90 % bar stated (D-07)
- [x] D0 reported by the same scripts, marked as the development run; re-measured like for like (D0R)
- [x] The A/A arm is reported: −3.3 [−7.3, +0.0]
- [x] The second repository is reported in its own section, never pooled
- [x] D0's data untouched and reproducible
- [x] Spend within `BUDGET_CAP_USD`
- [x] Offline figure regeneration works on a clean machine
- [ ] **A public repository and a Zenodo DOI** — yours to do: they publish, and cannot be undone
- [ ] Local tag `v1.0-paper` on the commit the numbers come from: move it to the commit of the final report (not pushed)

## What is left, and it is yours

1. **Publish** — push the repository (and the tags `v1.0-eval`, `v1.0-paper`) to a
   public host. Consider publishing a fresh copy rather than this history: older
   commits of `reports/data/` contain the local paths the final version scrubs.
2. **Zenodo** — archive the `v1.0-paper` release for a DOI, and put it in `CITATION.cff`.
