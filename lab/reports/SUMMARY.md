# Cortex, in one page

**The claim.** An agent's context should be measured, not curated. Cortex watches real sessions, proposes a skill or a rule from what went wrong, runs the agent with and without it on tasks harvested from those sessions, and keeps it only if the pass rate moves and nothing else breaks.

**The headline.** On holdout tasks never seen during evolution, the evolved harness beats no harness by **+55.0 points** [+34.1, +74.1] across the four families that have a house rule. The control family, which has none, moves -0.8 points.

| | |
|---|---|
| INCONCLUSIVE | 2 |
| NOT SUPPORTED | 4 |
| SUPPORTED | 11 |

**What it cost.** $1,196 measured for the programme, within a $1,500 cap (the development run before it: $155).

## The three limits

1. **One synthetic repository and four lintable rules.** A machine can tell whether these rules were followed. Rules that need judgement are not tested here at all, and that is the clearest limit on the whole claim.
2. **The gain is a property of a weak model.** Every primary number is `claude-haiku-4-5`. Under `claude-sonnet-5` the same harness gains **+5.6** points where it gained **+66.7** under Haiku (R1's harness), because the stronger model already follows most house rules without a harness; one `/prune` pass after the upgrade, at k=3, found 2 of its 4 items removable (exporter-checklist, billing-helpers). The loop is worth most where the model is weakest.
3. **A judge in the proposal layer.** Cortex ships one. Every primary number here was produced with it off, the gates contain no model and a test asserts so — and its own validation gate failed at 90 % before being lowered to 85 %.

A second, real repository nobody here built is reported separately in §13, never pooled. **On it the loop learned nothing**: the agent was rarely corrected, so no problem recurred and Cortex declined to invent a rule. It shows when the loop has work to do, and does not test whether what it learns transfers.

Full report: [`REPORT.md`](REPORT.md). Rebuild every number offline with `lab/reports/analysis/run.sh`.
