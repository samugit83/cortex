#!/usr/bin/env python3
"""gen_results_data.py — the numbers §5's charts draw, as diagrams/results.js.

  make diagrams      (runs it with the analysis environment, after gen_numbers.py)

Every value is computed by the lab's own analysis code (lab/reports/analysis): the
paired cells, the two-way bootstrap, the permutation test and Holm's correction, with
the same definitions the scorecard uses. The pooled result, the control family, the A/A
check, the ablations and the model change are recomputed here and must match the
scorecard to the printed digit, or the script stops: a chart can never disagree with the
text. Writes paper/diagrams/results.js, and the same object to
lab/reports/paper-data/figures-results.json, which is part of the repository.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CORTEX = Path(__file__).resolve().parents[3]
PAPER = CORTEX / "paper"                      # the paper's sources, kept outside the repository
sys.path.insert(0, str(CORTEX / "lab" / "reports" / "analysis"))
import load                                   # noqa: E402
import paper_data                             # noqa: E402  the same numbers, as data in the repository
import rescore                                # noqa: E402  the loop's verdicts, by score.sh's rules
import rebuild as RB                          # noqa: E402  arm_pair: the scorecard's comparison
import stats as S                             # noqa: E402

OUT = PAPER / "diagrams" / "results.js"
NAMES = {"A": "user-visible change", "B": "money", "C": "new exporter", "D": "control",
         "E": "time"}


def pts(x):
    return round(100 * x, 1)


def rates(cells):
    """Per arm: the mean over runs of the mean over that run's tasks (as paired_mean),
    and each run's own mean, for the dots."""
    by_run = defaultdict(lambda: ([], []))
    for (run, _task), (_f, pa, pb, _na, _nb) in cells.items():
        by_run[run][0].append(pa)
        by_run[run][1].append(pb)
    runs = {r: (sum(a) / len(a), sum(b) / len(b)) for r, (a, b) in sorted(by_run.items())}
    a = sum(v[0] for v in runs.values()) / len(runs)
    b = sum(v[1] for v in runs.values()) / len(runs)
    return a, b, runs


def pair(d, runs, a, b, fams, complete_case):
    r = RB.arm_pair(d, runs, a, b, families=fams, complete_case=complete_case)
    ra, rb, per_run = rates(r["cells"])
    return {"a": pts(ra), "b": pts(rb), "diff": pts(r["mean"]), "lo": pts(r["lo"]),
            "hi": pts(r["hi"]), "p": r["p"], "cells": len(r["cells"]),
            "runs": {k: [pts(x), pts(y)] for k, (x, y) in per_run.items()}}


def check(label, got, card):
    """got = (mean, lo, hi) in points; card = the scorecard's printed estimate/interval."""
    est = float(re.search(r"([+-]?[0-9.]+)", card["estimate"]).group(1))
    lo, hi = (float(x) for x in re.findall(r"([+-]?[0-9.]+)", card["interval"])[:2])
    want = (est, lo, hi)
    if any(abs(g - w) > 0.051 for g, w in zip(got, want)):
        raise SystemExit(f"gen_results_data.py: {label} is {got}, the scorecard says {want}")


def main():
    d = load.Data()
    ev = d.evaluation
    cards = json.loads((load.DATA / "scorecard.json").read_text())
    cards = {c["id"]: c for c in (cards if isinstance(cards, list) else cards.get("hypotheses", []))}
    R = {"families": NAMES, "runs": list(ev)}

    # ---- the headline: each family and the pool, complete-case (the primary set) ------
    head = {}
    for f in "ABCDE":
        head[f] = pair(d, ev, "none", "evolved", (f,), True)
    head["pool"] = pair(d, ev, "none", "evolved", tuple(load.RULE_FAMILIES), True)
    adj = S.holm([head[f]["p"] for f in load.RULE_FAMILIES])
    for f, p in zip(load.RULE_FAMILIES, adj):
        head[f]["holm"] = p
    check("H1", (head["pool"]["diff"], head["pool"]["lo"], head["pool"]["hi"]), cards["H1"])
    check("H2", (head["D"]["diff"], head["D"]["lo"], head["D"]["hi"]), cards["H2"])
    R["headline"] = head

    # ---- the A/A check: the same harness twice, R1, every family (report.py's definition)
    aa = S.cells(d.bench(runs=ev, arms=("none", "none2"), split="holdout"), "none", "none2",
                 families=list("ABCDE"), split="holdout")
    lo, hi, _ = S.two_way_bootstrap(aa)
    R["aa"] = {"diff": pts(S.paired_mean(aa)), "lo": pts(lo), "hi": pts(hi),
               "run": sorted({run for run, _ in aa})}

    # ---- the ablations: each arm against `evolved`, in the run that measured it -------
    abl = []
    measured = {(r["run"], r.get("arm")) for r in d.bench(runs=ev, split="holdout")}
    ablation_run = sorted({run for run, arm in measured if arm == "kitchen"})
    for arm in ("none", "none2", "kitchen", "ideal", "flat", "desc-only", "accept-all"):
        # the runs whose benchmark measured this arm (an arm identical to `evolved` in a
        # run was not benchmarked there); `none` is compared inside the ablation run
        runs = ablation_run if arm == "none" else [run for run in ev if (run, arm) in measured]
        if not runs:
            continue
        r = pair(d, runs, "evolved", arm, tuple(load.RULE_FAMILIES), False)
        abl.append({"arm": arm, "runs": runs, "evolved": r["a"], "rate": r["b"],
                    "diff": r["diff"], "lo": r["lo"], "hi": r["hi"],
                    "chars": d.arm_meta(runs, arm, "always_on_chars"),
                    "evolved_chars": d.arm_meta(runs, "evolved", "always_on_chars")})
    by = {a["arm"]: a for a in abl}
    if by["accept-all"]["runs"] == ablation_run:
        raise SystemExit("gen_results_data.py: accept-all was expected outside the ablation run")
    check("H6", (by["accept-all"]["diff"], by["accept-all"]["lo"], by["accept-all"]["hi"]), cards["H6"])
    check("H7", (by["flat"]["diff"], by["flat"]["lo"], by["flat"]["hi"]), cards["H7"])
    k = by["kitchen"]                           # the scorecard prints kitchen − evolved
    check("H8", (k["diff"], k["lo"], k["hi"]),
          {"estimate": f"-{cards['H8']['estimate'].split(' points')[0].split()[-1]}",
           "interval": cards["H8"]["interval"]})
    R["ablations"] = abl

    # ---- the model change: the same harness under each model --------------------------
    mc = [r["run"] for r in d.of_kind("model-change")]
    src = d.same_harness(mc)
    fams = tuple(load.RULE_FAMILIES)
    R["model"] = {"source": src, "strong_runs": mc,
                  "weak": pair(d, src, "none", "evolved", fams, False),
                  "strong": pair(d, mc, "none", "evolved", fams, False),
                  "weak_by_family": {f: pair(d, src, "none", "evolved", (f,), False) for f in "ABCDE"},
                  "strong_by_family": {f: pair(d, mc, "none", "evolved", (f,), False) for f in "ABCDE"}}
    h13 = cards["H13"]["estimate"]
    haiku = float(re.search(r"gains ([+-][0-9.]+) under Haiku", h13).group(1))
    strong = float(re.search(r"and ([+-][0-9.]+) under", h13).group(1))
    if abs(R["model"]["weak"]["diff"] - haiku) > 0.051 or abs(R["model"]["strong"]["diff"] - strong) > 0.051:
        raise SystemExit("gen_results_data.py: the model-change gains disagree with H13")

    # ---- why held-out rollouts fail: the oracle's verdict on every primary-arm rollout
    # of the scenarios valid in every run (the headline's set, so the passes are its bars)
    cc = set.intersection(*[{x["task"] for x in d.bench(runs=[r], split="holdout")} for r in ev])
    fails = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for r in d.bench(runs=ev, arms=("none", "evolved"), split="holdout"):
        if r.get("valid", 1) and r["task"] in cc:
            v = "pass" if r["pass"] else ("rule" if r.get("verdict") == r["family"] else r.get("verdict"))
            if v not in ("pass", "rule", "test", "tampered"):
                raise SystemExit(f"gen_results_data.py: an oracle verdict the figure has no place for: {v}")
            fails[r["family"]][r["arm"]][v] += 1
            fails[r["family"]][r["arm"]]["n"] += 1
    for f in "ABCE":                            # the passes are the headline's pass rates
        for arm, i in (("none", "a"), ("evolved", "b")):
            if abs(100 * fails[f][arm]["pass"] / fails[f][arm]["n"] - head[f][i]) > 0.051:
                raise SystemExit(f"gen_results_data.py: family {f}'s passes are not the headline's")
    R["failures"] = {f: {a: dict(v) for a, v in arms.items()} for f, arms in fails.items()}

    # ---- what each run kept, and whether it reached the held-out tasks ------------------
    fam_of = {(r["run"], r["name"]): r["family"] for r in
              csv.DictReader(open(CORTEX / "lab" / "reports" / "tables" / "T6-items.csv")) if r["fate"] == "kept"}

    def scope_label(paths):
        if len(paths) == 1 and ("*" in paths[0] or paths[0].endswith("/")):
            return paths[0], True               # a glob, printed as it is
        common = paths[0].rsplit("/", 1)[0] + "/"
        while not all(p.startswith(common) for p in paths):
            common = common.rstrip("/").rsplit("/", 1)[0] + "/"
        return f"{len(paths)} file{'s' if len(paths) > 1 else ''} in {common}", False
    grid = {}
    for run in ev:
        grid[run] = {}
        for f in load.RULE_FAMILIES:
            its = [i for i in d.items if i["run"] == run and i.get("fate") == "kept" and fam_of.get((run, i["name"])) == f]
            rs = [r for r in d.bench(runs=[run], arms=("evolved",), split="holdout")
                  if r.get("family") == f and r.get("valid", 1) and r["task"] in cc]
            names = {i["name"] for i in its}
            loaded = sum(1 for r in rs if names & set(r.get("fired") or []))
            # the run's gain on this family, from the exact per-scenario rates (the headline's set)
            rc = {k: v for k, v in S.cells(d.bench(runs=[run], arms=("none", "evolved"), split="holdout"),
                                           "none", "evolved", families=[f], split="holdout").items() if k[1] in cc}
            gain = 100 * sum(v[2] - v[1] for v in rc.values()) / len(rc)
            grid[run][f] = {"items": [{"name": i["name"], "kind": i["kind"], "scope": scope_label(i["paths"])[0],
                                       "glob": scope_label(i["paths"])[1]} for i in its],
                            "loaded": loaded, "n": len(rs), "gain": round(gain + 0.0, 1)}
            if not its:
                raise SystemExit(f"gen_results_data.py: {run} kept nothing for family {f}")
    R["kept_grid"] = grid

    # ---- every confirm sweep of the loop: what it won against the worst it lost ---------
    sc = []
    for c in rescore.candidates():
        for s in c["sweeps"]:
            if s["phase"] == "confirm":
                sc.append({"run": c["run"], "name": c["name"], "net": round(s["net_runs"]),
                           "drop": round(s["D"], 3), "verdict": c["verdict"],
                           "rechecked": bool(c.get("rechecked")), "protected": bool(s.get("failed") and "gate3" in s["failed"])})
    R["confirm_sweeps"] = sc

    # ---- every held-out scenario under every arm, in the run that measured it -----------
    cols = [(run, arm) for run in ev for arm in ("none", "evolved")]
    abl_run = next(a["runs"][0] for a in abl if a["arm"] == "kitchen")
    cols += [(abl_run, arm) for arm in ("none2", "kitchen", "ideal", "flat", "desc-only")]
    cols += [(run, "accept-all") for run in ev if (run, "accept-all") in measured]
    cells = defaultdict(lambda: [0, 0])
    for r in d.bench(runs=ev, split="holdout"):
        if r.get("valid", 1) and (r["run"], r["arm"]) in cols:
            cells[(r["task"], r["run"], r["arm"])][0] += r["pass"]
            cells[(r["task"], r["run"], r["arm"])][1] += 1
    tasks = sorted({t for t, _r, _a in cells})
    fam_task = {r["task"]: r["family"] for r in d.bench(runs=ev, split="holdout")}
    R["heatmap"] = {"cols": [{"run": r, "arm": a} for r, a in cols],
                    "rows": [{"task": t, "family": fam_task[t],
                              "cells": [round(100 * cells[(t, r, a)][0] / cells[(t, r, a)][1])
                                        if cells[(t, r, a)][1] else None for r, a in cols]} for t in tasks]}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("// generated by lab/reports/analysis/gen_results_data.py from lab/reports/data — do not edit\n"
                   "window.DATA = window.DATA || {};\nwindow.DATA.results = "
                   + json.dumps(R, indent=1) + ";\n")
    print(f"-> {OUT}")
    paper_data.write_figures("results", R)


if __name__ == "__main__":
    main()
