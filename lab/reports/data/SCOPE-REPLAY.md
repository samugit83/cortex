# scope-replay — does pre-sweep relevance predict the verdict?

_source: `<workspace>/cortex-eval/runs/R4/cortex-lab-R4/.evolve` · 7 candidate(s) · judge: on_

`cortex scope` runs before a sweep is paid for. Every number below was
computed from the candidate's own text and the run's task suite — never
from the verdict — and is then compared with what the sweep decided.

| candidate | kind | inj/suite | relevance | breadth | fate | rollouts | cost |
|---|---|---|---|---|---|---|---|
| `changelog-for-user-visible-changes` | rule | 25/25 | 12% | 100% | BURIED-gate5 | 12 | $1.43 |
| `changelog-contributing-reminder` | rule | 25/25 | 16% | 100% | BURIED-gate5 | 12 | $1.65 |
| `shop-clock-queries` | rule | 18/25 | 17% | 72% | KEPT | 98 | $11.07 |
| `billing-rates-helpers` | rule | 9/25 | 44% | 36% | KEPT | 30 | $3.32 |
| `shop-changelog-reminder` | rule | 18/25 | 44% | 72% | KEPT | 132 | $16.14 |
| `exporter-checklist` | skill | 4/25 | 100% | 16% | KEPT | 66 | $10.37 |
| `changelog-moment-check` | skill | 0/25 | — | 0% | BURIED-gate5 | 12 | $1.66 |
| | | | | | _always-on: scope does not apply_ | | |

## Separation

- **relevance (needs a judge)**: not enough of both groups to say
- **breadth (free, deterministic)**: not enough of both groups to say

## Counterfactual

At floor 0.35, `cortex scope` flags **2** candidate(s) that
the sweeps went on to bury: **24 rollouts, $3.08**.

It also flags **1** candidate(s) that were KEPT (`shop-clock-queries`) — these are the

  false alarms: `shop-clock-queries`

**This is advisory in Cortex and advisory here.** The warning never blocked
a sweep, and no number above changed a verdict. It is scored, not obeyed.
