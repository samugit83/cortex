#!/usr/bin/env python3
"""rescore.py — score every recorded sweep again, from its rollouts, by the paper's rules.

  python3 lab/reports/analysis/rescore.py            a table: each R1–R4 candidate, what the
                                              rules decide, and what was recorded

This is Eq. (1) and Table 2 of the paper — gain G, net N, worst drop D, protected set
P, firing f, RERUN, RECHECK — written again in Python from bin/score.sh at v1.0-eval,
and applied to lab/reports/data/rollouts.jsonl. It serves two purposes:

  * the figures and numbers about the loop's decisions come from the rules, not from
    the journal the /evolve agent wrote (gen_diagram_data.py imports it);
  * it checks the paper against the code: every KEEP the loop recorded must be a KEEP
    here too, and a recorded burial that the rules would not have decided is flagged.

Checked against bin/score.sh itself on the 51 raw R1–R4 sweep files: every verdict agrees.
What the exported rows cannot reproduce — the machine-load block (rows carry no `load`),
the planned-task and job-count checks (`outcome == "done"` stands in), the harness-hash
match of a recheck to its confirm — never fired in these runs.

Standard library only. Reads lab/reports/data; writes nothing.
"""
import json
import os
from collections import defaultdict
from pathlib import Path

# the same rows the rest of the analysis reads (load.py honours the same variable)
DATA = Path(os.environ.get("CORTEX_REPORT_DATA") or Path(__file__).resolve().parents[1] / "data")
EVAL = ("R1", "R2", "R3", "R4")
# the thresholds every evaluated run used (the tag's defaults; lab/rounds/round-00.md)
RTOL, MINNET, MAXINV = 0.34, 2, 0.1


def rows(name):
    return [json.loads(l) for l in (DATA / name).read_text().splitlines() if l.strip()]


def score(sweep, rs, k, cand):
    """One add-mode sweep, as score.sh's score_file() scores it."""
    valid = [r for r in rs if r.get("valid", 1) != 0]
    unknown = sum(1 for r in valid if r.get("fired") is None)
    fired = sum(1 for r in valid if r["arm"] == "cand" and cand in (r.get("fired") or []))
    vtracked = bool(valid) and all(r.get("visible") is not None for r in valid)
    runs = defaultdict(list)
    for r in valid:
        runs[(r["arm"], r["task"])].append(r["pass"])
    tasks = sorted({r["task"] for r in rs})
    measured = [t for t in tasks if len(runs[("base", t)]) >= k and len(runs[("cand", t)]) >= k]
    unmeasured = [t for t in tasks if t not in measured]
    exposed = None
    if vtracked and unknown == 0:
        exposed = {r["task"] for r in valid if r["arm"] == "cand" and cand in (r.get("visible") or [])}
    per = []
    for t in measured:
        b = sum(runs[("base", t)]) / len(runs[("base", t)])
        c = sum(runs[("cand", t)]) / len(runs[("cand", t)])
        per.append({"task": t, "base": b, "cand": c, "delta": c - b,
                    "exposed": exposed is None or t in exposed})
    S = [p for p in per if p["exposed"]]
    G = sum(p["delta"] for p in S if p["delta"] > 0)
    N = sum(p["delta"] for p in S)
    D = max([-p["delta"] for p in S if p["delta"] < 0] or [0.0])
    protected_broken = [p["task"] for p in S if p["base"] == 1 and p["cand"] < 1]
    clis = {r.get("cli_version") for r in valid if r.get("cli_version")}
    invrate = (len(rs) - len(valid)) / len(rs) if rs else 0.0
    scorable = (sweep.get("outcome") == "done" and invrate <= MAXINV and not unmeasured
                and bool(measured) and unknown == 0 and len(clis) <= 1)
    netruns = round(N * k, 6)
    regressed = [p["task"] for p in S if (p["base"] - p["cand"]) > RTOL
                 or (p["base"] == 1 and p["cand"] < 1)]
    failed = []
    if G <= 0:
        failed.append("gate1")
    if D > RTOL:
        failed.append("gate2")
    if protected_broken:
        failed.append("gate3")
    if netruns < MINNET:
        failed.append("gate4")
    if fired == 0:
        failed.append("gate5")
    informative = [p for p in S if p["base"] < 1 and (p["base"] > 0 or p["cand"] > 0)]
    uninformative = bool(S) and not informative
    phase = sweep["phase"]
    if not scorable:
        verdict = "RERUN"
    elif uninformative:
        verdict = "RERUN"
    elif phase == "screen":
        verdict = "KILL" if (G <= 0 or fired == 0) else "CONFIRM"
    elif failed:
        only = all(g in ("gate2", "gate3") for g in failed) and bool(regressed)
        verdict = "RECHECK" if only and phase == "confirm" else "KILL"
    else:
        verdict = "KEEP"
    return {"sweep": sweep["sweep"], "phase": phase, "k": k, "tasks": len(tasks),
            "exposed": sorted(p["task"] for p in S), "per_task": per, "G": G, "N": N, "D": D,
            "regression": G - N, "net_runs": netruns, "fired": fired, "unknown": unknown,
            "scorable": scorable, "uninformative": uninformative, "failed": failed,
            "regressed": regressed, "verdict": verdict, "rollouts": len(rs),
            "cost_usd": sweep.get("cost_usd") or 0.0, "started": sweep.get("started")}


def recheck(conf, rec):
    """A recheck sweep paired with the confirm that asked for it (score.sh, lines 388-423)."""
    got = {p["task"]: p for p in rec["per_task"]}
    missing = [t for t in conf["regressed"] if t not in got]
    if not rec["scorable"] or missing:
        return "RERUN"
    again = [t for t in conf["regressed"] if got[t]["exposed"]
             and ((got[t]["base"] - got[t]["cand"]) > RTOL
                  or (got[t]["base"] == 1 and got[t]["cand"] < 1))]
    return "KILL" if again else "KEEP"


def candidates():
    """Every candidate R1–R4 swept, in order, with each sweep scored and a final verdict."""
    sweeps = {s["sweep"]: s for s in rows("sweeps.jsonl") if s.get("run") in EVAL}
    by_sweep = defaultdict(list)
    for r in rows("rollouts.jsonl"):
        if r.get("source") == "sweep" and r.get("sweep") in sweeps:
            by_sweep[r["sweep"]].append(r)
    fates = {(i["run"], i["name"]): i["fate"] for i in rows("items.jsonl") if i.get("run") in EVAL}
    out = defaultdict(lambda: {"sweeps": []})
    for name, s in sorted(sweeps.items(), key=lambda kv: kv[1]["started"]):
        c = out[(s["run"], s["candidate"])]
        c.update(run=s["run"], name=s["candidate"], tier=s.get("tier"), kind=s.get("kind"))
        c["sweeps"].append(score(s, by_sweep[name], s["k"], s["candidate"]))
    for key, c in out.items():
        phases = [x["phase"] for x in c["sweeps"]]
        if len(phases) != len(set(phases)):          # one sweep per phase, or pair by hand
            raise SystemExit(f"rescore.py: {key} has two sweeps of one phase: {phases}")
        ph = {x["phase"]: x for x in c["sweeps"]}
        final = ph["screen"]["verdict"] if "screen" in ph else None
        if "confirm" in ph:
            final = ph["confirm"]["verdict"]
            if final == "RECHECK" and "recheck" in ph:
                final = recheck(ph["confirm"], ph["recheck"])
        c["verdict"] = final                       # what the rules decide
        c["stage"] = "confirm" if "confirm" in ph else "screen"
        c["rechecked"] = "recheck" in ph
        c["recorded"] = fates.get(key)             # what the loop recorded: kept / buried
    return [out[k] for k in sorted(out, key=lambda k: out[k]["sweeps"][0]["started"])]


if __name__ == "__main__":
    cs = candidates()
    for c in cs:
        # a recheck is shown as its pairing with the confirm decides it, not scored alone
        s = " ".join(f"{x['phase']}:{c['verdict'] if x['phase'] == 'recheck' else x['verdict']}"
                     for x in c["sweeps"])
        flag = ""
        if (c["recorded"] == "kept") != (c["verdict"] == "KEEP"):
            flag = "   <-- recorded differs from the rules"
        elif c["recorded"] == "buried" and c["verdict"] == "RERUN":
            flag = "   <-- buried with no scored verdict"
        print(f"{c['run']} {c['name']:36s} {c['tier'] or '':7s} {s:44s} -> {c['verdict']:6s} "
              f"recorded {c['recorded']}{flag}")
    kept = sum(1 for c in cs if c["verdict"] == "KEEP")
    print(f"\n{len(cs)} candidates swept; the rules keep {kept}; the loop kept "
          f"{sum(1 for c in cs if c['recorded'] == 'kept')}")
