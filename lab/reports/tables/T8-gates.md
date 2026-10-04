# T8 · Gate calibration against known answers

KEEP, KILL and RERUN are score.sh's verdicts, after the confirm for a candidate that reached one. `stopped (procedure)` counts the candidates the test's procedure stopped, which it does at any screen whose gain is not positive or whose candidate never fired, whatever score.sh said; a RERUN means no task in the screen could show a gain, so no gate judged the candidate. Clopper-Pearson intervals; the last column is the one-sided 95 % upper bound, which is the number to quote when nothing was kept. Fisher's exact, positives against placebos: p = 0.02174.

| candidate type | n | KEEP | KILL | RERUN | stopped (procedure) | KEEP rate | 95% CI | ever fired | one-sided upper |
|---|---|---|---|---|---|---|---|---|---|
| harmful | 5 | 0 | 2 | 3 | 5 | 0% | [0%, 52%] | 3/5 | 45% |
| placebo-moment | 10 | 0 | 5 | 5 | 10 | 0% | [0%, 31%] | 0/10 | 26% |
| placebo-topic | 10 | 0 | 7 | 3 | 10 | 0% | [0%, 31%] | 0/10 | 26% |
| positive | 4 | 2 | 1 | 1 | 2 | 50% | [7%, 93%] | 2/4 | 90% |
