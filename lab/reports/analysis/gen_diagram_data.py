#!/usr/bin/env python3
"""gen_diagram_data.py — the numbers the diagrams show, as diagrams/data.js.

  python3 lab/reports/analysis/gen_diagram_data.py   (after gen_numbers.py)

Diagrams are HTML; the ones that show data read window.DATA from this file, so a
diagram can never disagree with the rows or with the paper's text. The design's
parameters are read back from generated/numbers.tex, the same macros the text uses.
Standard library only.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# the re-scorer lives beside this script, with the lab's analysis (standard library only)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rescore                                # noqa: E402  the rules of Table 2, from the rollouts

PAPER = Path(__file__).resolve().parents[3] / "paper"   # the paper's sources, kept outside the repository
DATA = PAPER.parent / "lab" / "reports" / "data"
TABLES = PAPER.parent / "lab" / "reports" / "tables"
OUT = PAPER / "diagrams" / "data.js"
EVAL = ("R1", "R2", "R3", "R4")
RULE_FAMILIES = ("A", "B", "C", "E")
# the sweep fig:sweep draws: a KEPT rule whose exposure is a small part of the suite
GRID = ("R3", "exporter-checklist-v2")
# the sweep beside it: a rule that won runs and was still killed, on gate 3 alone, in the
# confirm and again in the recheck (the clock rule of §5)
KILLED = ("R3", "shop-clock-access")


def rows(name):
    return [json.loads(l) for l in (DATA / name).read_text().splitlines() if l.strip()]


def macros():
    t = (PAPER / "generated" / "numbers.tex").read_text()
    return {k: v.replace("{,}", ",").replace(r"\textminus{}", "−").replace(r"\%", "%")
            for k, v in re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", t)}


def main():
    M = macros()
    roll, cyc, sw, items, gates = (rows(n) for n in
                                   ("rollouts.jsonl", "cycles.jsonl", "sweeps.jsonl",
                                    "items.jsonl", "gates.jsonl"))
    D = {"params": {k: M[k] for k in ("KScreen", "KConfirm", "RegressionTolerance", "MinNetRuns",
                                        "MaxInvalidPct", "RolloutTimeoutMin", "MinThemeOccurrences",
                                        "RolloutModelName", "StrongModelName", "PrimaryK", "AblationK",
                                        "StopAfterBarren")}}

    cands = rescore.candidates()               # every R1–R4 candidate, scored by the rules

    # ---- the sweep figure: one confirm sweep, cell by cell ---------------------
    run, cand = GRID
    cs = next(c for c in cands if (c["run"], c["name"]) == GRID)
    conf = next(x for x in cs["sweeps"] if x["phase"] == "confirm")
    rs = [r for r in roll if r.get("source") == "sweep" and r.get("sweep") == conf["sweep"]]
    k = conf["k"]
    exposed = set(conf["exposed"])             # as score.sh decides it: visible in a cand rollout
    grid = []
    for t in sorted({r["task"] for r in rs}):
        cell = {"task": t, "base": [None] * k, "cand": [None] * k, "exposed": t in exposed}
        for r in rs:
            if r["task"] == t:
                cell[r["arm"]][r["r"] - 1] = ("pass" if r.get("valid") and r["pass"]
                                              else "fail" if r.get("valid") else "invalid")
        grid.append(cell)
    exp = [g for g in grid if g["exposed"]]
    item = next(i for i in items if i["run"] == run and i["name"] == cand)
    D["grid"] = {"run": run, "candidate": cand, "kind": item.get("kind"),
                 "paths": item.get("paths"), "verdict": cs["verdict"], "k": k,
                 "tasks": grid, "exposed": len(exp),
                 "base_pass": sum(v == "pass" for g in exp for v in g["base"]),
                 "cand_pass": sum(v == "pass" for g in exp for v in g["cand"]),
                 "runs_exposed": len(exp) * k,
                 # Eq. (1), in pass-rate units summed over exposed tasks; net also in runs
                 "gain": round(conf["G"], 2), "regression": round(conf["regression"], 2),
                 "worst_drop": round(conf["D"], 2), "net_runs": round(conf["net_runs"]),
                 "fired": conf["fired"]}

    # ---- beside it: a confirm sweep the gates killed, and the recheck that settled it --
    def cells(sweep, k):
        out = {}
        for r in roll:
            if r.get("source") == "sweep" and r.get("sweep") == sweep:
                c = out.setdefault(r["task"], {"task": r["task"], "base": [None] * k, "cand": [None] * k})
                c[r["arm"]][r["r"] - 1] = ("pass" if r.get("valid") and r["pass"]
                                           else "fail" if r.get("valid") else "invalid")
        return [out[t] for t in sorted(out)]

    fam = {(r["run"], r["name"]): r["family"].strip("—") for r in
           csv.DictReader(open(TABLES / "T6-items.csv"))}
    kc = next(c for c in cands if (c["run"], c["name"]) == KILLED)
    ph = {x["phase"]: x for x in kc["sweeps"]}
    kconf, krec = ph["confirm"], ph.get("recheck")
    if not (kc["verdict"] == "KILL" and kconf["verdict"] == "RECHECK" and krec
            and kconf["failed"] == ["gate3"]):
        raise SystemExit(f"gen_diagram_data.py: {KILLED} is no longer a gate-3 KILL settled by a recheck")
    per = {p["task"]: p for p in kconf["per_task"]}
    kgrid = cells(kconf["sweep"], kconf["k"])
    for g in kgrid:
        p = per[g["task"]]
        g.update(exposed=p["exposed"], protected=p["exposed"] and p["base"] == 1,
                 regressed=g["task"] in kconf["regressed"])
    kexp = [g for g in kgrid if g["exposed"]]
    kitem = next(i for i in items if (i["run"], i["name"]) == KILLED)
    # the rule that took its place: the next candidate of the run for the same family
    later = [c for c in cands if c["run"] == KILLED[0] and fam.get((c["run"], c["name"])) == fam[KILLED]
             and c["sweeps"][0]["started"] > kc["sweeps"][0]["started"]]
    succ = min(later, key=lambda c: c["sweeps"][0]["started"])
    sitem = next(i for i in items if (i["run"], i["name"]) == (succ["run"], succ["name"]))
    if (succ["verdict"], KILLED[0], str(len(sitem["paths"]))) != ("KEEP", M["NarrowRun"], M["NarrowClockFiles"]):
        raise SystemExit("gen_diagram_data.py: the killed clock rule's successor is not the one §5 describes")
    D["kill"] = {"run": KILLED[0], "candidate": KILLED[1], "kind": kitem.get("kind"),
                 "paths": kitem.get("paths"), "k": kconf["k"], "tasks": kgrid, "ntasks": len(kgrid),
                 "exposed": len(kexp), "protected": sum(g["protected"] for g in kgrid),
                 "base_pass": sum(v == "pass" for g in kexp for v in g["base"]),
                 "cand_pass": sum(v == "pass" for g in kexp for v in g["cand"]),
                 "runs_exposed": len(kexp) * kconf["k"],
                 "gain": round(kconf["G"], 2), "regression": round(kconf["regression"], 2),
                 "worst_drop": round(kconf["D"], 2), "net": round(kconf["N"], 2),
                 "net_runs": round(kconf["net_runs"]), "fired": kconf["fired"],
                 "regressed": kconf["regressed"], "confirm_verdict": kconf["verdict"],
                 "recheck": cells(krec["sweep"], krec["k"]), "verdict": kc["verdict"],
                 "successor": {"name": succ["name"], "files": len(sitem["paths"])}}

    # ---- the funnel: every /evolve cycle of the evaluation runs ----------------
    # cycles come from the journal (a barren cycle runs no sweep); candidates, stages and
    # verdicts from the sweeps, scored by the rules — not from what the agent journaled
    ev = [c for c in cyc if c["run"] in EVAL and c.get("is_cycle")]
    barren = sum(1 for c in ev if c.get("verdict") == "BARREN")
    at_screen = [c for c in cands if c["stage"] == "screen"]
    confirmed = [c for c in cands if c["stage"] == "confirm"]
    unscored = lambda cs_: sum(1 for c in cs_ if c["verdict"] == "RERUN" and c["recorded"] == "buried")
    rechecked = [c for c in confirmed if c["rechecked"]]
    stage = defaultdict(lambda: [0, 0.0])
    for s in sw:
        if s["run"] in EVAL:
            stage[s["phase"]][0] += s.get("rollouts") or 0
            stage[s["phase"]][1] += s.get("cost_usd") or 0
    D["funnel"] = {"cycles": len(ev), "barren": barren, "active": len(ev) - barren,
                   "swept": len(cands),
                   "stopped_screen": len(at_screen),
                   "killed_screen": sum(1 for c in at_screen if c["verdict"] == "KILL"),
                   "unscored_screen": unscored(at_screen),
                   "confirmed": len(confirmed),
                   "rechecked": len(rechecked),
                   "recheck_keep": sum(1 for c in rechecked if c["verdict"] == "KEEP"),
                   "recheck_kill": sum(1 for c in rechecked if c["verdict"] == "KILL"),
                   "keep": sum(1 for c in confirmed if c["verdict"] == "KEEP"),
                   "kill_confirm": sum(1 for c in confirmed if c["verdict"] == "KILL"),
                   "unscored_confirm": unscored(confirmed),
                   "rollouts": {p: v[0] for p, v in stage.items()},
                   "cost": {p: round(v[1], 2) for p, v in stage.items()},
                   "runs": len(EVAL)}
    # the figure and §5's text count the same things: stop if they ever disagree
    F = D["funnel"]
    same = {"LoopCycles": F["cycles"], "LoopBarren": F["barren"], "LoopSwept": F["swept"],
            "KeptItems": F["keep"], "LoopKilled": F["killed_screen"] + F["kill_confirm"],
            "LoopUnscored": F["unscored_screen"] + F["unscored_confirm"],
            "Rechecked": F["rechecked"], "RecheckKept": F["recheck_keep"],
            "LoopRollouts": f"{sum(F['rollouts'].values()):,}",
            "LoopConfirmRollouts": f"{F['rollouts']['confirm']:,}"}
    for k, v in same.items():
        if M[k] != str(v):
            raise SystemExit(f"gen_diagram_data.py: the funnel's {k} is {v}, the text's macro says {M[k]}")

    # ---- beside the funnel: every cycle of every run, in the order it ran ----------
    # A swept cycle is placed by its first sweep's start (the journal's own order is not
    # always the order of the sweeps); a barren cycle, which runs no sweep, keeps the place
    # the journal gives it. A candidate with no journal entry of its own was swept inside
    # the cycle whose journaled candidate came next.
    seqs, first = [], lambda c: c["sweeps"][0]["started"]
    for run in EVAL:
        jc = sorted((c for c in ev if c["run"] == run), key=lambda c: c["journal_index"])
        named = {c["name"] for c in jc if c.get("verdict") != "BARREN"}
        groups, pending = {}, []
        for c in sorted((c for c in cands if c["run"] == run), key=first):
            pending.append(c)
            if c["name"] in named:
                groups[c["name"]], pending = pending, []
        if pending or set(groups) != named:
            raise SystemExit(f"gen_diagram_data.py: {run}'s sweeps and journal do not pair up")
        swept = iter(sorted(groups.values(), key=lambda g: first(g[-1])))
        cells_, have, full_at = [], set(), None
        for c in jc:
            if c.get("verdict") == "BARREN":
                cells_.append({"barren": True})
                continue
            g = next(swept)
            cells_.append({"barren": False, "items": [
                {"name": x["name"], "family": fam.get((run, x["name"]), ""), "verdict": x["verdict"],
                 "rechecked": x["rechecked"]} for x in g]})
            have |= {fam.get((run, x["name"])) for x in g if x["verdict"] == "KEEP"}
            if full_at is None and set(RULE_FAMILIES) <= have:
                full_at = len(cells_) - 1
        seqs.append({"run": run, "cycles": cells_,
                     "swept": sum(len(x["items"]) for x in cells_ if not x["barren"]),
                     "kept": sum(i["verdict"] == "KEEP" for x in cells_ if not x["barren"] for i in x["items"]),
                     "barren_after_full": sum(x["barren"] for x in cells_[full_at + 1:])})
    D["cycles"] = {"runs": seqs, "ncycles": max(len(s["cycles"]) for s in seqs),
                   "barren": sum(x["barren"] for s in seqs for x in s["cycles"]),
                   "barren_after_full": sum(s["barren_after_full"] for s in seqs)}
    if (sum(len(s["cycles"]) for s in seqs), D["cycles"]["barren"], sum(s["swept"] for s in seqs),
            sum(s["kept"] for s in seqs)) != (F["cycles"], F["barren"], F["swept"], F["keep"]):
        raise SystemExit("gen_diagram_data.py: the cycle timeline does not add up to the funnel")

    # ---- loaded vs chosen --------------------------------------------------------
    # every candidate of a tier, in every run where it was offered: the loop's sweeps and
    # the gate test's screens (tiers as each sweep recorded them). No selection by outcome.
    kept = [i for i in items if i["run"] in EVAL and i.get("fate") == "kept"]
    kept_skills = [i for i in kept if i.get("kind") == "skill"]
    offered = {"always": [0, 0], "gated": [0, 0]}
    for r in roll:
        if (r.get("source") == "sweep" and r["run"] in EVAL and r.get("arm") == "cand"
                and r.get("candidate_tier") in offered and r.get("valid", 1)):
            if r["candidate"] in (r.get("visible") or []):
                offered[r["candidate_tier"]][0] += 1
                offered[r["candidate_tier"]][1] += r["candidate"] in (r.get("fired") or [])
    n_always_gate = 0
    for g in gates:
        sc = g.get("screen") or {}
        if sc.get("candidate_tier") == "always":
            n_always_gate += 1
            offered["always"][0] += sc.get("candidate_visible_runs") or 0
            offered["always"][1] += sc.get("candidate_fired_runs") or 0
    swept_by_tier = defaultdict(int)
    for c in cands:
        swept_by_tier[{"rule": "rule", "gated": "gated", "always": "always"}.get(c["tier"], c["tier"])] += 1
    D["loaded"] = {"kept_rules": sum(1 for i in kept if i.get("kind") == "rule"),
                   "kept_skills": len(kept_skills),
                   "kept_skill_paths": sorted({p for i in kept_skills for p in (i.get("paths") or [])}),
                   "gated": {"offered": offered["gated"][0], "invoked": offered["gated"][1]},
                   "always": {"offered": offered["always"][0], "invoked": offered["always"][1],
                              "candidates": n_always_gate + swept_by_tier["always"]},
                   "swept": dict(swept_by_tier)}

    # ---- the setup figures (§4): the design of the lab, the runs and the tests --------
    D["setup"] = {k: M[k] for k in (
        "SessionsPerRun", "Rounds", "TrainTasks", "HoldoutTasks", "EvalRuns", "TrainK",
        "ConfirmSweepRollouts", "MaxRunsDefault", "MaxRunsEval", "StopAfterBarrenEval",
        "ClaudeCodeVersion", "CompleteTasks", "GateCandidates", "Placebos", "PlaceboTopic",
        "PlaceboMoment", "Harmful", "Positives", "Planted", "RunOneItems", "ModelChangeK",
        "SecondRepo", "SecondRepoHoldout", "SecondRepoK", "ExcludedScenario", "ExcludedFrom")}
    D["setup"]["families"] = {f: {"train": M["TrainFam" + f], "holdout": M["HoldFam" + f]}
                              for f in "ABCDE"}
    # the lab's schedule: which family each round's sessions belong to (scenarios.py: ROUNDS)
    sys.path.insert(0, str(PAPER.parent / "lab" / "bin"))
    import scenarios                          # noqa: E402  the lab's scenarios, standard library only
    D["setup"]["rounds"] = [[scenarios.by_id(sid)["family"] for sid in scenarios.ROUNDS[r]]
                            for r in sorted(scenarios.ROUNDS)]
    autopilot = (PAPER.parent / "lab" / "bin" / "autopilot").read_text()
    D["setup"]["max_corrections"] = int(re.search(r"^MAX_CORRECTIONS = (\d+)", autopilot, re.M).group(1))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("// generated by lab/reports/analysis/gen_diagram_data.py from lab/reports/data — do not edit\n"
                   "window.DATA = " + json.dumps(D, indent=1) + ";\n")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
