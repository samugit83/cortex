# T4 · Main results: family x arm x split

Rows are over the complete-case set, the scenarios valid in every run (the primary, as in H1), except the last, which pools every valid scenario. Rates are over rollouts with Wilson intervals (description only: they ignore that repeats of one task are correlated). The paired difference and its interval are over TASKS and RUNS, which is the inference. Holm is applied across the four rule families on the holdout.

| split | family | tasks | rollouts | none | evolved | paired diff | bootstrap 95% CI | permutation p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| holdout | A user-visible change (CHANGELOG) | 20 | 200 | 0% [+0, +4] | 97% [+92, +99] | +97 | [+91, +100] | 0.0001 | 0.0004 |
| holdout | B money (billing) | 24 | 240 | 26% [+19, +34] | 79% [+71, +85] | +53 | [+18, +88] | 0.0001 | 0.0004 |
| holdout | C new exporter | 24 | 240 | 2% [+0, +6] | 52% [+43, +60] | +50 | [+25, +73] | 0.0001 | 0.0004 |
| holdout | D control (plain bugs) | 24 | 240 | 100% [+97, +100] | 99% [+95, +100] | -1 | [-5, +0] | 1.0000 |  |
| holdout | E time (clock) | 24 | 240 | 55% [+46, +64] | 82% [+74, +88] | +27 | [+2, +60] | 0.0001 | 0.0004 |
| holdout | A+B+C+E pooled | 92 | 920 | 22% [+18, +26] | 77% [+72, +80] | +55 | [+34, +74] | 0.0001 |  |
| train | A user-visible change (CHANGELOG) | 24 | 144 | 0% [+0, +5] | 90% [+81, +95] | +90 | [+78, +100] | 0.0001 |  |
| train | B money (billing) | 24 | 144 | 12% [+7, +22] | 89% [+80, +94] | +76 | [+53, +93] | 0.0001 |  |
| train | C new exporter | 24 | 144 | 4% [+1, +12] | 76% [+65, +85] | +72 | [+44, +92] | 0.0001 |  |
| train | D control (plain bugs) | 16 | 96 | 100% [+93, +100] | 98% [+89, +100] | -2 | [-8, +0] | 1.0000 |  |
| train | E time (clock) | 16 | 96 | 10% [+5, +22] | 85% [+73, +93] | +75 | [+54, +92] | 0.0001 |  |
| train | A+B+C+E pooled | 88 | 528 | 6% [+4, +10] | 85% [+80, +89] | +79 | [+69, +87] | 0.0001 |  |
| holdout | A+B+C+E pooled, every valid scenario (secondary) | 95 | 950 | 21% [+17, +25] | 77% [+73, +81] | +56 | [+35, +75] | 0.0001 |  |
