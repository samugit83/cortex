# T6 · Kept and buried items, across runs

`in context` and `invoked` are over that run's benchmark rollouts in the `evolved` arm. A rule is never 'invoked' by choice: it is loaded when the agent reads a matching file, which is why its two columns are equal.

| run | name | kind | family | paths | chars | fate | by score.sh | in context | invoked | fired on its own family | fired elsewhere | why buried (journal) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | check-changelog-on-shop-edits | skill | A | shop/** | 569 | kept | — | 123/123 | 7/123 | 2/27 | 5/96 | — |
| D0 | complete-exporter-setup | skill | C | shop/plugins/** | 772 | kept | — | 27/123 | 20/123 | 20/27 | 0/0 | — |
| D0 | use-billing-helpers | rule | B | shop/billing/** | 321 | kept | — | 52/123 | 52/123 | 27/27 | 25/25 | — |
| D0 | changelog-rule-v2 | rule | A | shop/** | 481 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-20T10:24:42+02:00  from: candidate kind: rule why:  screen: gate2 worst_drop 0.5 exceeds regression_tolerance 0.34 on task  |
| D0 | changelog-updates | skill | A | (none) | 707 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-20T11:50:49+02:00  from: candidate kind: skill why:  screen gate5: never invoked, description did not trigger. Should have  |
| D0 | check-changelog-on-shop-edits | skill | A | shop/** | 593 | buried | — | 123/123 | 7/123 | 2/27 | 5/96 | # Buried 2026-09-19T15:21:02+02:00  from: candidate kind: skill why:  screen: never loaded (gate5); no gain (gate1) |
| D0 | clock-in-billing | rule | E | shop/billing/** | 277 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-20T11:11:30+02:00  from: candidate kind: rule why:  gate2 worst drop 0.67 exceeds tolerance 0.34; gate3 broke protected set |
| D0 | enforce-shop-clock | rule | E | shop/** | 380 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-20T09:12:11+02:00  from: candidate kind: rule why:  screen: gain 0, tasks 11/13 never passed |
| D0 | enforce-shop-clock-v2 | rule | E | shop/** | 304 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-20T10:07:58+02:00  from: candidate kind: rule why:  gate2 worst drop 1.0 exceeds tolerance 0.34, gate3 broke protected set  |
| D0 | shop-clock-usage | rule | E | shop/** | 494 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-20T11:41:19+02:00  from: candidate kind: rule why:  gate2: worst_drop 0.67 exceeds tolerance 0.34; gate3: broke protected;  |
| R1 | exporter-checklist | skill | C | shop/plugins/** | 1135 | kept | kept | 48/228 | 48/228 | 48/48 | 0/0 | — |
| R1 | billing-helpers | rule | B | shop/billing/** | 317 | kept | kept | 83/228 | 83/228 | 46/46 | 37/37 | — |
| R1 | changelog-requirement | rule | A | shop/** | 518 | kept | kept | 222/228 | 222/228 | 47/47 | 175/175 | — |
| R1 | shop-clock-rule | rule | E | shop/** | 327 | kept | kept | 222/228 | 222/228 | 41/41 | 181/181 | — |
| R2 | billing-exact-arithmetic | rule | B | shop/billing/** | 564 | kept | kept | 80/228 | 80/228 | 47/47 | 33/33 | — |
| R2 | changelog-user-visible | rule | A | shop/** | 529 | kept | kept | 221/228 | 221/228 | 47/47 | 174/174 | — |
| R2 | exporter-docs-and-golden | rule | C | shop/plugins/** | 427 | kept | kept | 48/228 | 48/228 | 48/48 | 0/0 | — |
| R2 | shop-clock-not-datetime | rule | E | shop/** | 353 | kept | kept | 221/228 | 221/228 | 39/39 | 182/182 | — |
| R2 | shop-clock-explicit-imports | rule | E | shop/** | 1473 | buried | unscored | 0/0 | 0/0 | — | — | # Buried 2026-09-21T20:45:12+02:00  from: candidate kind: rule why:  overlaps with live rule shop-clock-not-datetime; refinements use /prune |
| R3 | billing-rate-helpers | rule | B | shop/billing/shipping.py, shop/billing/refunds.py | 510 | kept | kept | 6/228 | 6/228 | 6/6 | 0/0 | — |
| R3 | changelog-shop-reminder | rule | A | shop/** | 261 | kept | kept | 226/228 | 226/228 | 48/48 | 178/178 | — |
| R3 | changelog-user-facing | rule | A | shop/cli.py, shop/formatting.py, shop/report.py | 334 | kept | kept | 63/228 | 63/228 | 48/48 | 15/15 | — |
| R3 | exporter-checklist-v2 | rule | C | shop/plugins/*_export.py | 621 | kept | kept | 48/228 | 48/228 | 48/48 | 0/0 | — |
| R3 | rate-helpers-narrow | rule | B | shop/billing/tax.py, shop/billing/discount.py, shop/billing/fx.py | 380 | kept | kept | 9/228 | 9/228 | 9/9 | 0/0 | — |
| R3 | shop-clock-narrow | rule | E | shop/billing/invoice.py, shop/cart.py, shop/orders.py | 335 | kept | kept | 71/228 | 71/228 | 18/18 | 53/53 | — |
| R3 | exporter-checklist | skill | C | shop/plugins/** | 829 | buried | killed | 0/0 | 0/0 | — | — | # Buried 2026-09-21T21:36:33+02:00  from: candidate kind: skill why:  gate4: net 1 run is noise (threshold 2) |
| R3 | shop-clock-access | rule | E | shop/** | 282 | buried | killed-regression | 0/0 | 0/0 | — | — | # Buried 2026-09-21T22:13:21+02:00  from: candidate kind: rule why:  gate2/3: task 13 regressed 100%->67% and confirmed on recheck |
| R3 | text-utilities-correctness | rule | — | shop/util/text.py | 640 | buried | killed-regression | 0/0 | 0/0 | — | — | # Buried 2026-09-21T23:25:54+02:00  from: candidate kind: rule why:  gate2/3: worst_drop 0.67 broke tasks 13,15 in protected set |
| R3 | use-rate-helpers | rule | B | shop/billing/** | 320 | buried | unscored | 0/0 | 0/0 | — | — | # Buried 2026-09-21T20:55:34+02:00  from: candidate kind: rule why:  confirm: gain +3 but regression +3, worst_drop 1.0 — rule too broad, br |
| R4 | exporter-checklist | skill | C | shop/plugins/** | 940 | kept | kept | 48/223 | 40/223 | 40/48 | 0/0 | — |
| R4 | billing-rates-helpers | rule | B | shop/billing/** | 823 | kept | kept | 80/223 | 80/223 | 48/48 | 32/32 | — |
| R4 | shop-changelog-reminder | rule | A | shop/** | 616 | kept | kept | 219/223 | 219/223 | 42/42 | 177/177 | — |
| R4 | shop-clock-queries | rule | E | shop/** | 574 | kept | kept | 219/223 | 219/223 | 39/39 | 180/180 | — |
| R4 | changelog-contributing-reminder | rule | A | CONTRIBUTING.md | 649 | buried | killed | 0/0 | 0/0 | — | — | # Buried 2026-09-22T00:47:00+02:00  from: candidate kind: rule why:  screen: never loaded — no rollout read a matching file |
| R4 | changelog-for-user-visible-changes | rule | A | CHANGELOG.md | 799 | buried | killed | 0/0 | 0/0 | — | — | # Buried 2026-09-22T00:16:31+02:00  from: candidate kind: rule why:  screen: gain 0 + never loaded |
| R4 | changelog-in-contributing | rule | A | (none) | 0 | buried | — | 0/0 | 0/0 | — | — | # Buried 2026-09-22T00:44:01+02:00  from: candidate kind: malformed why:  empty candidate — malformed |
| R4 | changelog-moment-check | skill | A | (none) | 1455 | buried | unscored | 0/0 | 0/0 | — | — | # Buried 2026-09-22T00:43:20+02:00  from: candidate kind: skill why:  screen: never invoked; agent doesn't treat always-on reminder as actio |
