# T18 · Every claim, and what supports it

A sentence with no evidence is deleted, not softened. This table is the check that it was.

| # | the sentence the report asserts | figure or table | the number |
|---|---|---|---|
| 1 | H0: Without a harness the agent breaks A/B/C/E often and passes D — SUPPORTED | F1, T4 · the stricter reading, all four below 50%, is not met · the margin is the rule the analysis code applies (DEVIATIONS D-22) | A0% B26% C2% D100% E55% — |
| 2 | H1: PRIMARY. On holdout tasks `evolved` beats `none`, A+B+C+E pooled — SUPPORTED | T4, F2, F3 · permutation p = 9.999e-05 · 92 complete-case scenario-run pairs (23 scenarios) · all-valid set: +56.5 [+35.4, +75.0] | +55.0 points [+34.1, +74.1] |
| 3 | H2: PRIMARY. Family D is not harmed, and no spurious item is kept — SUPPORTED | T4, T6, F2 | -0.8 points; 0 spurious item(s) [-5.0, +0.0] |
| 4 | H3: Each kept item lands in a defensible tier and fires in its own area — NOT SUPPORTED | T6, F9 | 15 of 18 items scored 3/3 — |
| 5 | H4: Corrections fall once an item is live, beyond the control runs — SUPPORTED | T9, F5 | -0.31 corrections per session see T9 |
| 6 | H5: Gates are calibrated: placebos rarely kept, harmful killed, positives kept — NOT SUPPORTED | T8, F10 · a harmful candidate counts as killed when score.sh killed it (DEVIATIONS D-22) | false KEEP 0/20; harmful kept 0/5 (score.sh: 2 KILL, 3 RERUN); positives kept 2/4 false KEEP [0%, 17%] |
| 7 | H6: Gates add value: `accept-all` is not better than `evolved` — SUPPORTED | T7, F8 | -8.9 points [-16.1, -1.7] |
| 8 | H7: Tiers add value: `flat` costs more always-on context without gaining pass rate — SUPPORTED | T7, F8 | -12.5 points; always-on 559 → 1688 chars [-28.3, +1.7] |
| 9 | H8: Efficiency: `evolved` approaches `kitchen` and `ideal` at far lower cost — SUPPORTED | T7, F8 | evolved is 11.1 points AHEAD OF `kitchen` · always-on 559 vs kitchen 2519, ideal 728 [-22.5, +0.0] (kitchen − evolved) |
| 10 | H9: Independent runs learn the same families, in similar forms — SUPPORTED | F7, T6 | 4 of 4 families learned in every run — |
| 11 | H13: D0 replicates: the development run's finding holds on the frozen version — SUPPORTED | T4, F3 | D0 +42.5 (on its own 15-task holdout: +50.0), replicates +56.5 [+35.4, +75.0] |
| 12 | H10: /prune deletes planted useless items that fired, keeps needed ones, and never deletes one that never fired — NOT SUPPORTED | T10 | 6 of 8 matched — |
| 13 | H14: After a model upgrade, re-measurement changes which items earn their place — SUPPORTED | T15, F16 | 2 of 4 decided item(s) removable (exporter-checklist, billing-helpers); the same harness gains +66.7 under Haiku (R1) and +5.6 under claude-sonnet-5 [-2.8, +13.9] |
| 14 | H16: Pre-sweep relevance separates KEPT from BURIED-on-regression where breadth does not — NOT SUPPORTED | T19, F18 · the development run is in T19, not pooled | relevance: lowest KEPT 17% vs highest BURIED 75% · breadth: 8% vs 58% · 18 kept, 2 buried on a regression see T19 |
| 15 | H17: The judge's predicted fire rate tracks the measured one — SUPPORTED | F19, T19 · largest miss: check-changelog-on-shop-edits, 54 points | check-changelog-on-shop-edits predicted 60% vs measured 6%; complete-exporter-setup predicted 100% vs measured 74%; exporter-checklist predicted 100% vs measured 100%; exporter-checklist predicted 100% vs measured 83% n = 4 items |
| 16 | Without a harness, the agent solves these tasks without opening the file that documents the house rules. | rollouts.jsonl · read_contributing, `none` arm | 3/595 holdout rollouts = 0.5% |
| 17 | `billing-helpers` (R1) was in context in 83 rollouts and invoked in 83. | F9, T6 | 83/83 = 100% |
| 18 | `changelog-requirement` (R1) was in context in 222 rollouts and invoked in 222. | F9, T6 | 222/222 = 100% |
| 19 | `exporter-checklist` (R1) was in context in 48 rollouts and invoked in 48. | F9, T6 | 48/48 = 100% |
| 20 | `shop-clock-rule` (R1) was in context in 222 rollouts and invoked in 222. | F9, T6 | 222/222 = 100% |
| 21 | `billing-exact-arithmetic` (R2) was in context in 80 rollouts and invoked in 80. | F9, T6 | 80/80 = 100% |
| 22 | `changelog-user-visible` (R2) was in context in 221 rollouts and invoked in 221. | F9, T6 | 221/221 = 100% |
| 23 | `exporter-docs-and-golden` (R2) was in context in 48 rollouts and invoked in 48. | F9, T6 | 48/48 = 100% |
| 24 | `shop-clock-not-datetime` (R2) was in context in 221 rollouts and invoked in 221. | F9, T6 | 221/221 = 100% |
| 25 | `billing-rate-helpers` (R3) was in context in 6 rollouts and invoked in 6. | F9, T6 | 6/6 = 100% |
| 26 | `changelog-shop-reminder` (R3) was in context in 226 rollouts and invoked in 226. | F9, T6 | 226/226 = 100% |
| 27 | `changelog-user-facing` (R3) was in context in 63 rollouts and invoked in 63. | F9, T6 | 63/63 = 100% |
| 28 | `exporter-checklist-v2` (R3) was in context in 48 rollouts and invoked in 48. | F9, T6 | 48/48 = 100% |
| 29 | `rate-helpers-narrow` (R3) was in context in 9 rollouts and invoked in 9. | F9, T6 | 9/9 = 100% |
| 30 | `shop-clock-narrow` (R3) was in context in 71 rollouts and invoked in 71. | F9, T6 | 71/71 = 100% |
| 31 | `billing-rates-helpers` (R4) was in context in 80 rollouts and invoked in 80. | F9, T6 | 80/80 = 100% |
| 32 | `exporter-checklist` (R4) was in context in 48 rollouts and invoked in 40. | F9, T6 | 40/48 = 83% |
| 33 | `shop-changelog-reminder` (R4) was in context in 219 rollouts and invoked in 219. | F9, T6 | 219/219 = 100% |
| 34 | `shop-clock-queries` (R4) was in context in 219 rollouts and invoked in 219. | F9, T6 | 219/219 = 100% |
| 35 | The lab found defects in Cortex itself, and they are a result rather than an embarrassment. | T16 | 61 total: 39 while the lab was built and during the development run, 22 during this programme |
| 36 | What the programme cost, measured. | T14, spend.json | $1,195.75 of a $1,500 cap (the development run, before it: $155.45) |
| 37 | Invalid rollouts are excluded, counted and listed by reason. | T13 | 9 of 6,462 = 0.14% |
| 38 | The holdout set carries a measurement here. | T2 | 30 tasks |
| 39 | The train set carries a measurement here. | T2 | 26 tasks |
