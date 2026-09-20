# `jev/` — the evidence, and the gate

This directory exists to answer one question before any Jev code is written:

> Does a calibrated judge tell Cortex something a free deterministic check cannot?

## Files

| File | What it is | Needs a key |
|---|---|---|
| `corpus.py` | builds the `(candidate, task)` firing corpus from `.evolve/runs/*.jsonl` | no |
| `evidence.py` | reproduces every number in §1 of `../jev_integration_plan.md` | no |
| `EVIDENCE.txt` | the recorded output of `evidence.py` on `cortex-lab` run R1 | no |
| `validate.py` | **J0** — the same test with real Jev calls instead of the keyword oracle | yes |
| `RESULTS.md` | written by `validate.py`; the gate's verdict. Its first lines carry the model id `bin/jev.py` reads back on every call | — |
| `corpus/` | a **committed snapshot** of exactly the rows J0 scored | no |

## Run the evidence (no key, no network)

```bash
python3 jev/evidence.py                       # defaults to cortex-lab
python3 jev/evidence.py /path/to/repo/.evolve # any repo with sweep history
python3 jev/validate.py --dry-run             # the same baseline, in J0's own words
```

## Run the gate (needs a key)

```bash
python3 jev/validate.py                       # score a repo's sweep history
python3 jev/validate.py --corpus jev/corpus   # replay the committed snapshot
python3 jev/validate.py --snapshot-only       # rebuild the snapshot, ask nothing
```

Exit **0** = PASS · **1** = FAIL (stop, and archive this directory with the
numbers) · **2** = there was no corpus to score, so there is no result.

### Why `corpus/` is committed

`cortex clean --runs` deletes `.evolve/runs/*.jsonl`, which is this whole
directory's evidence base and the only thing `RESULTS.md` rests on. So
`validate.py` snapshots every row it scored — the sweeps, the task prompts and
notes it sent, the graveyard entries it read the verdicts from, and the
candidates' own text — into `corpus/` before it scores anything. One cleanup
would otherwise make every number here unfalsifiable.

J0 is a property of **a corpus**, not of an install: one repo's green J0
licenses the feature everywhere, and `RESULTS.md` names which repo and which
snapshot it used.

## What it shows

On `cortex-lab` R1 (984 rollouts, 26 sweeps, 10 candidates, $107.53):

- **73.5% of spend** went to candidates buried for *breaking things*, not for
  failing to trigger. One theme — a `shop/**` clock rule, four attempts — took
  694 rollouts and $77.70 and landed nothing.
- Those candidates share a property visible **before** any sweep: they are
  injected into tasks they are not about. Relevance 8% / 16% / 20%, against
  100% for all three items that were kept.
- The free alternative (glob breadth) **cannot** separate them: 100% breadth
  appears in both the kept and the buried group.
- Firing is not noise — 88.4% of repeated `(candidate, task)` cells are
  unanimous — and the tier predicts it: a visible rule fires **100%** of the
  time, a gated skill 27%, an always-on skill 0%.

## The honest caveat

`evidence.py` judges "is this task about X" with a hand-written keyword matcher,
not with Jev. It proves the **signal exists and separates**. It does not prove
Jev can compute it. That is `validate.py` (J0), and until J0 is green nothing in
`../jev_integration_plan.md` ships.

The oracle also reads **more** than Jev is ever sent: it matches against
`fix.patch` as well as the prompt and the notes. That makes it a harder baseline
rather than an easier one — and it means a disagreement is not automatically
Jev's error.

Sample size is 6 confirm-swept candidates, three of them the same theme, all on
Haiku 4.5. Treat the separation as a strong lead, not a law.
