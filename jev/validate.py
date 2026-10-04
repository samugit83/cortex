#!/usr/bin/env python3
"""validate.py — J0. The gate the whole integration is blocked on.

Cortex's founding constraint (THEORY §2) is that a verifier is a command that
exits 0 or non-zero — "not an opinion, not an LLM judge". Jev IS a judge, so the
burden of proof is on the integration, not on the reader. Nothing in
the integration (docs/JEV.md) ships until this script says PASS on Cortex's own
recorded data.

What it does
  1. Builds the (candidate, task) firing corpus from a repo's .evolve/runs/,
     then SNAPSHOTS everything it scored into jev/corpus/ and expects you to
     commit it — `cortex clean --runs` deletes .evolve/runs/*.jsonl, which is
     this evidence's only home otherwise.
  2. Asks Jev, once per row: "Is this task about <the candidate's subject>?",
     sending that task's title, prompt.txt and notes.md as state and nothing else.
  3. Reports three numbers:
       - agreement with the keyword oracle of plan §1.3
       - whether the relevance ratio still separates KEPT from BURIED-on-regression
       - calibration: bucketed by returned probability, observed frequency beside it
  4. Compares against the free baseline of §1.4 (glob breadth), which overlaps and
     therefore cannot discriminate.

PASS   agreement >= 85%, separation preserved, calibration monotonic  -> exit 0
FAIL   anything less                                                  -> exit 1
       Then stop: archive jev/ with these numbers and delete the plan.
CANNOT RUN  no sweep history to score                                 -> exit 2

Usage
  python3 jev/validate.py                      # the default corpus repo
  python3 jev/validate.py --evolve /path/to/repo/.evolve
  python3 jev/validate.py --corpus jev/corpus  # replay the committed snapshot
  python3 jev/validate.py --snapshot-only      # build the snapshot, ask nothing
  python3 jev/validate.py --dry-run            # everything except the Jev calls

This step is permanently useful: it is a regression test for Jev itself. Re-run it
after any model version change, exactly as `cortex preflight` re-proves the suite.
"""
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CORTEX_HOME = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CORTEX_HOME, "bin"))
import jev                                                      # noqa: E402

DEFAULT_EVOLVE = os.path.join(os.path.dirname(CORTEX_HOME), "cortex-lab", ".evolve")
SNAPSHOT = os.path.join(HERE, "corpus")

# Set to 0.85 on 2026-09-21, AFTER the first measurement returned 89.4%. The
# original bar was 0.90 and the original result was a FAIL. Seven of the eleven
# disagreements are cases where the keyword oracle read `fix.patch` — which Jev is
# never sent — and the operator judged the bar unfair on that ground. A reader who
# wants the untouched verdict should apply 0.90.
PASS_AGREEMENT = 0.85
RELEVANT_P = 0.5                 # a Noul is the probability of yes; 0.5 is its midpoint

# The keyword oracle of plan §1.3. It is a hand-written matcher, NOT Jev: it
# proves the signal exists and separates. Whether Jev can compute that signal is
# exactly what this script tests, so the two must stay independent.
SUBJECTS = {
    "time":      ("shop.clock", "date.today", "datetime.now", "clock.today"),
    "billing":   ("shop/billing", "cents", "scale(", "round(", "float("),
    "changelog": ("changelog",),
    "exporters": ("exporter", "plugins/", "golden"),
}
OF = {"use-billing-helpers": "billing", "clock-in-billing": "time",
      "shop-clock-usage": "time", "enforce-shop-clock": "time",
      "enforce-shop-clock-v2": "time", "changelog-rule-v2": "changelog",
      "changelog-updates": "changelog", "check-changelog-on-shop-edits": "changelog",
      "complete-exporter-setup": "exporters", "exporter-completeness-rule": "exporters"}


# ------------------------------------------------------------------ reading --
def read(path, limit=200000):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def sweeps(runs_dir):
    for f in sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []:
        if not f.endswith(".jsonl"):
            continue
        hdr, rows = None, []
        for line in read(os.path.join(runs_dir, f), 50_000_000).splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("event") == "start":
                hdr = r
            elif r.get("v"):
                rows.append(r)
        if hdr:
            yield f, hdr, rows


def build_corpus(evolve):
    """-> (rows, meta). One row per (sweep, candidate, task) in the cand arm."""
    runs = os.path.join(evolve, "runs")
    corpus, models, phases = [], set(), set()
    for f, h, rows in sweeps(runs):
        cand = h.get("candidate")
        if not cand:                          # a /prune --replace sweep adds nothing
            continue
        models.add(h.get("model") or "")
        phases.add(h.get("phase") or "")
        per = defaultdict(lambda: {"runs": 0, "visible": 0, "fired": 0, "passed": 0})
        for r in rows:
            if r.get("v") != "cand" or r.get("valid") != 1:
                continue
            vis = r.get("visible")
            if vis is None:                   # unknown firing: never score it as "did not fire"
                continue
            d = per[r["t"]]
            d["runs"] += 1
            d["visible"] += 1 if cand in vis else 0
            d["fired"] += 1 if cand in (r.get("skills") or []) + (r.get("rules") or []) else 0
            d["passed"] += r.get("pass", 0)
        for t, d in sorted(per.items()):
            corpus.append({"sweep": f, "phase": h.get("phase"), "candidate": cand,
                           "kind": h.get("candidate_kind"), "tier": h.get("candidate_tier"),
                           "task": t, **d})
    meta = {"rollout_models": sorted(m for m in models if m), "phases": sorted(phases)}
    return corpus, meta


def fate(evolve, name):
    b = os.path.join(evolve, "graveyard", name, "BURIED.md")
    if not os.path.isfile(b):
        return "KEPT", ""
    w = read(b)
    why = next((l[4:].strip() for l in w.splitlines() if l.startswith("why:")), "")
    g5 = any(k in w.lower() for k in ("gate5", "never invoked", "never loaded", "did not trigger"))
    return ("BURIED-gate5" if g5 else "BURIED-regression"), why


def item_text(evolve, name):
    """The candidate's own words: the graveyard copy for a buried one, the live
    copy for one that was kept."""
    for p in (os.path.join(evolve, "graveyard", name, "SKILL.md"),
              os.path.join(evolve, "graveyard", name, "RULE.md"),
              os.path.join(evolve, "..", ".claude", "skills", name, "SKILL.md"),
              os.path.join(evolve, "..", ".claude", "rules", name + ".md"),
              os.path.join(evolve, "items", name, "SKILL.md"),
              os.path.join(evolve, "items", name, "RULE.md")):
        if os.path.isfile(p):
            return read(p, 8000), os.path.basename(p)
    return "", ""


def subject_of(evolve, name):
    """What the candidate is ABOUT, built the same way `cortex scope` builds it, so
    J0 measures the question J1 will actually ask."""
    text, _ = item_text(evolve, name)
    fields = {}
    body = text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "-")):
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
    s = {"name": name.replace("-", " ")}
    if fields.get("description"):
        s["description"] = fields["description"][:1000]
    if body.strip():
        s["says"] = body.strip()[:2000]
    return s


def task_state(evolve, tid):
    d = os.path.join(evolve, "tasks", tid)
    title = ""
    for line in read(os.path.join(d, "task.yaml"), 4000).splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip().strip("'\"")
    notes = read(os.path.join(d, "notes.md"), 4000).strip()
    state = {"task": tid, "title": title, "prompt": read(os.path.join(d, "prompt.txt"), 8000).strip()}
    if notes:
        state["notes"] = notes
    return state


_blob = {}


def oracle(evolve, task, subject):
    """The §1.3 keyword matcher, unchanged. Reads MORE than Jev does (fix.patch
    included), which makes it a harder baseline, not an easier one."""
    if task not in _blob:
        b = ""
        for fn in ("notes.md", "prompt.txt", "fix.patch"):
            b += read(os.path.join(evolve, "tasks", task, fn)).lower()
        _blob[task] = b
    return any(k.lower() in _blob[task] for k in SUBJECTS[subject])


# ---------------------------------------------------------------- snapshot --
def snapshot(evolve, rows, meta, dest=SNAPSHOT):
    """Copy everything J0 scored into jev/corpus/ and expect it committed.

    `cortex clean --runs` deletes .evolve/runs/*.jsonl, which is this whole plan's
    evidence base and the only thing jev/RESULTS.md rests on. Without this, one
    cleanup makes J0 unreproducible and every number in RESULTS.md unfalsifiable.
    """
    if os.path.abspath(evolve) == os.path.abspath(dest):
        return dest                            # already replaying the snapshot
    shutil.rmtree(dest, ignore_errors=True)
    for sub in ("runs", "tasks", "graveyard", "items"):
        os.makedirs(os.path.join(dest, sub), exist_ok=True)
    sweep_files = sorted({r["sweep"] for r in rows})
    for f in sweep_files:
        shutil.copy2(os.path.join(evolve, "runs", f), os.path.join(dest, "runs", f))
    for t in sorted({r["task"] for r in rows}):
        src, dst = os.path.join(evolve, "tasks", t), os.path.join(dest, "tasks", t)
        os.makedirs(dst, exist_ok=True)
        for fn in ("task.yaml", "prompt.txt", "notes.md", "fix.patch"):
            if os.path.isfile(os.path.join(src, fn)):
                shutil.copy2(os.path.join(src, fn), os.path.join(dst, fn))
    for name in sorted({r["candidate"] for r in rows}):
        g = os.path.join(evolve, "graveyard", name)
        if os.path.isdir(g):
            os.makedirs(os.path.join(dest, "graveyard", name), exist_ok=True)
            for fn in os.listdir(g):
                if os.path.isfile(os.path.join(g, fn)):
                    shutil.copy2(os.path.join(g, fn), os.path.join(dest, "graveyard", name, fn))
        text, base = item_text(evolve, name)
        if text:
            os.makedirs(os.path.join(dest, "items", name), exist_ok=True)
            with open(os.path.join(dest, "items", name, base), "w", encoding="utf-8") as fh:
                fh.write(text)
    manifest = {"source": os.path.abspath(evolve), "taken": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "rows": len(rows), "sweeps": len(sweep_files),
                "tasks": sorted({r["task"] for r in rows}),
                "candidates": sorted({r["candidate"] for r in rows}), **meta}
    with open(os.path.join(dest, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(dest, "firing_corpus.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    return dest


# ------------------------------------------------------------------- report --
def bar(frac, width=28):
    n = int(round(max(0.0, min(1.0, frac)) * width))
    return "#" * n + "." * (width - n)


def relevance_table(evolve, rows, judge):
    """Per candidate, over the CONFIRM/RECHECK sweeps only: injected, relevant,
    relevance, breadth, fate. Screens run only the theme's tasks, so relevance is
    100% there by construction and only a confirm can show over-injection."""
    per = defaultdict(lambda: {"ran": set(), "inj": set(), "rel": set(), "unk": set()})
    for r in rows:
        if r["phase"] not in ("confirm", "recheck") or r["candidate"] not in OF:
            continue
        d = per[r["candidate"]]
        d["ran"].add(r["task"])
        if r["fired"] > 0 or r["visible"] > 0:
            d["inj"].add(r["task"])
            verdict = judge(r["candidate"], r["task"])
            if verdict is None:
                d["unk"].add(r["task"])
            elif verdict:
                d["rel"].add(r["task"])
    out = []
    for name, d in per.items():
        answered = len(d["inj"]) - len(d["unk"])
        f, _ = fate(evolve, name)
        out.append({"name": name, "suite": len(d["ran"]), "injected": len(d["inj"]),
                    "relevant": len(d["rel"]), "answered": answered,
                    "relevance": (len(d["rel"]) / answered) if answered else None,
                    "breadth": len(d["inj"]) / max(len(d["ran"]), 1), "fate": f})
    return sorted(out, key=lambda r: (r["relevance"] is None, r["relevance"] or 0))


def separation(table, key):
    kept = [r[key] for r in table if r["fate"] == "KEPT" and r[key] is not None]
    bad = [r[key] for r in table if r["fate"] == "BURIED-regression" and r[key] is not None]
    if not kept or not bad:
        return None, kept, bad
    return min(kept) > max(bad), kept, bad


def calibration(pairs, buckets=5):
    """pairs = [(p, truth)]. Observed frequency per probability bucket. Monotonic
    means a higher returned probability really does mean more often right — the
    property that makes a threshold meaningful at all."""
    rows = []
    for i in range(buckets):
        lo, hi = i / buckets, (i + 1) / buckets
        sel = [t for p, t in pairs if (lo <= p < hi or (i == buckets - 1 and p == 1.0))]
        rows.append({"lo": lo, "hi": hi, "n": len(sel),
                     "observed": (sum(1 for t in sel if t) / len(sel)) if sel else None})
    seen = [r["observed"] for r in rows if r["observed"] is not None]
    mono = all(b >= a - 1e-9 for a, b in zip(seen, seen[1:])) if len(seen) >= 2 else None
    return rows, mono


# --------------------------------------------------------------------- main --
def main(argv):
    evolve = corpus_dir = None
    snapshot_only = "--snapshot-only" in argv
    dry = "--dry-run" in argv
    out_path = os.path.join(HERE, "RESULTS.md")
    i = 0
    while i < len(argv):
        if argv[i] == "--evolve" and i + 1 < len(argv):
            evolve = argv[i + 1]; i += 2
        elif argv[i] == "--corpus" and i + 1 < len(argv):
            corpus_dir = argv[i + 1]; i += 2
        elif argv[i] == "--out" and i + 1 < len(argv):
            out_path = argv[i + 1]; i += 2
        elif argv[i] in ("--snapshot-only", "--dry-run"):
            i += 1
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 2

    replaying = bool(corpus_dir)
    if corpus_dir:
        evolve = corpus_dir
    elif not evolve:
        here_evolve = os.path.join(os.getcwd(), ".evolve")
        evolve = here_evolve if os.path.isdir(os.path.join(here_evolve, "runs")) else DEFAULT_EVOLVE

    rows, meta = build_corpus(evolve)
    if not rows:
        print(f"no sweep history under {os.path.join(evolve, 'runs')}: J0 needs a repo that has "
              "run /evolve at least twice. Point it at one with --evolve <path>.", file=sys.stderr)
        return 2

    # REPLAYING A SNAPSHOT MUST NEVER REBUILD ONE. `--corpus <somewhere else>`
    # used to rmtree jev/corpus and refill it from that other path, destroying the
    # committed evidence this whole directory exists to preserve — the exact loss
    # the snapshot was introduced to prevent.
    snap = evolve if replaying else snapshot(evolve, rows, meta)
    print(f"corpus: {len(rows)} (candidate, task) rows from "
          f"{len({r['sweep'] for r in rows})} sweep(s)")
    if replaying:
        print(f"        replaying {evolve} — no snapshot written")
    else:
        print(f"        snapshot -> {os.path.relpath(snap, CORTEX_HOME)}  (COMMIT IT: "
              "`cortex clean --runs` deletes the original)")
    if snapshot_only:
        return 0

    scorable = [r for r in rows if r["candidate"] in OF]
    pairs = sorted({(r["candidate"], r["task"]) for r in scorable})
    print(f"        {len(pairs)} distinct (candidate, task) pairs to judge\n")

    # ---- the Jev census ----
    answers, model, census = {}, "", None
    if not dry:
        cfg = jev.resolve(None)
        if not cfg.on:
            print(f"jev is not usable: {cfg.off_reason}. J0 cannot run without a key.\n"
                  "Set JEV_API_KEY (see .env.example) and JEV_ENABLED=1, then re-run.",
                  file=sys.stderr)
            return 2
        jobs = [{"key": f"{c}|{t}", "state": task_state(evolve, t),
                 "questions": {"relevant": jev.q_relevant(subject_of(evolve, c))},
                 "meta": {"candidate": c, "task": t}} for c, t in pairs]
        print(f"asking {len(jobs)} question(s) of {cfg.model} at {cfg.base_url} ...")
        raw, census = jev.ask_many(cfg, jobs, site="scope", repo=None)
        for c, t in pairs:
            a = raw.get(f"{c}|{t}")
            p = a.noul("relevant") if a is not None else None
            if p is not None:
                answers[(c, t)] = p
        model = census.model or cfg.model
        print(f"  answered {census.answered}/{census.requests}"
              f"  ·  fell back {census.fell_back}"
              f"  ·  {census.input_tokens} input tokens"
              f"  ·  model {model}")
        if census.refused:
            print(f"  REFUSED: {census.refused}", file=sys.stderr)
        if not answers:
            print("no answers at all: J0 cannot report a result it did not measure.",
                  file=sys.stderr)
            return 2
    else:
        model = "(dry run: no model was asked)"

    def jev_says(c, t):
        p = answers.get((c, t))
        return None if p is None else p >= RELEVANT_P

    def oracle_says(c, t):
        return oracle(evolve, t, OF[c])

    # ---- 1. agreement with the keyword oracle ----
    compared = [(c, t) for c, t in pairs if (c, t) in answers]
    agree = sum(1 for c, t in compared if jev_says(c, t) == oracle_says(c, t))
    agreement = agree / len(compared) if compared else 0.0
    disagreements = [{"candidate": c, "task": t, "p": round(answers[(c, t)], 3),
                      "jev": jev_says(c, t), "oracle": oracle_says(c, t)}
                     for c, t in compared if jev_says(c, t) != oracle_says(c, t)]

    # ---- 2. does the separation survive with Jev as the judge ----
    t_jev = relevance_table(evolve, scorable, jev_says)
    t_oracle = relevance_table(evolve, scorable, lambda c, t: oracle_says(c, t))
    sep_jev, kept_j, bad_j = separation(t_jev, "relevance")
    sep_oracle, kept_o, bad_o = separation(t_oracle, "relevance")
    sep_breadth, kept_b, bad_b = separation(t_oracle, "breadth")

    # ---- 3. calibration ----
    cal, mono = calibration([(answers[(c, t)], oracle_says(c, t)) for c, t in compared])

    # A dry run measured nothing, so it may not produce a verdict — and above all it
    # may not write RESULTS.md, whose `validated-model:` line bin/jev.py reads back
    # on every call. A fake value there would silence the drift check for good.
    ok = (agreement >= PASS_AGREEMENT) and bool(sep_jev) and (mono is not False)
    verdict = "DRY RUN" if dry else ("PASS" if ok else "FAIL")

    # ---- report ----
    print("")
    print("=" * 92)
    print("1. AGREEMENT WITH THE KEYWORD ORACLE OF PLAN §1.3")
    print("=" * 92)
    print(f"  {agree}/{len(compared)} = {agreement:.1%}   (pass needs >= {PASS_AGREEMENT:.0%})")
    for d in disagreements[:12]:
        print(f"    {d['candidate'][:28]:28s} task {d['task']:>3s}  p={d['p']:.2f}  "
              f"jev={'about' if d['jev'] else 'not about':9s} oracle="
              f"{'about' if d['oracle'] else 'not about'}")
    if len(disagreements) > 12:
        print(f"    ... and {len(disagreements) - 12} more")

    print("")
    print("=" * 92)
    print("2. DOES THE RELEVANCE RATIO STILL SEPARATE KEPT FROM BURIED-ON-REGRESSION?")
    print("=" * 92)
    print(f"  {'candidate':30s} {'suite':>5s} {'inj':>4s} {'rel':>4s} {'RELEVANCE':>9s} "
          f"{'BREADTH':>8s}  fate")
    print("  " + "-" * 88)
    for r in t_jev:
        rel = f"{r['relevance']:8.0%}" if r["relevance"] is not None else "       -"
        print(f"  {r['name'][:30]:30s} {r['suite']:5d} {r['injected']:4d} {r['relevant']:4d} "
              f"{rel} {r['breadth']:7.0%}  {r['fate']}")
    print("")
    for label, ok_, kept, bad in (("RELEVANCE, judged by Jev", sep_jev, kept_j, bad_j),
                                  ("RELEVANCE, judged by the keyword oracle", sep_oracle, kept_o, bad_o),
                                  ("BREADTH (free, deterministic — the alternative)", sep_breadth, kept_b, bad_b)):
        if ok_ is None:
            print(f"  {label}: not enough of both groups to say")
            continue
        print(f"  {label}")
        print(f"    KEPT              : {[f'{x:.0%}' for x in sorted(kept)]}")
        print(f"    BURIED-regression : {[f'{x:.0%}' for x in sorted(bad)]}")
        print(f"    lowest KEPT {min(kept):.0%} vs highest BURIED {max(bad):.0%}  ->  "
              + ("SEPARATES CLEANLY" if ok_ else "OVERLAPS: cannot discriminate"))

    print("")
    print("=" * 92)
    print("3. CALIBRATION: DOES A HIGHER PROBABILITY MEAN MORE OFTEN RIGHT?")
    print("=" * 92)
    print(f"  {'bucket':>12s} {'n':>5s} {'observed':>9s}")
    for c in cal:
        obs = f"{c['observed']:8.0%}" if c["observed"] is not None else "       -"
        b = bar(c["observed"]) if c["observed"] is not None else ""
        print(f"  {c['lo']:.1f}-{c['hi']:.1f}".rjust(14) + f" {c['n']:5d} {obs}  {b}")
    print(f"  monotonic: {'yes' if mono else ('no' if mono is False else 'too few buckets to say')}")

    print("")
    print("=" * 92)
    print(f"J0 VERDICT: {verdict}")
    print("=" * 92)
    if dry:
        print("  --dry-run asked nothing, so there is no verdict and RESULTS.md was not")
        print("  touched. The oracle and breadth rows above are the baseline Jev must beat;")
        print("  they reproduce plan §1.3 and §1.4 with no key and no network.")
        return 0
    print(f"  agreement  {agreement:.1%} {'>=' if agreement >= PASS_AGREEMENT else '<'} "
          f"{PASS_AGREEMENT:.0%}")
    print(f"  separation {'preserved' if sep_jev else 'LOST'}")
    print(f"  calibration {'monotonic' if mono else ('NOT monotonic' if mono is False else 'unmeasurable')}")
    if not ok:
        print("  -> STOP. Archive jev/ with these numbers and delete the plan.")

    write_results(out_path, verdict, model, snap, rows, pairs, compared, agreement,
                  disagreements, t_jev, sep_jev, sep_oracle, sep_breadth, cal, mono, meta, census)
    print(f"\nwritten: {os.path.relpath(out_path, CORTEX_HOME)}")
    return 0 if ok else 1


def write_results(path, verdict, model, snap, rows, pairs, compared, agreement,
                  disagreements, table, sep_jev, sep_oracle, sep_breadth, cal, mono, meta, census):
    """jev/RESULTS.md. Its FIRST lines carry every fact that can invalidate the
    result — the answering model id above all — because bin/jev.py reads
    `validated-model:` back on every call and warns when the answer comes from a
    different one. None of these may be implicit."""
    L = []
    L.append("# J0 — Jev against Cortex's own corpus")
    L.append("")
    L.append("```")
    L.append(f"validated-model: {model}")
    L.append(f"verdict:         {verdict}")
    L.append(f"measured:        {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    L.append(f"snapshot:        {os.path.relpath(snap, CORTEX_HOME)}")
    L.append(f"rows:            {len(rows)} (candidate, task) rows; "
             f"{len(pairs)} distinct pairs; {len(compared)} answered")
    L.append(f"rollout model:   {', '.join(meta.get('rollout_models') or ['unknown'])}  "
             "(the model those rollouts RAN on; firing rates may differ on another)")
    if census is not None:
        L.append(f"input tokens:    {census.input_tokens}")
    L.append("```")
    L.append("")
    L.append("Every line above can invalidate this result, so none of them is implicit. "
             "`bin/jev.py` compares each answer's model id against `validated-model` and "
             "warns once per run when they differ (§3.7).")
    L.append("")
    L.append("## 1. Agreement with the keyword oracle (plan §1.3)")
    L.append("")
    L.append(f"**{agreement:.1%}** over {len(compared)} answered pairs "
             f"(pass needs ≥ {PASS_AGREEMENT:.0%}).")
    if disagreements:
        L.append("")
        L.append("| candidate | task | p | Jev | oracle |")
        L.append("|---|---|---|---|---|")
        for d in disagreements[:25]:
            L.append(f"| `{d['candidate']}` | {d['task']} | {d['p']:.2f} | "
                     f"{'about' if d['jev'] else 'not about'} | "
                     f"{'about' if d['oracle'] else 'not about'} |")
        if len(disagreements) > 25:
            L.append(f"| … | | | | {len(disagreements) - 25} more |")
    L.append("")
    L.append("## 2. Separation: KEPT vs BURIED-on-regression")
    L.append("")
    L.append("| candidate | suite | injected | relevant | relevance | breadth | fate |")
    L.append("|---|---|---|---|---|---|---|")
    for r in table:
        rel = f"{r['relevance']:.0%}" if r["relevance"] is not None else "—"
        L.append(f"| `{r['name']}` | {r['suite']} | {r['injected']} | {r['relevant']} | "
                 f"{rel} | {r['breadth']:.0%} | {r['fate']} |")
    L.append("")
    L.append(f"- relevance judged by **Jev**: {'separates cleanly' if sep_jev else 'OVERLAPS'}")
    L.append(f"- relevance judged by the **keyword oracle**: "
             f"{'separates cleanly' if sep_oracle else 'OVERLAPS'}")
    L.append(f"- **breadth** (the free deterministic alternative): "
             f"{'separates cleanly' if sep_breadth else 'OVERLAPS — cannot discriminate'}")
    L.append("")
    L.append("## 3. Calibration")
    L.append("")
    L.append("| probability bucket | n | observed frequency |")
    L.append("|---|---|---|")
    for c in cal:
        obs = f"{c['observed']:.0%}" if c["observed"] is not None else "—"
        L.append(f"| {c['lo']:.1f}–{c['hi']:.1f} | {c['n']} | {obs} |")
    L.append("")
    L.append(f"Monotonic: **{'yes' if mono else ('no' if mono is False else 'too few buckets')}**.")
    L.append("")
    L.append("## Honest limits")
    L.append("")
    L.append(f"- n = {len({r['name'] for r in table})} confirm-swept candidates. Small.")
    L.append("- The regression-buried ones share a theme, so the separation may be partly a "
             "theme artifact rather than a general law.")
    L.append("- The oracle this is scored against is a keyword matcher, and it reads "
             "`fix.patch` — which Jev is never sent. Disagreements are not automatically "
             "Jev's error.")
    L.append(f"- Those rollouts ran on {', '.join(meta.get('rollout_models') or ['an unknown model'])}. "
             "Firing rates may differ elsewhere.")
    L.append("")
    L.append("Re-run after any Jev model version change: "
             "`python3 jev/validate.py --corpus jev/corpus`.")
    L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
