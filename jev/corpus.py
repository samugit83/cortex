#!/usr/bin/env python3
"""Build the (candidate, task) firing ground-truth corpus from Cortex sweep history."""
import json, glob, os, sys
from collections import defaultdict

RUNS = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/samuele/Progetti didattici/cortex-lab/.evolve/runs"

sweeps = []
for f in sorted(glob.glob(os.path.join(RUNS, "*.jsonl"))):
    hdr, rows, end = None, [], None
    for line in open(f):
        try: r = json.loads(line)
        except ValueError: continue
        if r.get("event") == "start": hdr = r
        elif r.get("event"): end = r
        elif r.get("v"): rows.append(r)
    if hdr: sweeps.append((os.path.basename(f), hdr, rows, end))

print(f"sweeps parsed: {len(sweeps)}")
print(f"{'sweep':30s} {'phase':8s} {'candidate':28s} {'kind':6s} {'tier':10s} {'rolls':>5s}")
for f, h, rows, e in sweeps:
    cand = h.get("candidate") or ("-".join(h.get("replaced") or []) or "?")
    print(f"{f[:30]:30s} {h.get('phase',''):8s} {cand[:28]:28s} "
          f"{(h.get('candidate_kind') or '-'):6s} {(h.get('candidate_tier') or '-'):10s} {len(rows):5d}")

# ---- the corpus: one row per (sweep, candidate, task), cand arm only ----
corpus = []
for f, h, rows, e in sweeps:
    cand = h.get("candidate")
    if not cand:            # a /prune --replace sweep has no additive candidate
        continue
    kind = h.get("candidate_kind"); tier = h.get("candidate_tier")
    per_task = defaultdict(lambda: {"runs": 0, "visible": 0, "fired": 0, "passed": 0})
    for r in rows:
        if r.get("v") != "cand" or r.get("valid") != 1:
            continue
        vis = r.get("visible"); fired = (r.get("skills") or []) + (r.get("rules") or [])
        if vis is None:     # unknown firing: never score it as "did not fire"
            continue
        d = per_task[r["t"]]
        d["runs"] += 1
        d["visible"] += 1 if cand in vis else 0
        d["fired"]   += 1 if cand in fired else 0
        d["passed"]  += r.get("pass", 0)
    for t, d in sorted(per_task.items()):
        corpus.append({"sweep": f, "phase": h.get("phase"), "candidate": cand,
                       "kind": kind, "tier": tier, "task": t, **d})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firing_corpus.jsonl")
with open(out, "w") as fh:
    for row in corpus: fh.write(json.dumps(row) + "\n")
print(f"\ncorpus rows (candidate x task): {len(corpus)}  ->  {out}")
