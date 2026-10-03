# T15 · The same harness under a stronger model

Analysed separately from Haiku and never pooled with it. /prune under claude-sonnet-5 (model-upgrade), every item of R1: `exporter-checklist` ACCEPT; `billing-helpers` ACCEPT; `changelog-requirement` REJECT; `shop-clock-rule` REJECT. ACCEPT means removing it cost nothing under this model.

| family | none | evolved | paired diff | 95% CI |
|---|---|---|---|---|
| A | 94% | 100% | +6 | [+0, +17] |
| B | 100% | 100% | +0 | [+0, +0] |
| C | 78% | 89% | +11 | [-11, +39] |
| D | 100% | 100% | +0 | [+0, +0] |
| E | 83% | 89% | +6 | [-11, +22] |
| A+B+C+E | 91% | 96% | +6 | [-3, +14] |
