# J0 — Jev against Cortex's own corpus

```
validated-model: typesafe-ai/jev
verdict:         PASS
measured:        2026-09-21T15:26:04+00:00
snapshot:        jev/corpus
rows:            174 (candidate, task) rows; 104 distinct pairs; 104 answered
rollout model:   claude-haiku-4-5-20251001  (the model those rollouts RAN on; firing rates may differ on another)
input tokens:    60165
```

Every line above can invalidate this result, so none of them is implicit. `bin/jev.py` compares each answer's model id against `validated-model` and warns once per run when they differ (§3.7).

## 1. Agreement with the keyword oracle (plan §1.3)

**89.4%** over 104 answered pairs (pass needs ≥ 85%).

| candidate | task | p | Jev | oracle |
|---|---|---|---|---|
| `changelog-rule-v2` | 05 | 0.25 | not about | about |
| `changelog-rule-v2` | 06 | 0.28 | not about | about |
| `changelog-updates` | 05 | 0.33 | not about | about |
| `changelog-updates` | 06 | 0.27 | not about | about |
| `changelog-updates` | 11 | 0.49 | not about | about |
| `check-changelog-on-shop-edits` | 05 | 0.09 | not about | about |
| `check-changelog-on-shop-edits` | 06 | 0.11 | not about | about |
| `clock-in-billing` | 22 | 0.45 | not about | about |
| `exporter-completeness-rule` | 10 | 0.45 | not about | about |
| `use-billing-helpers` | 02 | 0.38 | not about | about |
| `use-billing-helpers` | 03 | 0.05 | not about | about |

## 2. Separation: KEPT vs BURIED-on-regression

| candidate | suite | injected | relevant | relevance | breadth | fate |
|---|---|---|---|---|---|---|
| `clock-in-billing` | 23 | 12 | 1 | 8% | 52% | BURIED-regression |
| `shop-clock-usage` | 25 | 25 | 4 | 16% | 100% | BURIED-regression |
| `check-changelog-on-shop-edits` | 6 | 6 | 1 | 17% | 100% | BURIED-gate5 |
| `enforce-shop-clock-v2` | 15 | 15 | 3 | 20% | 100% | BURIED-regression |
| `use-billing-helpers` | 3 | 3 | 1 | 33% | 100% | KEPT |
| `exporter-completeness-rule` | 12 | 3 | 2 | 67% | 25% | KEPT |
| `complete-exporter-setup` | 9 | 3 | 3 | 100% | 33% | KEPT |

- relevance judged by **Jev**: separates cleanly
- relevance judged by the **keyword oracle**: separates cleanly
- **breadth** (the free deterministic alternative): OVERLAPS — cannot discriminate

## 3. Calibration

| probability bucket | n | observed frequency |
|---|---|---|
| 0.0–0.2 | 73 | 4% |
| 0.2–0.4 | 5 | 100% |
| 0.4–0.6 | 6 | 100% |
| 0.6–0.8 | 3 | 100% |
| 0.8–1.0 | 17 | 100% |

Monotonic: **yes**.

## Honest limits

- n = 7 confirm-swept candidates. Small.
- The regression-buried ones share a theme, so the separation may be partly a theme artifact rather than a general law.
- The oracle this is scored against is a keyword matcher, and it reads `fix.patch` — which Jev is never sent. Disagreements are not automatically Jev's error.
- Those rollouts ran on claude-haiku-4-5-20251001. Firing rates may differ elsewhere.

Re-run after any Jev model version change: `python3 jev/validate.py --corpus jev/corpus`.
