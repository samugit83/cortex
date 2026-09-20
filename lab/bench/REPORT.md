# Benchmark — Haiku 4.5 with and without the evolved harness

_2026-09-20T12:07 · 246 valid rollouts · judge: the lab oracle_

## holdout

| Family | none | evolved | gain | tasks |
|---|---|---|---|---|
| A user-visible change (CHANGELOG) | 0% (9) [0%–30%] | 67% (9) [35%–88%] | +67% | 3 |
| B money (billing) | 11% (9) [2%–44%] | 100% (9) [70%–100%] | +89% | 3 |
| C new exporter | 0% (9) [0%–30%] | 44% (9) [19%–73%] | +44% | 3 |
| D control (plain bugs) | 100% (9) [70%–100%] | 100% (9) [70%–100%] | +0% | 3 |
| E time (clock) | 67% (9) [35%–88%] | 67% (9) [35%–88%] | +0% | 3 |

## train

| Family | none | evolved | gain | tasks |
|---|---|---|---|---|
| A user-visible change (CHANGELOG) | 0% (18) [0%–18%] | 56% (18) [34%–75%] | +56% | 6 |
| B money (billing) | 11% (18) [3%–33%] | 72% (18) [49%–88%] | +61% | 6 |
| C new exporter | 11% (18) [3%–33%] | 56% (18) [34%–75%] | +44% | 6 |
| D control (plain bugs) | 100% (12) [76%–100%] | 100% (12) [76%–100%] | +0% | 4 |
| E time (clock) | 0% (12) [0%–24%] | 8% (12) [1%–35%] | +8% | 4 |

## Cost per rollout

| Arm | tokens (mean) | $ (mean) | seconds (mean) |
|---|---|---|---|
| none | 484,650 | 0.092 | 42 |
| evolved | 630,608 | 0.113 | 48 |

## Why rollouts failed

| Arm | verdict | count |
|---|---|---|
| none | B | 23 |
| none | A | 23 |
| none | C | 20 |
| none | E | 13 |
| none | test | 7 |
| none | tampered | 5 |
| evolved | E | 14 |
| evolved | C | 12 |
| evolved | A | 10 |
| evolved | test | 4 |
| evolved | B | 2 |
| evolved | tampered | 1 |

## What loaded (evolved arm)

- `check-changelog-on-shop-edits`: in context in 123 of 123 rollouts, loaded/used in 7
- `complete-exporter-setup`: in context in 27 of 123 rollouts, loaded/used in 20
- `run`: in context in 0 of 123 rollouts, loaded/used in 9
- `use-billing-helpers`: in context in 52 of 123 rollouts, loaded/used in 52
