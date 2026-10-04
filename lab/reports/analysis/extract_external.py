#!/usr/bin/env python3
"""extract_external.py — the second repository's training, which the lab's export leaves out.

  python3 lab/reports/analysis/extract_external.py   -> lab/reports/data/external-training.json

lab/reports/data/external.jsonl records the second repository's benchmark, but not the
loop that came before it: how many sessions were played, how often the agent was
corrected, what the sessions left for Cortex to learn from, and what /evolve did with it.
The report and the paper quote those counts, so this script copies them from the run's own
records (the lab's session state, and Cortex's task store, lessons and journal in the
repository the run worked on) into one file beside the lab's other rows.

The raw directories live beside the repository (../cortex-eval/runs, or
$CORTEX_EVAL_RUNS). Without them the committed extract is kept as it is. Standard
library only; writes only lab/reports/data/external-training.json.
"""
import json
import os
import re
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[1]
CORTEX = REPORTS.parents[1]
RAW = Path(os.environ.get("CORTEX_EVAL_RUNS", CORTEX.parent / "cortex-eval" / "runs"))
OUT = REPORTS / "data" / "external-training.json"
RUN = "X1"


def main():
    run = RAW / RUN
    if not run.is_dir():
        print(f"extract_external.py: no raw run at {run}; keeping {OUT}")
        return
    mani = json.loads((run / "manifest.json").read_text())
    split = json.loads((run / "split.json").read_text())
    state = json.loads((run / "state.json").read_text())
    evolve = Path(mani["repo"]).name            # the run's working copy, under the run's folder
    evolve = run / evolve / ".evolve"
    if set(state) != set(split["train"]):
        raise SystemExit("extract_external.py: the session state is not the training split")
    sessions = [{"task": t, "verdicts": state[t]["verdicts"], "corrections": state[t]["corrections"]}
                for t in split["train"]]
    # one line per correction, in the format /harvest writes: `date | task NN | ... | ...`
    lessons = [l for l in (evolve / "lessons.md").read_text().splitlines()
               if re.match(r"\d{4}-\d{2}-\d{2} \| ", l)]
    # one entry per /evolve cycle: `## date  (barren)`, or `## date  name — VERDICT`
    cycles = []
    for head in re.findall(r"(?m)^## (.+)$", (evolve / "journal.md").read_text()):
        barren = re.search(r"\(barren\)\s*$", head)
        verdict = "BARREN" if barren else (re.search(r"\b(KEEP|KILL|RERUN)\b", head) or [None, "?"])[1]
        cycles.append({"verdict": verdict})
    tasks = sorted(p.name for p in (evolve / "tasks").iterdir() if p.is_dir() and re.fullmatch(r"\d+", p.name))
    out = {"run": RUN, "base": mani["base"], "model": mani["model"], "sessions": sessions,
           "tasks": len(tasks), "lessons": len(lessons), "cycles": cycles,
           "kept": sum(1 for c in cycles if c["verdict"] == "KEEP")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"{len(sessions)} sessions, {len(tasks)} tasks, {len(lessons)} lessons, {len(cycles)} cycles -> {OUT}")


if __name__ == "__main__":
    main()
