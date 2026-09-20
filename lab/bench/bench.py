#!/usr/bin/env python3
"""bench.py — the lab's final measurement: Haiku with and without what Cortex evolved.

  bench.py prepare            commit each holdout scenario on its own branch off the
                              final HEAD (bench/<ID>), write bench/tasks.json
  bench.py run [--k 3] [--arms none,evolved] [--only ID,ID] [--jobs auto|N]
                              run every task k times per arm, interleaved, in clean
                              sandboxes; judge each rollout with the lab's oracle.
                              --jobs: rollouts at once, each in its own sandbox; auto
                              (default) sizes it like a Cortex sweep, from the lab's
                              measurement.parallel settings and the RAM free now
  bench.py report             bench/REPORT.md: pass rates per family, split and arm,
                              95% Wilson intervals, paired gains, cost, tokens, time

Tasks: the training scenarios, each from the commit its session started from (the
teammate's commit, i.e. the harvested base_sha), and the 15 holdout scenarios,
never seen by /evolve, committed onto the final code. The judge is the lab oracle
(test passes, suite and lint green, CHANGELOG changed for family A, QA's test
untouched) — the same for every arm and every task, unlike harvested checks.

Arms differ ONLY in the harness installed in the sandbox:
  none      no skills, no rules, CLAUDE.md as `cortex init` wrote it
  evolved   .claude/skills, .claude/rules and CLAUDE.md as the lab has them now
"""
import argparse
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import types
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
src = (LAB / "bin" / "lab").read_text()
L = types.ModuleType("labtool")
L.__file__ = str(LAB / "bin" / "lab")
exec(compile(src, "lab", "exec"), L.__dict__)
S, REPO = L.S, L.REPO
CORTEX = LAB.parent
HARNESS_PY = CORTEX / "bin" / "harness.py"
# BENCH_OUT / BENCH_SANDBOX move the outputs and the sandboxes (for rehearsals)
OUT = Path(os.environ.get("BENCH_OUT", HERE))
TASKS = OUT / "tasks.json"
RESULTS = OUT / "results.jsonl"
SANDBOX = Path(os.environ.get("BENCH_SANDBOX", "/tmp/cortex-lab-bench"))
MODEL = "claude-haiku-4-5-20251001"
TIMEOUT = 600
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", DISABLE_AUTOUPDATER="1")


def git(repo, *args, env=None, check=True):
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env or ENV)
    if check and p.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {p.stderr}")
    return p.stdout.strip()


# ------------------------------------------------------------------ prepare --
def cmd_prepare(_args):
    st = L.load_state()
    head = git(REPO, "rev-parse", "HEAD")
    tasks = []
    for r, ids in S.ROUNDS.items():
        for sid in ids:
            rec = st["scenarios"].get(sid, {})
            if rec.get("status") != "done":
                continue
            tasks.append({"id": sid, "split": "train", "family": S.by_id(sid)["family"], "base": rec["base"]})
    holdout = [s for s in S.SCENARIOS if s["split"] == "holdout"]
    for s in holdout:
        branch = f"bench/{s['id']}"
        if git(REPO, "rev-parse", "--verify", "--quiet", branch, check=False):
            base = git(REPO, "rev-parse", branch)
        else:
            w = SANDBOX / "prepare"
            shutil.rmtree(w, ignore_errors=True)
            git(REPO.parent, "clone", "-q", str(REPO), str(w))
            git(w, "checkout", "-q", "-b", branch, head)
            for rel, content in s["files"].items():
                (w / rel).parent.mkdir(parents=True, exist_ok=True)
                (w / rel).write_text(content, encoding="utf-8")
            git(w, "add", "-A")
            git(w, "commit", "-q", "-m", s["message"], env=L.author_env(s["author"]))
            git(w, "push", "-q", "origin", f"{branch}:{branch}")
            base = git(w, "rev-parse", "HEAD")
            shutil.rmtree(w, ignore_errors=True)
        tasks.append({"id": s["id"], "split": "holdout", "family": s["family"], "base": base})
    install_commit = git(REPO, "log", "--format=%H", "-1", "--", "CLAUDE.md", check=False)
    first = git(REPO, "log", "--reverse", "--format=%H", "--", "CLAUDE.md").splitlines()
    meta = {"prepared": datetime.now().isoformat(timespec="seconds"), "head": head,
            "claude_md_install_commit": first[0] if first else install_commit,
            "provenance": provenance(), "tasks": tasks}
    TASKS.write_text(json.dumps(meta, indent=1))
    print(f"{len(tasks)} tasks: {sum(t['split'] == 'train' for t in tasks)} train, "
          f"{sum(t['split'] == 'holdout' for t in tasks)} holdout -> {TASKS}")


# ------------------------------------------------------------- provenance --
def provenance():
    """Who produced the harness this benchmark is about to measure.

    An arm IS a harness, and a harness proposed with a judge in the loop is a
    different treatment from one proposed without — even though the two are
    byte-identical in form, which is exactly why this has to be recorded rather
    than inferred later from the files. `/evolve` may consult Jev when choosing
    the theme, the tier and the scope; the gates never do. A benchmark that does
    not say which it was cannot be compared with one that did.
    """
    jev = {"enabled": False, "model": None, "requests": 0, "answered": 0}
    log = REPO / ".evolve" / "jev"
    if log.is_dir():
        for f in sorted(log.glob("*.jsonl")):
            for line in f.read_text(errors="replace").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(r, dict) or r.get("summary"):
                    continue
                jev["enabled"] = True
                jev["requests"] += 1
                jev["answered"] += 1 if r.get("outcome") == "ok" else 0
                jev["model"] = jev["model"] or r.get("model")
    return {"jev": jev,
            "cortex": shutil.which("cortex"),
            "env_jev_enabled": os.environ.get("JEV_ENABLED"),
            "env_jev_model": os.environ.get("JEV_MODEL")}


# -------------------------------------------------------------------- arms --
def snapshot_arms(meta):
    """Freeze each arm's harness once, like a sweep does."""
    arms = {}
    root = SANDBOX / "harness"
    shutil.rmtree(root, ignore_errors=True)
    for arm in ("none", "evolved"):
        h = root / arm
        (h / "skills").mkdir(parents=True)
        (h / "rules").mkdir(parents=True)
        if arm == "evolved":
            for d in ("skills", "rules"):
                srcd = REPO / ".claude" / d
                if srcd.is_dir():
                    shutil.copytree(srcd, h / d, dirs_exist_ok=True, symlinks=False)
            shutil.copy2(REPO / "CLAUDE.md", h / "CLAUDE.md")
        else:
            claude_md = git(REPO, "show", f"{meta['claude_md_install_commit']}:CLAUDE.md")
            (h / "CLAUDE.md").write_text(claude_md + "\n")
        arms[arm] = h
    return arms


def install(w, h):
    for d in ("skills", "rules"):
        shutil.rmtree(w / ".claude" / d, ignore_errors=True)
        shutil.copytree(h / d, w / ".claude" / d)
    shutil.copy2(h / "CLAUDE.md", w / "CLAUDE.md")


def refresh(w):
    """A sandbox kept from an earlier run lacks every commit made since (new
    rounds, new holdout branches): checking one out would fail. Fetch them."""
    git(w, "fetch", "-q", str(REPO), "+refs/heads/*:refs/remotes/src/*", check=False)


def sandbox(k=1):
    w = SANDBOX / f"work-{k}"
    if not (w / ".git").exists():
        shutil.rmtree(w, ignore_errors=True)
        git(REPO.parent, "clone", "-q", "--no-checkout", str(REPO), str(w))
        git(w, "config", "core.sparseCheckout", "true")
        (w / ".git" / "info").mkdir(parents=True, exist_ok=True)
        (w / ".git" / "info" / "sparse-checkout").write_text("/*\n!/.evolve/\n")
        git(w, "remote", "remove", "origin", check=False)
        git(w, "config", "user.email", "bench@local")
        git(w, "config", "user.name", "bench")
    return w


def reset(w, base, h):
    git(w, "checkout", "-q", "-f", "--detach", base)
    git(w, "clean", "-qfdx")
    shutil.rmtree(w / ".evolve", ignore_errors=True)
    L.purge_caches(w)
    install(w, h)


# --------------------------------------------------------------------- run --
def observe(stream, h, w, prompt_file):
    p = subprocess.run([sys.executable, str(HARNESS_PY), "observe", str(stream), str(h), str(w), str(prompt_file)],
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"skills": None, "rules": None, "visible": None, "tokens": None, "cost_usd": None}


def workers_for(jobs, setting):
    """How many rollouts at once: the same sizing as a Cortex sweep in the lab repo."""
    cmd = [sys.executable, str(HARNESS_PY), "parallel", "--kind", "rollouts", "--jobs", str(max(1, jobs)), "--json"]
    if setting and setting != "auto":
        cmd += ["--override", setting]
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"bench: cannot size the workers: {p.stderr.strip() or p.stdout.strip()}")
    return json.loads(p.stdout)


def cmd_run(args):
    meta = json.loads(TASKS.read_text())
    arms = snapshot_arms(meta)
    want_arms = args.arms.split(",")
    only = set(args.only.split(",")) if args.only else None
    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            row = json.loads(line)
            done.add((row["task"], row["arm"], row["r"]))
    # every rollout still to run, in the order they start: arms interleaved
    jobs = [(t, arm, r) for t in meta["tasks"] if not only or t["id"] in only
            for r in range(1, args.k + 1) for arm in want_arms if (t["id"], arm, r) not in done]
    if not jobs:
        print("bench: nothing left to run")
        return
    par = workers_for(len(jobs), args.jobs)
    n = par["workers"]
    print(f"bench: {len(jobs)} rollouts, {n} at a time — {par['why']}", flush=True)
    todo = queue.Queue()
    for j in jobs:
        todo.put(j)
    lock = threading.Lock()
    failed = []                                        # rollouts that could not run at all

    def one(k, t, arm, r):
        w = sandbox(k)
        s = S.by_id(t["id"])
        stream, prompt_file = SANDBOX / f"rollout-{k}.jsonl", SANDBOX / f"prompt-{k}.txt"
        prompt_file.write_text(s["prompt"])
        reset(w, t["base"], arms[arm])
        t0 = time.time()
        try:
            with open(stream, "w") as fh:
                p = subprocess.run(["claude", "-p", s["prompt"], "--output-format", "stream-json", "--verbose",
                                    "--permission-mode", "acceptEdits", "--model", MODEL],
                                   cwd=w, stdout=fh, stderr=subprocess.DEVNULL, timeout=TIMEOUT, env=ENV)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = 124
        secs = round(time.time() - t0)
        seen = observe(stream, arms[arm], w, prompt_file)
        verdict, detail = L.oracle(w, s, t["base"])
        row = {"task": t["id"], "split": t["split"], "family": t["family"], "arm": arm, "r": r,
               "pass": int(verdict == "ok"), "verdict": verdict, "detail": detail[:2], "rc": rc,
               "valid": int(rc in (0, 124)), "secs": secs, "tokens": seen.get("tokens"),
               "cost_usd": seen.get("cost_usd"), "skills": seen.get("skills"),
               "rules": seen.get("rules"), "visible": seen.get("visible"), "w": k,
               "t": datetime.now().isoformat(timespec="seconds")}
        stream.unlink(missing_ok=True)
        with lock:
            with open(RESULTS, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"{t['id']:4} {t['split']:7} {arm:8} r{r} -> {'PASS' if row['pass'] else 'fail ' + verdict} "
                  f"({secs}s ${seen.get('cost_usd')})" + (f" [w{k}]" if n > 1 else ""), flush=True)

    def worker(k):
        try:
            refresh(sandbox(k))
        except (Exception, SystemExit) as ex:          # noqa: BLE001
            with lock:
                print(f"bench: worker {k} cannot prepare its sandbox: {ex}", flush=True)
        while True:
            try:
                t, arm, r = todo.get_nowait()
            except queue.Empty:
                return
            # git() and friends end with sys.exit: SystemExit is not an Exception,
            # and a thread swallows it without a word — the rollout would simply
            # vanish. Catch both, say so, and keep going with the next one.
            try:
                one(k, t, arm, r)
            except (Exception, SystemExit) as ex:      # noqa: BLE001
                msg = (str(ex).strip().splitlines() or [repr(ex)])[0]
                with lock:
                    failed.append(f"{t['id']} {arm} r{r}: {msg}")
                    print(f"{t['id']:4} {arm:8} r{r} -> DID NOT RUN: {msg}" + (f" [w{k}]" if n > 1 else ""), flush=True)

    threads = [threading.Thread(target=worker, args=(k,), daemon=True) for k in range(1, n + 1)]
    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    print(f"bench: done in {round(time.time() - t0)} s", flush=True)
    if failed:
        print(f"\nbench: {len(failed)} rollout(s) DID NOT RUN (no row written; `bench.py run` again retries them):")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)


# ------------------------------------------------------------------ report --
def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def cmd_report(_args):
    rows = [json.loads(l) for l in RESULTS.read_text().splitlines()] if RESULTS.exists() else []
    rows = [r for r in rows if r["valid"]]
    # Arms are compared on the same tasks, the same number of times. A task whose
    # arms have unequal numbers of valid rollouts (a rollout that did not run, an
    # interrupted run) would tilt the comparison: it is left out and listed.
    per = {}
    for r in rows:
        per.setdefault(r["task"], {"none": 0, "evolved": 0})
        per[r["task"]][r["arm"]] = per[r["task"]].get(r["arm"], 0) + 1
    unpaired = {t: c for t, c in per.items() if c.get("none", 0) != c.get("evolved", 0)}
    rows = [r for r in rows if r["task"] not in unpaired]
    planned = [t["id"] for t in json.loads(TASKS.read_text())["tasks"]] if TASKS.exists() else []
    unmeasured = [t for t in planned if t not in per]
    fams = {"A": "user-visible change (CHANGELOG)", "B": "money (billing)", "C": "new exporter",
            "D": "control (plain bugs)", "E": "time (clock)"}
    out = ["# Benchmark — Haiku 4.5 with and without the evolved harness", "",
           f"_{datetime.now().isoformat(timespec='minutes')} · {len(rows)} valid rollouts · judge: the lab oracle_", ""]
    if unpaired:
        out += [f"> **Incomplete:** {len(unpaired)} task(s) left out because their arms were not measured the "
                f"same number of times — run `bench.py run` again to complete them: "
                + ", ".join(f"{t} (none {c.get('none', 0)}, evolved {c.get('evolved', 0)})" for t, c in sorted(unpaired.items())),
                ""]
    if unmeasured:
        out += [f"> **Not measured:** {len(unmeasured)} of {len(planned)} prepared task(s) have no valid rollout "
                f"in either arm: {', '.join(unmeasured)}", ""]
    for split in ("holdout", "train"):
        out += [f"## {split}", "", "| Family | none | evolved | gain | tasks |", "|---|---|---|---|---|"]
        for f in "ABCDE":
            cells = []
            for arm in ("none", "evolved"):
                rs = [r for r in rows if r["split"] == split and r["family"] == f and r["arm"] == arm]
                n = len(rs)
                p = sum(r["pass"] for r in rs) / n if n else 0
                lo, hi = wilson(p, n)
                cells.append((p, n, lo, hi))
            ntasks = len({r["task"] for r in rows if r["split"] == split and r["family"] == f})
            if not ntasks:
                continue
            (p0, n0, l0, h0), (p1, n1, l1, h1) = cells
            out.append(f"| {f} {fams[f]} | {p0:.0%} ({n0}) [{l0:.0%}–{h0:.0%}] | {p1:.0%} ({n1}) [{l1:.0%}–{h1:.0%}] "
                       f"| {p1 - p0:+.0%} | {ntasks} |")
        out.append("")
    out += ["## Cost per rollout", "", "| Arm | tokens (mean) | $ (mean) | seconds (mean) |", "|---|---|---|---|"]
    for arm in ("none", "evolved"):
        rs = [r for r in rows if r["arm"] == arm]
        if rs:
            mean = lambda k: sum((r.get(k) or 0) for r in rs) / len(rs)
            out.append(f"| {arm} | {mean('tokens'):,.0f} | {mean('cost_usd'):.3f} | {mean('secs'):.0f} |")
    out += ["", "## Why rollouts failed", "", "| Arm | verdict | count |", "|---|---|---|"]
    for arm in ("none", "evolved"):
        counts = {}
        for r in rows:
            if r["arm"] == arm and not r["pass"]:
                counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        for v, c in sorted(counts.items(), key=lambda x: -x[1]):
            out.append(f"| {arm} | {v} | {c} |")
    out += ["", "## What loaded (evolved arm)", ""]
    ev = [r for r in rows if r["arm"] == "evolved"]
    items = {}
    for r in ev:
        for name in (r.get("visible") or []):
            items.setdefault(name, {"visible": 0, "fired": 0})["visible"] += 1
        for name in set((r.get("skills") or []) + (r.get("rules") or [])):
            items.setdefault(name, {"visible": 0, "fired": 0})["fired"] += 1
    for name, c in sorted(items.items()):
        out.append(f"- `{name}`: in context in {c['visible']} of {len(ev)} rollouts, loaded/used in {c['fired']}")
    (OUT / "REPORT.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "run", "report"])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--arms", default="none,evolved")
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", default="auto", help="rollouts at once: auto (default) or a number")
    args = ap.parse_args()
    {"prepare": cmd_prepare, "run": cmd_run, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
