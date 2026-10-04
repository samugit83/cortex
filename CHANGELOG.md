# Changelog

Every release of Cortex, newest first. Versions follow
[semantic versioning](https://semver.org): the first number changes when a verdict or a
file format changes incompatibly, the second when the tool gains a feature, the third for
fixes, documentation and the lab's analysis. The file `VERSION` holds the current version,
and each release is the git tag `v<version>`.

Two older tags name a role instead of a version: `v1.0-eval` is the Cortex that every
evaluation run used, and `v1.0-paper` is the first public release, 1.0.0.

## [1.0.2] - 2026-10-04

The tool measures and decides exactly as in 1.0.1, and no measured number changed. This
release is the one the paper cites.

### Changed

- The lab's report lists the hypotheses that were tested, numbered H0 to H16 as in the
  paper, and its tables are numbered T1 to T19. `lab/reports/REPORT.md`, `SUMMARY.md`,
  `data/scorecard.json` and the tables are regenerated from the same rows: every estimate,
  interval, margin and verdict is the one 1.0.1 printed.
- The scripts that compute the paper's numbers (`lab/reports/analysis/gen_numbers.py`,
  `gen_results_data.py`) read the new labels.
- `lab/reports/REPRODUCE.md` and `docs/GUIDE.md` follow the report.

### Removed

- The programme's working documents (its brief, its plan, its logs and checkpoints) and
  the list of defects found while the lab was built, with the table drawn from it. The
  report, the rows behind it and the scripts that rebuild every number stay.

## [1.0.1] - 2026-10-04

The tool measures and decides exactly as in 1.0.0. This release is the one whose scripts
and data regenerate every number, table and chart of the paper.

### Added

- `VERSION` and this changelog.
- `docs/GUIDE.md`, the complete manual, moved out of the README and checked against the
  code; the logo in `docs/images/`.
- `lab/reports/data/external-training.json`, the second repository's training (its
  sessions with their verdicts and corrections, the tasks and lessons they left, the
  `/evolve` cycles), and `lab/reports/analysis/extract_external.py`, which exports it from
  the run's own records.

### Changed

- `README.md` is a short landing page: what Cortex is, the result, install, quick start,
  and where to read more. The comments in `bin/cortex` and `bin/compile-config.py` that
  pointed to the README's sections now point to the guide.
- The scripts that compute the paper's numbers (`lab/reports/analysis/gen_numbers.py`,
  `gen_tables.py`, `gen_diagram_data.py`):
  - every count the paper states is now a macro read from the rows or from the code at
    `v1.0-eval`;
  - the second repository's counts come from `external-training.json`, not from prose;
  - the tally of how often a path-gated candidate was listed and opened covers the gate
    test as well as the loop's sweeps, as the always-on tally already did;
  - the size of the implementation counts `hooks/` as well as `bin/`;
  - a bound of zero prints as `0.0`, without a sign;
  - the release the paper cites is read from `VERSION`;
  - rows that no section of the paper includes are still checked against the text that
    quotes them, but no longer written as tables.

### Fixed

- `lab/reports/tables/T15-model-change`: the pooled row A+B+C+E included the control
  family D, and read 91% and 96%. It now covers the four rule families, 89% and 94%, as
  the rows give. No hypothesis and no other table used that row.
- `gen_numbers.py` at 1.0.0 did not define every macro the paper uses, so the paper's
  numbers could not all be regenerated from that release. They can from this one:
  `lab/reports/REPRODUCE.md` gives the four commands.

## [1.0.0] - 2026-10-03

The first public release (tag `v1.0-paper`).

- **The tool**: the `cortex` command line, the three Claude Code commands `/harvest`,
  `/evolve` and `/prune`, the optional session-end hook and the optional judge, Jev. It is
  the Cortex frozen for the evaluation as `v1.0-eval` (2026-09-20), with one addition:
  `cortex scope --json` also reports the judge's predicted invocation (`would_fire`).
- **The evaluation lab**: the synthetic repository, its scenarios in five task families,
  the scripted developer, and the benchmark.
- **The report and its data**: `lab/reports/REPORT.md`, its tables and figures, and the
  rollout-level rows behind every number, with the scripts that rebuild them offline
  (`lab/reports/REPRODUCE.md`).

[1.0.2]: https://github.com/samugit83/cortex/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/samugit83/cortex/compare/v1.0-paper...v1.0.1
[1.0.0]: https://github.com/samugit83/cortex/releases/tag/v1.0-paper
