# T10 · The prune experiment: planted items and their verdicts

6 of 8 matched the expected verdict, written for each item before the testbed was built. `fired in its sweep` is measured: the base rollouts of the item's own removal sweep in which it fired (data/prune-sweeps.jsonl).

| run | item | planted role | expected | verdict | matches | fired in its sweep | chosen by | rollouts | what the planted role expected |
|---|---|---|---|---|---|---|---|---|---|
| PRUNE | before-reporting-a-change-complete | placebo always-on skill, moment description | ACCEPT | ACCEPT | yes | 1/15 | not chosen | 30 | ACCEPT (deleted): it fires and costs nothing |
| PRUNE | after-finishing-an-edit | placebo always-on skill, moment description | ACCEPT | REJECT | NO | 0/18 | not chosen | 36 | ACCEPT (deleted): it fires and costs nothing |
| PRUNE | vendor-bundle-conventions | gated skill whose paths match no file any task touches | SKIPPED | SKIPPED | yes | not swept | not chosen | — | SKIPPED by the plan; never deleted |
| PRUNE | rotate-a-signing-key | always-on skill whose description names no moment here | UNMEASURED | SKIPPED | NO | not swept | not chosen | — | UNMEASURED (never fires); not deleted |
| PRUNE | exporter-checklist | R1's own evolved item | REJECT | REJECT | yes | 15/75 | plan | 150 | an item the run earned: deleting it should cost pass rate |
| PRUNE | billing-helpers | R1's own evolved item | REJECT | REJECT | yes | 31/75 | plan | 150 | an item the run earned: deleting it should cost pass rate |
| PRUNE | changelog-requirement | R1's own evolved item | REJECT | REJECT | yes | 74/75 | plan | 150 | an item the run earned: deleting it should cost pass rate |
| PRUNE | shop-clock-rule | R1's own evolved item | REJECT | REJECT | yes | 74/75 | plan | 150 | an item the run earned: deleting it should cost pass rate |
