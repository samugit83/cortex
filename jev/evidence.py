#!/usr/bin/env python3
"""The evidence that justified the Jev integration (docs/JEV.md).

Reads a Cortex repo's recorded sweeps and graveyard and reproduces every number
in section 1 of the plan. No network, no model, no API key: this is the
BASELINE the real Jev must beat in J0 (jev/validate.py, not yet written).

    python3 jev/evidence.py [path/to/repo/.evolve]

The "relevance" judgement here is a keyword oracle written by hand. That is the
point: it shows the SIGNAL separates. Whether Jev can compute that signal is
what J0 tests.
"""
import json, os, sys, glob
from collections import defaultdict

# default: the development run's repository, cortex-lab, beside this checkout
EV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "cortex-lab", ".evolve")
RUNS, TASKS, GRAVE = (os.path.join(EV, d) for d in ("runs", "tasks", "graveyard"))

# subject -> keywords marking a task as being ABOUT that subject
SUBJECTS = {
    "time":      ("shop.clock", "date.today", "datetime.now", "clock.today"),
    "billing":   ("shop/billing", "cents", "scale(", "round(", "float("),
    "changelog": ("changelog",),
    "exporters": ("exporter", "plugins/", "golden"),
}
OF = {  # candidate -> its subject
    "use-billing-helpers": "billing", "clock-in-billing": "time",
    "shop-clock-usage": "time", "enforce-shop-clock": "time",
    "enforce-shop-clock-v2": "time", "changelog-rule-v2": "changelog",
    "changelog-updates": "changelog", "check-changelog-on-shop-edits": "changelog",
    "complete-exporter-setup": "exporters", "exporter-completeness-rule": "exporters",
}

def sweeps():
    for f in sorted(glob.glob(os.path.join(RUNS, "*.jsonl"))):
        hdr, rows = None, []
        for line in open(f):
            try: r = json.loads(line)
            except ValueError: continue
            if r.get("event") == "start": hdr = r
            elif r.get("v"): rows.append(r)
        if hdr: yield os.path.basename(f), hdr, rows

_blob = {}
def about(task, subject):
    if task not in _blob:
        b = ""
        for fn in ("notes.md", "prompt.txt", "fix.patch"):
            p = os.path.join(TASKS, task, fn)
            if os.path.isfile(p): b += open(p, errors="replace").read().lower()
        _blob[task] = b
    return any(k.lower() in _blob[task] for k in SUBJECTS[subject])

def fate(name):
    b = os.path.join(GRAVE, name, "BURIED.md")
    if not os.path.isfile(b): return "KEPT", ""
    w = "".join(open(b)); lw = w.lower()
    why = next((l[4:].strip() for l in w.splitlines() if l.startswith("why:")), "")
    g5 = any(k in lw for k in ("gate5", "never invoked", "never loaded", "did not trigger"))
    return ("BURIED-gate5" if g5 else "BURIED-regression"), why

def rule(t): print("-" * 96)
def head(n, t): print(f"\n{'='*96}\n{n}. {t}\n{'='*96}")

# ---- 1.1 where the money went ----------------------------------------------
head("1.1", "WHERE THE MONEY WENT")
spend = defaultdict(lambda: {"rolls": 0, "cost": 0.0, "sweeps": 0})
for f, h, rows in sweeps():
    n = h.get("candidate") or "-".join(h.get("replaced") or []) or "?"
    d = spend[n]; d["sweeps"] += 1; d["rolls"] += len(rows)
    d["cost"] += sum(r.get("cost_usd") or 0 for r in rows)
buckets = defaultdict(lambda: [0, 0.0])
print(f"{'candidate':30s} {'swp':>3s} {'rolls':>5s} {'cost':>7s}  outcome")
rule(0)
for n, d in sorted(spend.items(), key=lambda x: -x[1]["cost"]):
    f_, why = fate(n)
    buckets[f_][0] += d["rolls"]; buckets[f_][1] += d["cost"]
    print(f"{n[:30]:30s} {d['sweeps']:3d} {d['rolls']:5d} ${d['cost']:6.2f}  {f_}: {why[:40]}")
rule(0)
tot = sum(v[1] for v in buckets.values())
for k in ("KEPT", "BURIED-regression", "BURIED-gate5"):
    r_, c = buckets[k]
    print(f"  {k:20s} {r_:5d} rollouts  ${c:7.2f}  ({c/tot:5.1%})")

# ---- 1.3/1.4 the separation -------------------------------------------------
head("1.3", "INJECTION RELEVANCE vs FATE  (confirm/recheck sweeps only)")
print("Screens run only the theme's tasks, so relevance is 100% there by construction.")
print("Only confirms run the whole suite, so only they can show over-injection.\n")
per = defaultdict(lambda: {"ran": set(), "inj": set(), "rel": set()})
for f, h, rows in sweeps():
    n = h.get("candidate")
    if not n or n not in OF or h.get("phase") not in ("confirm", "recheck"): continue
    for r in rows:
        if r.get("v") != "cand" or r.get("valid") != 1 or r.get("visible") is None: continue
        d = per[n]; d["ran"].add(r["t"])
        if n in (r.get("skills") or []) + (r.get("rules") or []):
            d["inj"].add(r["t"])
            if about(r["t"], OF[n]): d["rel"].add(r["t"])
print(f"{'candidate':30s} {'suite':>5s} {'inj':>4s} {'rel':>4s} {'irrel':>5s} {'RELEVANCE':>9s} {'BREADTH':>8s}  fate")
rule(0)
R = {"KEPT": [], "BURIED-regression": []}; B = {"KEPT": [], "BURIED-regression": []}
for n, d in sorted(per.items(), key=lambda x: len(x[1]["rel"]) / max(len(x[1]["inj"]), 1)):
    s, i, rl = len(d["ran"]), len(d["inj"]), len(d["rel"])
    rel_, br = rl / max(i, 1), i / max(s, 1)
    f_, _ = fate(n)
    if f_ in R: R[f_].append(rel_); B[f_].append(br)
    print(f"{n[:30]:30s} {s:5d} {i:4d} {rl:4d} {i-rl:5d} {rel_:8.0%} {br:7.0%}  {f_}")
rule(0)
def verdict(label, kept, bad):
    if not kept or not bad: return
    lo, hi = min(kept), max(bad)
    ok = lo > hi
    print(f"\n{label}")
    print(f"  KEPT              : {[f'{x:.0%}' for x in sorted(kept)]}")
    print(f"  BURIED-regression : {[f'{x:.0%}' for x in sorted(bad)]}")
    print(f"  lowest KEPT {lo:.0%} vs highest BURIED {hi:.0%}  ->  "
          + ("SEPARATES CLEANLY" if ok else "OVERLAPS: cannot discriminate"))
verdict("RELEVANCE (semantic - needs a judge like Jev):", R["KEPT"], R["BURIED-regression"])
verdict("BREADTH (deterministic, free, glob-only - the alternative):", B["KEPT"], B["BURIED-regression"])

# ---- 1.5 firing priors ------------------------------------------------------
head("1.5", "IS FIRING PREDICTABLE, AND WHAT PREDICTS IT?")
cells = defaultdict(lambda: {"runs": 0, "vis": 0, "fire": 0, "tier": ""})
for f, h, rows in sweeps():
    n = h.get("candidate")
    if not n: continue
    for r in rows:
        if r.get("v") != "cand" or r.get("valid") != 1 or r.get("visible") is None: continue
        c = cells[(n, r["t"], f)]; c["tier"] = h.get("candidate_tier") or "?"
        c["runs"] += 1
        c["vis"] += n in r["visible"]
        c["fire"] += n in (r.get("skills") or []) + (r.get("rules") or [])
multi = [c for c in cells.values() if c["runs"] >= 2]
unan = [c for c in multi if c["fire"] in (0, c["runs"])]
print(f"(candidate,task) cells with >=2 repeat runs : {len(multi)}")
print(f"  unanimous (always fired / never fired)    : {len(unan)}  ({len(unan)/max(len(multi),1):.1%})")
print(f"  split                                     : {len(multi)-len(unan)}"
      f"  ({(len(multi)-len(unan))/max(len(multi),1):.1%})   <- firing is NOT noise\n")
print(f"{'tier':10s} {'runs':>5s} {'visible':>8s} {'fired':>7s} {'FIRED|VISIBLE':>14s}")
rule(0)
for tier in ("rule", "gated", "always"):
    sel = [c for c in cells.values() if c["tier"] == tier]
    if not sel: continue
    r_ = sum(c["runs"] for c in sel); v = sum(c["vis"] for c in sel); fr = sum(c["fire"] for c in sel)
    print(f"{tier:10s} {r_:5d} {v/max(r_,1):7.1%} {fr/max(r_,1):6.1%} "
          f"{('n/a' if not v else f'{fr/v:.1%}'):>14s}")
print("\nA rule that is visible ALWAYS fires. That is why an over-scoped rule is the")
print("most destructive object in the system - and why 1.3 is the check that matters.")
