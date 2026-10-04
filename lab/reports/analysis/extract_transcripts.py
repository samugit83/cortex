#!/usr/bin/env python3
"""extract_transcripts.py — what each rollout read that its harness did not give it.

  python3 lab/reports/analysis/extract_transcripts.py   -> lab/reports/data/transcripts.jsonl

Cortex deletes the event stream it reads once exposure is known, but Claude Code keeps
its own record of every headless session, in ~/.claude/projects (or $CLAUDE_PROJECTS),
one folder per working directory, so one per sandbox worker of every run. This script
reads those records for the programme's rollouts, matches each to the row the lab
recorded for it (same run, same worker, the same cost to the millionth of a dollar), and
writes one row per matched rollout with what it read, as flags. No command, output or
path is copied.

  fix     a successful git command printed a commit that is not an ancestor of the
          rollout's starting commit: a later commit of the run, such as the one that
          fixed the task in its session (shopkit, harvested tasks only)
  store   a git command printed the task store, a harvested fix.patch or the lessons,
          which the sparse checkout keeps off disk (shopkit)
  names   git listed a harness item that the rollout's arm does not have: in the
          benchmark, an item of the run's harness that the arm replaced; in a prune
          sweep's removal arm, the removed item (a `git status` of the tracked file)
  text    git printed the text of such an item (the tracked file's diff, or
          `git show <commit>:.claude/...`)
  impl    structlog: git printed the upstream implementation that the task removed

The session records live outside the repository, and Claude Code prunes old ones after
its retention period; without them (or the raw runs) the committed extract is kept as
it is. Standard library and git only; writes only lab/reports/data/transcripts.jsonl
and transcripts-coverage.json (recorded rollouts, and how many a record was matched to).
"""
import functools
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[1]
CORTEX = REPORTS.parents[1]
RAW = Path(os.environ.get("CORTEX_EVAL_RUNS", CORTEX.parent / "cortex-eval" / "runs"))
PROJECTS = Path(os.environ.get("CLAUDE_PROJECTS", Path.home() / ".claude" / "projects"))
DATA = REPORTS / "data"
OUT = DATA / "transcripts.jsonl"
COVER = DATA / "transcripts-coverage.json"

# a tool result that is a refusal, not output: the headless CLI asks, and nobody answers
REFUSED = ("requires approval", "was blocked", "Contains backslash", "<tool_use_error>")
LESSON = re.compile(r"\d{4}-\d{2}-\d{2} \| task \d+ \||^# Lessons", re.M)
GIT_READ = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(?:show|diff|checkout|restore|cat-file|grep|log\b[^|;&]*(?:-p\b|--patch))")
REF = re.compile(r"(?<![\w/.-])([0-9a-f]{7,40}|main|master|src/[\w/.-]+)(?![\w-])")
ITEM = r"\.claude/(?:rules/([\w.-]+?)\.md|skills/([\w.-]+)/)"
CD = re.compile(r'cd\s+"[^"]*"\s*&&\s*|cd\s+\S+\s*&&\s*')


def sessions(folder):
    """Each session in a Claude Code project folder: when it started, its first prompt,
    its cost, and its tool calls with their output (refusals left out)."""
    for f in sorted(folder.glob("*.jsonl")):
        calls, pend, cost, start, prompt = [], {}, None, None, None
        for line in f.read_text(errors="replace").splitlines():
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if "totalCostUSD" in j:
                cost = j["totalCostUSD"]
            start = start or j.get("timestamp")
            content = (j.get("message") or {}).get("content")
            if prompt is None and j.get("type") == "user":
                prompt = content if isinstance(content, str) else " ".join(
                    x.get("text", "") for x in (content or []) if isinstance(x, dict))
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    pend[b["id"]] = (b.get("name"), inp.get("command") or json.dumps(inp))
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in pend:
                    out = b.get("content")
                    if isinstance(out, list):
                        out = " ".join(x.get("text", "") for x in out if isinstance(x, dict))
                    out = str(out or "")
                    name, cmd = pend.pop(b["tool_use_id"])
                    if not b.get("is_error") and not any(x in out[:400] for x in REFUSED):
                        calls.append((name, CD.sub("", cmd or ""), out))
        yield {"cost": cost, "start": start, "prompt": prompt or "", "calls": calls}


@functools.lru_cache(maxsize=None)
def ancestor(repo, sha, base):
    r = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, base],
                       capture_output=True)
    return {0: True, 1: False}.get(r.returncode)


def items_in(text):
    return {a or b for a, b in re.findall(ITEM, text)}


def shopkit_reads(calls, repo, base, split, foreign):
    """The flags of one shopkit rollout. `foreign`: the harness items this arm lacks (whose
    names git could list) and the items whose text it lacks (missing or rewritten), or
    None where no such comparison applies."""
    f = {"fix": False, "store": False}
    if foreign is not None:
        f.update(names=False, text=False)
        foreign_names, foreign_text = foreign
        foreign = foreign_names | foreign_text
    for name, cmd, out in calls:
        if name != "Bash" or not re.search(r"\bgit\b", cmd) or not out.strip() or "fatal:" in out[:200]:
            continue
        reads = GIT_READ.search(cmd)
        if reads and (LESSON.search(out) or (".evolve" in cmd and "diff --git" in out)):
            f["store"] = True
        if reads and split != "holdout":
            for ref in REF.findall(cmd):
                if ref in ("main", "master") or ref.startswith("src/") or ancestor(repo, ref, base) is False:
                    f["fix"] = True
                    break
        if foreign:
            if items_in(out) & foreign_names:
                f["names"] = True
            shown = {a or b for a, b in re.findall(r"diff --git a/" + ITEM, out)}
            if reads and re.search(r"git\s+show\s+\S+:\.claude/", cmd):
                shown |= items_in(cmd)
            if shown & foreign_text:
                f["text"] = True
    return f


def structlog_reads(calls, training):
    """Did git print the upstream implementation's code, and was that before the rollout's
    first edit of it? In the benchmark HEAD is the upstream commit itself, with the
    implementation reverted in the index and the working tree; in training the upstream
    commits are ancestors of HEAD. A file list (`--stat`) is not code, and is not counted."""
    first_edit = next((i for i, (name, cmd, _o) in enumerate(calls)
                       if name in ("Edit", "Write", "MultiEdit") and "src/structlog" in cmd), len(calls))
    for i, (name, cmd, out) in enumerate(calls):
        if name != "Bash" or not out.strip() or "fatal" in out[:100]:
            continue
        if training:
            hit = re.search(r"git\s+(show\s+[0-9a-f]{7,40}|log\s+[^|;&]*(-p\b|--patch|-S|-G))", cmd)
        else:
            hit = re.search(r"git\s+(show\s+(HEAD|[0-9a-f]{7,40})\b|diff\s+[^|;&]*(HEAD|--cached|--staged|[0-9a-f]{7,40})"
                            r"|log\s+[^|;&]*(-p\b|--patch|-S|-G))", cmd)
        if hit and re.search(r"\bdef |\bclass |diff --git|^@@", out, re.M):
            return ["impl"] + (["impl_first"] if i < first_edit else [])
    return []


def recorded_rows():
    """The rows the lab recorded, keyed by run, source and worker."""
    rows = defaultdict(list)
    for run in ("R1", "R2", "R3", "R4", "C1", "D0R", "M1"):
        f = RAW / run / "bench" / "results.jsonl"
        if not f.exists():
            continue
        meta = json.loads((RAW / run / "bench" / "tasks.json").read_text())
        arms = json.loads((RAW / run / "bench" / "arms.json").read_text())
        base = {t["id"]: t["base"] for t in meta["tasks"]}
        # the run's harness is tracked in every clone (the control run has none); an arm
        # without one of its items can meet it in git, and so can an arm that rewrote one:
        # desc-only replaces each skill's body, and a diff shows the body it replaced
        # (flat only drops `paths`, and keeps every word)
        ev = arms.get("evolved") or {"skills": [], "rules": []}
        tracked = set(ev["skills"]) | set(ev["rules"])
        for line in f.read_text().splitlines():
            r = json.loads(line)
            own = set(arms[r["arm"]]["skills"]) | set(arms[r["arm"]]["rules"])
            rewritten = set(arms[r["arm"]]["skills"]) if r["arm"] == "desc-only" else set()
            rows[(run, "bench", r.get("w"))].append({
                "run": run, "source": "bench", "arm": r["arm"], "split": r["split"], "task": r["task"],
                "family": r.get("family"), "pass": r["pass"], "valid": r.get("valid", 1),
                "cost": r.get("cost_usd") or 0, "base": base[r["task"]],
                "foreign": (tracked - own, (tracked - own) | rewritten)})
    prune = {(r["run"], r["sweep"]) for r in
             (json.loads(l) for l in (DATA / "prune-sweeps.jsonl").read_text().splitlines() if l.strip())}
    for run in ("R1", "R2", "R3", "R4", "GATE", "PRUNE", "M1"):
        repo = RAW / run / f"cortex-lab-{run}"
        bases = {}
        for y in (repo / ".evolve" / "tasks").glob("*/task.yaml"):
            m = re.search(r"base_sha:\s*(\w+)", y.read_text())
            bases[y.parent.name] = m and m.group(1)
        files = sorted((repo / ".evolve" / "runs").glob("*.jsonl")) + \
            sorted((repo / ".evolve" / "runs-interrupted").glob("*.jsonl"))
        for f in files:
            recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            head = next((r for r in recs if r.get("event") == "start"), {})
            mode = head.get("mode", "add")
            finished = any(r.get("event") == "done" for r in recs)
            # a sweep counts as recorded when it finished and belongs to the experiment: the
            # prune passes' own sweeps (a copied repository's loop history is not part of the
            # test), and the loop's and the gate test's additions. A sweep cut short (a reboot,
            # an outage) is matched too, so that its rollouts are accounted for, but kept apart
            if run in ("PRUNE", "M1"):
                if (run, f.name) not in prune and (mode != "replace" or finished):
                    continue
            elif mode != "add":
                continue
            cut = not finished or (run in ("PRUNE", "M1") and (run, f.name) not in prune)
            removed = set(head.get("replaced") or [])
            for r in recs:
                if r.get("event") is not None or "v" not in r:
                    continue
                rows[(run, "sweep", r.get("w"))].append({
                    "run": run, "source": "sweep", "sweep": f.name, "phase": head.get("phase"),
                    "mode": mode, "removed": sorted(removed), "arm": r["v"], "split": "train",
                    "task": r["t"], "pass": r["pass"], "valid": r.get("valid", 1),
                    "cost": r.get("cost_usd") or 0, "base": bases.get(r["t"]), "cut": cut,
                    # a removal arm lacks exactly the removed item; an addition's arms are compared
                    # on the candidate, which the base arm's sandbox never holds
                    "foreign": (removed, removed) if (mode == "replace" and r["v"] == "cand") else None})
    return rows


def deleted_sweeps(folders, prefix):
    """Sweep records that an agent deleted: a successful `rm` of .evolve/runs/<file>.jsonl in
    the lab's own sessions (the /evolve and /prune turns). Returns (run, file, from, until)
    in UTC: the sweep's rollouts ran between the file's own time stamp and the deletion."""
    out = []
    for folder in folders:
        m = re.match(re.escape(prefix) + r"([A-Z0-9]+)-cortex-lab-", folder.name)
        if not m:
            continue
        for f in sorted(folder.glob("*.jsonl")):
            pend = {}
            for line in f.read_text(errors="replace").splitlines():
                try:
                    j = json.loads(line)
                except ValueError:
                    continue
                content = (j.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use" and b.get("name") == "Bash":
                        pend[b["id"]] = (j.get("timestamp"), (b.get("input") or {}).get("command") or "")
                    elif b.get("type") == "tool_result" and b.get("tool_use_id") in pend:
                        ts, cmd = pend.pop(b["tool_use_id"])
                        if b.get("is_error"):
                            continue
                        for name in re.findall(r"\brm\s+(?:-\w+\s+)*\S*\.evolve/runs/(\d{8}T\d{6}-\w+\.jsonl)", cmd):
                            began = datetime.strptime(name[:15], "%Y%m%dT%H%M%S").isoformat()
                            out.append((m.group(1), name, utc(began), ts[:19]))
    return out


def utc(local_iso):
    """A naive local time from the lab's files, as the UTC stamp Claude Code writes."""
    return datetime.fromisoformat(local_iso).astimezone().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def main():
    if not RAW.is_dir() or not PROJECTS.is_dir():
        print(f"extract_transcripts.py: no raw runs at {RAW} or no session records at {PROJECTS}; keeping {OUT}")
        return
    prefix = re.sub(r"[^A-Za-z0-9]", "-", str(RAW)) + "-"
    folders = sorted(p for p in PROJECTS.iterdir() if p.name.startswith(prefix))
    rows = recorded_rows()
    deleted = deleted_sweeps(folders, prefix)
    out, unmatched, cut_short, lost = [], Counter(), Counter(), defaultdict(list)

    # ---- shopkit: the loop's sweeps, the gate and prune tests, every benchmark ---------
    for folder in folders:
        run, rest = re.match(re.escape(prefix) + r"([A-Z0-9]+)-(.*)$", folder.name).groups()
        if run == "X1" or not rest.startswith("sandbox"):
            continue                           # structlog below; the lab's own sessions are not rollouts
        w = re.search(r"work-(\d+)$", rest)
        # a benchmark worker is sandbox/bench/work-N, or sandbox/work-N for the two runs that
        # only benchmark; a sweep worker is sandbox/<repository hash>/work-N
        source = "bench" if (rest.startswith("sandbox-bench-") or re.fullmatch(r"sandbox-work-\d+", rest)) else "sweep"
        pool = rows.get((run, source, int(w.group(1)) if w else None), [])
        for s in sessions(folder):
            hit = [r for r in pool if abs(r["cost"] - (s["cost"] or 0)) < 2e-6]
            if len({(r["task"], r["arm"], r.get("sweep")) for r in hit}) != 1:
                gone = [x for x in deleted if x[0] == run and source == "sweep"
                        and x[2] <= (s["start"] or "")[:19] <= x[3]]
                if not hit and len(gone) == 1:
                    lost[gone[0][1]].append(s["cost"] or 0)
                else:
                    unmatched[f"{run} {source}"] += 1
                continue
            r = hit[0]
            if r.get("cut"):
                cut_short[f"{run} {source}"] += 1
                continue
            flags = shopkit_reads(s["calls"], RAW / run / f"cortex-lab-{run}", r["base"], r["split"],
                                  r["foreign"])
            out.append({k: v for k, v in r.items() if k not in ("cost", "base", "foreign", "cut")}
                       | {"reads": flags})

    # ---- structlog: its benchmark, and the training sessions of the restarted run -----
    x1 = RAW / "X1"
    split = json.loads((x1 / "split.json").read_text())
    xrows = [json.loads(l) for l in (x1 / "bench.jsonl").read_text().splitlines() if l.strip()]
    training = []
    for folder in folders:
        m = re.match(re.escape(prefix) + r"X1-(.*)$", folder.name)
        if not m:
            continue
        for s in sessions(folder):
            if m.group(1) == "structlog":
                # a session opens with its task's request; /harvest and /evolve open with a
                # command; the first attempt, before the restart, was discarded
                if s["prompt"].lstrip().startswith("<command") or (s["start"] or "") < utc(split["at"]):
                    continue
                training.append({"run": "X1", "source": "session", "split": "train", "start": s["start"],
                                 "reads": {f: True for f in structlog_reads(s["calls"], True)}})
            else:
                hit = [r for r in xrows if abs((r.get("cost_usd") or 0) - (s["cost"] or 0)) < 2e-6]
                if len(hit) != 1:
                    unmatched["X1 bench"] += 1
                    continue
                r = hit[0]
                out.append({"run": "X1", "source": "bench", "arm": r["arm"], "split": r["split"],
                            "task": r["task"], "pass": r["pass"], "valid": r.get("valid", 1),
                            "reads": {f: True for f in structlog_reads(s["calls"], False)}})
    if len(training) != len(split["train"]):
        raise SystemExit(f"extract_transcripts.py: {len(training)} structlog training sessions after the "
                         f"restart, expected {len(split['train'])}")
    # whether each session passed at its first attempt, from the run's own state (one verdict,
    # ok, and no correction), so that the text need not read the raw run directory
    state = json.loads((x1 / "state.json").read_text())
    for t, sid in zip(sorted(training, key=lambda t: t["start"]), split["train"]):
        t.pop("start")
        st = state.get(sid) or {}
        out.append(t | {"task": sid, "right_first_time": int(st.get("verdicts") == ["ok"]
                                                              and not st.get("corrections"))})

    # how much of the record the transcripts cover: recorded rollouts, and those matched
    cover = defaultdict(lambda: {"recorded": 0, "matched": 0})
    for (run, source, _w), rs in rows.items():
        cover[f"{run} {source}"]["recorded"] += sum(1 for r in rs if not r.get("cut"))
    cover["X1 bench"]["recorded"] = len(xrows)
    for o in out:
        if o["source"] != "session":
            cover[f"{o['run']} {o['source']}"]["matched"] += 1

    for o in out:                              # a flag is recorded only when it is true
        o["reads"] = sorted(k for k, v in o["reads"].items() if v)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(o, sort_keys=True, separators=(",", ":")) + "\n" for o in out))
    report = {"rollouts": dict(sorted(cover.items())),
              "cut_short_matched": dict(sorted(cut_short.items())),
              # sweeps whose record an agent deleted: their rollouts, from the session records alone
              "deleted": [{"run": run, "sweep": name, "rollouts": len(lost[name]),
                           "cost_usd": round(sum(lost[name]), 2)} for run, name, _a, _b in deleted]}
    COVER.write_text(json.dumps(report, indent=1) + "\n")
    print(f"{len(out)} rollouts and sessions -> {OUT}")
    print("session records with no recorded row (sweeps cut short and run again):", dict(sorted(unmatched.items())))
    print("recorded rollouts without a matched record:",
          {k: v["recorded"] - v["matched"] for k, v in sorted(cover.items()) if v["recorded"] != v["matched"]})


if __name__ == "__main__":
    main()
