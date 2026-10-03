#!/usr/bin/env python3
"""extract_prune.py — the prune test's rollouts, which the lab's export leaves out.

  python3 lab/reports/analysis/extract_prune.py   -> lab/reports/data/prune-sweeps.jsonl

lab/reports/data/prune*.jsonl record each prune verdict but not the sweeps behind it,
and the report and the paper quote what those sweeps saw: whether an item fired, which
tasks lost runs, how often the always-on skills planted for the test were opened. This
script copies the rollout rows of every replace-mode sweep of the two prune passes (PRUNE,
with the evaluation model, and M1, with the stronger one) from the raw run directories
into one file beside the lab's other rows, keeping only the fields a verdict depends on.
The paper's number script scores the sweeps again from it and stops if a verdict differs
from the lab's record.

The raw directories live beside the repository (../cortex-eval/runs, or
$CORTEX_EVAL_RUNS). Without them the committed extract is kept as it is. Standard
library only; writes only lab/reports/data/prune-sweeps.jsonl.
"""
import json
import os
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[1]
CORTEX = REPORTS.parents[1]
RAW = Path(os.environ.get("CORTEX_EVAL_RUNS", CORTEX.parent / "cortex-eval" / "runs"))
OUT = REPORTS / "data" / "prune-sweeps.jsonl"
PASSES = ("PRUNE", "M1")


def main():
    if not RAW.is_dir():
        print(f"extract_prune.py: no raw runs at {RAW}; keeping {OUT}")
        return
    rows = []
    for run in PASSES:
        for f in sorted((RAW / run / f"cortex-lab-{run}" / ".evolve" / "runs").glob("*.jsonl")):
            recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            head = next((r for r in recs if r.get("event") == "start"), {})
            if head.get("mode") != "replace":
                continue                      # the copied repository's own loop history
            removed = head.get("replaced") or []
            if len(removed) != 1:
                raise SystemExit(f"extract_prune.py: {f.name} removes {removed}, not one item")
            for r in recs:
                if r.get("event") is not None:
                    continue
                rows.append({"run": run, "sweep": f.name, "model": head.get("model"), "k": head.get("k"),
                             "removed": removed[0], "arm": r["v"], "task": r["t"], "r": r["r"],
                             "pass": r["pass"], "valid": r.get("valid", 1),
                             # score.sh reads `skills` as the items that fired (a skill invoked,
                             # a rule whose paths matched); null means the stream was unreadable
                             "fired": r.get("skills"), "visible": r.get("visible")})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    print(f"{len(rows)} rollouts -> {OUT}")


if __name__ == "__main__":
    main()
