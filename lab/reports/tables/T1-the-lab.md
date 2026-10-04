# T1 · The lab: families, rules and task counts

The expected form is the design's prediction, written before any run. Whether it is right is H3, not an assumption.

| family | what it is | the house rule | the usual mistake | what checks it | the form the design predicts | train | holdout |
|---|---|---|---|---|---|---|---|
| A | user-visible change (CHANGELOG) | every user-visible change gets a CHANGELOG line under [Unreleased] | fixes the code, forgets the CHANGELOG | a new `+- ` line in CHANGELOG.md since the base commit | a moment -> always-on skill | 6 | 6 |
| B | money (billing) | amounts are integer cents; scale them with the rates helpers | int(rate.split('.')[0]) or float arithmetic | tools/lint.py, money | an area it reads -> rule on shop/billing/** | 6 | 6 |
| C | new exporter | a new exporter needs module, registry entry, docs row and golden file | writes the exporter module and stops | tools/lint.py, exporters | an area it creates in -> gated skill on shop/plugins/** | 6 | 6 |
| D | control (plain bugs) | — (control: no house rule) | — | the task's own test and the suite | nothing should be learned | 4 | 6 |
| E | time (clock) | read the time through shop.clock, never datetime.now() | calls date.today() directly | tools/lint.py, time | repo-wide -> always-on skill | 4 | 6 |
