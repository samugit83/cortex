#!/usr/bin/env python3
"""bench.py — the lab's final measurement: Haiku with and without what Cortex evolved.

  bench.py prepare            commit each holdout scenario on its own branch off the
                              final HEAD (bench/<ID>), write bench/tasks.json
  bench.py arms [--arms ...]  build each named arm's harness under BENCH_OUT/harness
                              and write arms.json (what each one is, and what it
                              costs in always-on characters)
  bench.py run [--k 5] [--train-k 3] [--split holdout] [--arms none,evolved]
               [--only ID,ID] [--jobs auto|N]
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

Arms differ ONLY in the harness installed in the sandbox. Seven are derived from
the run under measurement, so each run gets its own; two are fixed and written by
hand, under lab/bench/harnesses/:

  none        no skills, no rules, CLAUDE.md as `cortex init` wrote it
  none2       built by the same code as `none`. The A/A check: the true difference
              between these two arms is zero, so whatever they report is the floor
              under every other comparison in the benchmark
  evolved     .claude/skills, .claude/rules and CLAUDE.md as that run kept them
  kitchen     `none` plus the whole of CONTRIBUTING.md in CLAUDE.md — everything
              the agent could need, always on, at full cost
  accept-all  `evolved` plus every candidate that run buried: what the loop would
              have produced with the gates switched off
  flat        `evolved`'s texts with scope removed: gated skills lose `paths`,
              path-scoped rules become path-less rules. Same words, no tiers
  desc-only   `evolved`'s skills keep name, description and paths; the body is
              replaced by neutral filler of similar length. Tests whether the
              description alone carries the effect (H12)
  ideal       hand-written, the forms the lab's design predicted
  swapped     `ideal`'s items in the other form, to test that the form matters

`bench.py arms` builds them; `bench.py run --arms a,b,c` measures them.
"""
import argparse
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
sys.path.insert(0, str(LAB / "bin"))
import guard                                              # noqa: E402
src = (LAB / "bin" / "lab").read_text()
L = types.ModuleType("labtool")
L.__file__ = str(LAB / "bin" / "lab")
exec(compile(src, "lab", "exec"), L.__dict__)
S, REPO = L.S, L.REPO
CORTEX = LAB.parent
HARNESS_PY = CORTEX / "bin" / "harness.py"
# harness.py is a script, not a package: load it the way `lab` is loaded above, so
# the benchmark's always-on accounting is literally Cortex's own.
HP = types.ModuleType("harness_py")
HP.__file__ = str(HARNESS_PY)
exec(compile(HARNESS_PY.read_text(), "harness.py", "exec"), HP.__dict__)
# BENCH_OUT / BENCH_SANDBOX move the outputs and the sandboxes (for rehearsals)
OUT = Path(os.environ.get("BENCH_OUT", HERE))
TASKS = OUT / "tasks.json"
RESULTS = OUT / "results.jsonl"
SANDBOX = Path(os.environ.get("BENCH_SANDBOX", "/tmp/cortex-lab-bench"))
HARNESSES = HERE / "harnesses"                            # the hand-written arms
ARMS_JSON = OUT / "arms.json"
# The rollout model. BENCH_MODEL overrides it for the model-change study (§4.8),
# which is the only place in the programme another model is allowed; every row
# records what it ran on, so two models can never be pooled by accident.
MODEL = os.environ.get("BENCH_MODEL") or "claude-haiku-4-5-20251001"
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
    TASKS.parent.mkdir(parents=True, exist_ok=True)
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
# An arm is a directory holding CLAUDE.md, skills/ and rules/ — exactly what
# `install()` copies into a sandbox. Seven are derived from the run under
# measurement; `ideal` and `swapped` are written by hand and are the same for
# every run, because they are the design's prediction, not a run's output.
DERIVED = ("none", "none2", "evolved", "kitchen", "accept-all", "flat", "desc-only")
STATIC = ("ideal", "swapped")
ALL_ARMS = DERIVED + STATIC

FILLER = (
    "This section is deliberately without content. It is here only so that this "
    "file occupies about as much of the context window as the text it replaces, "
    "so that two arms of the benchmark differ in what the body says and not in "
    "how long it is. Nothing in it describes this repository, its conventions, "
    "its tests or how to work in it. ")


def _frontmatter(text):
    """(fields-text, body). A file with no frontmatter has an empty fields-text."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 3)
    if end == -1:
        return "", text
    return text[4:end + 1], text[end + 5:]


def _drop_paths(fm):
    """Remove a `paths:` key and its list items from a frontmatter block."""
    out, skipping = [], False
    for line in fm.splitlines():
        if re.match(r"^paths\s*:", line):
            skipping = True
            continue
        if skipping and (line.startswith((" ", "\t", "-")) or not line.strip()):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def _filler(n):
    """Neutral text of about n characters."""
    if n <= 0:
        return ""
    reps = FILLER * (n // len(FILLER) + 1)
    return reps[:n].rstrip() + "\n"


def _empty(h):
    shutil.rmtree(h, ignore_errors=True)
    (h / "skills").mkdir(parents=True)
    (h / "rules").mkdir(parents=True)


def baseline_claude_md(meta):
    """CLAUDE.md as `cortex init` wrote it, from the commit that installed it."""
    return git(REPO, "show", f"{meta['claude_md_install_commit']}:CLAUDE.md")


def build_none(h, meta):
    _empty(h)
    (h / "CLAUDE.md").write_text(baseline_claude_md(meta) + "\n")


def build_none2(h, meta):
    # the A/A arm is `none`, built by the same function, on purpose
    build_none(h, meta)


def build_evolved(h, meta):
    _empty(h)
    for d in ("skills", "rules"):
        srcd = REPO / ".claude" / d
        if srcd.is_dir():
            shutil.copytree(srcd, h / d, dirs_exist_ok=True, symlinks=False)
    shutil.copy2(REPO / "CLAUDE.md", h / "CLAUDE.md")


def build_kitchen(h, meta):
    build_none(h, meta)
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    with open(h / "CLAUDE.md", "a", encoding="utf-8") as fh:
        fh.write("\n" + contributing.rstrip() + "\n")


def build_accept_all(h, meta):
    """`evolved` plus everything the gates buried: the loop with no gates."""
    build_evolved(h, meta)
    gy = REPO / ".evolve" / "graveyard"
    for d in sorted(p for p in gy.glob("*") if p.is_dir()) if gy.is_dir() else []:
        name = d.name
        if (d / "SKILL.md").is_file():
            if (h / "skills" / name).exists():      # a live item of the same name wins
                continue
            (h / "skills" / name).mkdir(parents=True)
            shutil.copy2(d / "SKILL.md", h / "skills" / name / "SKILL.md")
        elif (d / "RULE.md").is_file():
            if (h / "rules" / f"{name}.md").exists():
                continue
            shutil.copy2(d / "RULE.md", h / "rules" / f"{name}.md")


def build_flat(h, meta):
    """The same words with no scope: every skill and rule loses its `paths`."""
    build_evolved(h, meta)
    for f in list((h / "skills").glob("*/SKILL.md")) + list((h / "rules").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, body = _frontmatter(text)
        if not fm:
            continue
        fm = _drop_paths(fm)
        f.write_text((f"---\n{fm}---\n{body}" if fm.strip() else body), encoding="utf-8")


def build_desc_only(h, meta):
    """Skills keep their description and paths; their body says nothing (H12)."""
    build_evolved(h, meta)
    for f in (h / "skills").glob("*/SKILL.md"):
        text = f.read_text(encoding="utf-8")
        fm, body = _frontmatter(text)
        if not fm:
            continue
        f.write_text(f"---\n{fm}---\n\n{_filler(len(body.strip()))}", encoding="utf-8")


def build_static(h, meta, name):
    src = HARNESSES / name
    if not src.is_dir():
        sys.exit(f"bench: arm '{name}' needs a hand-written harness at {src}")
    _empty(h)
    for d in ("skills", "rules"):
        if (src / d).is_dir():
            shutil.copytree(src / d, h / d, dirs_exist_ok=True, symlinks=False)
    if (src / "CLAUDE.md").is_file():
        shutil.copy2(src / "CLAUDE.md", h / "CLAUDE.md")
    else:
        (h / "CLAUDE.md").write_text(baseline_claude_md(meta) + "\n")


BUILDERS = {"none": build_none, "none2": build_none2, "evolved": build_evolved,
            "kitchen": build_kitchen, "accept-all": build_accept_all,
            "flat": build_flat, "desc-only": build_desc_only}


def diff_count(a, b):
    """{"changed": n, "only_a": n, "only_b": n} over the two harnesses' files."""
    fa = {str(p.relative_to(a)): p.read_bytes() for p in a.rglob("*") if p.is_file()}
    fb = {str(p.relative_to(b)): p.read_bytes() for p in b.rglob("*") if p.is_file()}
    return {"changed": sum(1 for k in fa.keys() & fb.keys() if fa[k] != fb[k]),
            "only_evolved": len(fa.keys() - fb.keys()),
            "only_here": len(fb.keys() - fa.keys())}


def fingerprint(h):
    """A content hash of a harness: CLAUDE.md plus every skill and rule, by path."""
    import hashlib
    acc = hashlib.sha256()
    for f in sorted(p for p in h.rglob("*") if p.is_file()):
        acc.update(str(f.relative_to(h)).encode())
        acc.update(f.read_bytes())
    return acc.hexdigest()[:16]


def always_on_chars(h):
    """What this arm costs on EVERY turn, by Cortex's own accounting.

    CLAUDE.md is always in context. Beyond it, only a path-less rule (loaded
    whatever the agent reads) and an always-on skill's description are always on;
    a gated skill and a path-scoped rule cost nothing until their area is touched.
    Computed with harness.py's own Item, so the benchmark and `cortex tiers`
    cannot drift apart.
    """
    with tempfile.TemporaryDirectory(prefix="bench-chars-") as tmp:
        os.symlink(h, os.path.join(tmp, ".claude"))
        items, _ = HP.load_live(tmp)
        per = {it.name: it.always_on_chars for it in items}
    md = len((h / "CLAUDE.md").read_text(encoding="utf-8")) if (h / "CLAUDE.md").is_file() else 0
    return {"claude_md_chars": md, "item_chars": sum(per.values()),
            "always_on_chars": md + sum(per.values()), "per_item": per}


def snapshot_arms(meta, want=("none", "evolved"), root=None):
    """Freeze each arm's harness once, like a sweep does."""
    root = root or SANDBOX / "harness"
    arms, record = {}, {}
    for arm in want:
        if arm not in ALL_ARMS:
            sys.exit(f"bench: unknown arm '{arm}'. Known: {', '.join(ALL_ARMS)}")
        h = root / arm
        (BUILDERS[arm] if arm in BUILDERS else lambda x, m, n=arm: build_static(x, m, n))(h, meta)
        arms[arm] = h
        skills = sorted(d.name for d in (h / "skills").glob("*") if (d / "SKILL.md").is_file())
        rules = sorted(f.stem for f in (h / "rules").glob("*.md"))
        record[arm] = {"kind": "derived" if arm in DERIVED else "hand-written",
                       "dir": str(h), "skills": skills, "rules": rules,
                       "fingerprint": fingerprint(h), **always_on_chars(h)}
    # Two arms can come out byte-identical for a reason that is itself a result:
    # `accept-all` is `evolved` plus everything the run buried, and a run that
    # buried nothing makes them the same harness. Measuring one against the other
    # then yields a difference of exactly zero that looks like a finding and is
    # not one. Say so here, so the analysis can refuse to report it.
    # How much each derived arm actually perturbs `evolved`, file by file. It
    # matters because `desc-only` only rewrites SKILL bodies: on a harness that is
    # mostly rules it changes almost nothing, and H12 would then be answered by an
    # arm that barely differs from the one it is compared against.
    base = record.get("evolved", {}).get("dir")
    for arm, rec in record.items():
        same = sorted(o for o, r in record.items()
                      if o != arm and r.get("fingerprint") == rec.get("fingerprint"))
        rec["identical_to"] = same
        if base and arm != "evolved":
            rec["differs_from_evolved"] = diff_count(Path(base), Path(rec["dir"]))
        if same and arm not in ("none", "none2"):
            print(f"bench: NOTE — `{arm}` is byte-identical to {', '.join(same)}. "
                  f"Any comparison between them measures nothing.")
    ARMS_JSON.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(ARMS_JSON.read_text()) if ARMS_JSON.exists() else {}
    prev.update(record)
    ARMS_JSON.write_text(json.dumps({"built": datetime.now().isoformat(timespec="seconds"),
                                     "repo": str(REPO), **{k: v for k, v in prev.items()
                                                           if k not in ("built", "repo")}}, indent=1))
    return arms


def cmd_arms(args):
    meta = json.loads(TASKS.read_text())
    want = [a for a in args.arms.split(",") if a]
    snapshot_arms(meta, want)
    rec = json.loads(ARMS_JSON.read_text())
    print(f"{'arm':12} {'always-on':>10}  {'CLAUDE.md':>10}  items")
    for arm in want:
        r = rec[arm]
        items = ", ".join(sorted(r["skills"] + r["rules"])) or "—"
        print(f"{arm:12} {r['always_on_chars']:>10}  {r['claude_md_chars']:>10}  {items}")
    print(f"\n-> {ARMS_JSON}")


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
        return {"skills": None, "rules": None, "visible": None, "tokens": None,
                "cost_usd": None, "turns": None, "tool_calls": None,
                "read_contributing": None}


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
    want_arms = [a for a in args.arms.split(",") if a]
    arms = snapshot_arms(meta, want_arms)
    only = set(args.only.split(",")) if args.only else None
    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            row = json.loads(line)
            # A rollout that could not run (usage limit, auth, 5xx: rc outside 0/124)
            # stays in the file as a record of the outage, but it is not a measurement,
            # so a restart must measure it again rather than count it as done.
            if row.get("valid", 1):
                done.add((row["task"], row["arm"], row["r"]))
    # Every rollout still to run, in the order they start: arms interleaved.
    #
    # k is per SPLIT, because the pre-registration sets them apart: the holdout is
    # the inference and gets k=5, the training set is description and gets k=3.
    # One k for both quietly turns a 456-rollout benchmark into a 560-rollout one,
    # and for the eight-arm run it was the difference between $66 and $225.
    def k_for(split):
        return args.train_k if split == "train" and args.train_k else args.k

    tasks = [t for t in meta["tasks"] if not only or t["id"] in only]
    if args.split:
        tasks = [t for t in tasks if t["split"] == args.split]
    # PREREGISTRATION.md §5.1: a scenario that fails validation on THIS run's final
    # code is excluded from this run's benchmark, identically in every arm. It was
    # being recorded and not applied, which is the worst of both — a file that says
    # a task was excluded, and a results set in which it was not.
    drop = {x.strip() for x in (args.exclude or "").split(",") if x.strip()}
    if drop:
        before = len(tasks)
        tasks = [t for t in tasks if t["id"] not in drop]
        print(f"bench: excluding {len(drop)} task(s) that failed validation on this "
              f"run's final code: {' '.join(sorted(drop))} ({before} -> {len(tasks)})")
    jobs = [(t, arm, r) for t in tasks
            for r in range(1, k_for(t["split"]) + 1)
            for arm in want_arms if (t["id"], arm, r) not in done]
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
    # Usage running out does not look like a crash: `claude -p` exits 1 in seconds
    # and the rollout is written as INVALID, then the next one does the same, and a
    # whole benchmark "finishes" in minutes having measured nothing. BREAK rollouts
    # in a row that could not run stop the bench with exit 3, which the programme
    # reads as "stop and ask for a recharge". One stray 5xx resets on the next pass.
    BREAK = 5
    streak = [0]
    halt = threading.Event()

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
               "turns": seen.get("turns"), "tool_calls": seen.get("tool_calls"),
               "read_contributing": seen.get("read_contributing"), "model": MODEL,
               "t": datetime.now().isoformat(timespec="seconds")}
        if not row["valid"]:
            row["why"] = stream_error(stream)
        stream.unlink(missing_ok=True)
        with lock:
            with open(RESULTS, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            if row["valid"]:
                streak[0] = 0
            else:
                streak[0] += 1
                if streak[0] >= BREAK and not halt.is_set():
                    halt.set()
                    print(f"bench: {streak[0]} rollouts in a row could not run "
                          f"(rc={rc}: {row.get('why') or 'no message'}) — stopping", flush=True)
            print(f"{t['id']:4} {t['split']:7} {arm:8} r{r} -> {('INVALID rc=' + str(rc)) if not row['valid'] else 'PASS' if row['pass'] else 'fail ' + verdict} "
                  f"({secs}s ${seen.get('cost_usd')})" + (f" [w{k}]" if n > 1 else ""), flush=True)

    def worker(k):
        try:
            refresh(sandbox(k))
        except (Exception, SystemExit) as ex:          # noqa: BLE001
            with lock:
                print(f"bench: worker {k} cannot prepare its sandbox: {ex}", flush=True)
        while True:
            if halt.is_set():
                return
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
    if halt.is_set():
        print(f"\nbench: STOPPED — {streak[0]} rollouts in a row could not run. Usage limit or "
              f"auth? Nothing more was started; `bench.py run` again measures the rest, "
              f"including the rollouts that could not run.", flush=True)
        sys.exit(3)
    if failed:
        print(f"\nbench: {len(failed)} rollout(s) DID NOT RUN (no row written; `bench.py run` again retries them):")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)


def stream_error(stream):
    """The CLI's own words when a rollout could not run ("usage limit reached",
    "invalid API key", ...), from the last result event it streamed."""
    try:
        for line in reversed(Path(stream).read_text(errors="replace").splitlines()):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "result":
                return str(ev.get("result") or ev.get("subtype") or "")[-200:]
    except OSError:
        pass
    return ""


# ------------------------------------------------------------------ report --
def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def cmd_report(_args):
    """A per-run summary. It is deliberately descriptive: the paper's numbers come
    from reports/analysis/, which reads the same rows and does the clustering,
    the bootstrap and the permutation test this file does not."""
    rows = [json.loads(l) for l in RESULTS.read_text().splitlines()] if RESULTS.exists() else []
    invalid = [r for r in rows if not r["valid"]]
    rows = [r for r in rows if r["valid"]]
    arms = sorted({r["arm"] for r in rows}, key=lambda a: (a not in ALL_ARMS, ALL_ARMS.index(a) if a in ALL_ARMS else 0))
    ref = "none" if "none" in arms else (arms[0] if arms else None)
    chars = json.loads(ARMS_JSON.read_text()) if ARMS_JSON.exists() else {}

    # Arms are compared on the same tasks, the same number of times. A task whose
    # arms have unequal numbers of valid rollouts (one that did not run, an
    # interrupted run) would tilt the comparison: it is left out and listed, so
    # that "incomplete" is visible rather than quietly averaged away.
    per = {}
    for r in rows:
        per.setdefault(r["task"], {})[r["arm"]] = per.setdefault(r["task"], {}).get(r["arm"], 0) + 1
    counts = {t: {a: c.get(a, 0) for a in arms} for t, c in per.items()}
    unpaired = {t: c for t, c in counts.items() if len({n for n in c.values() if n}) > 1
                or any(c.get(a, 0) == 0 for a in arms)}
    rows = [r for r in rows if r["task"] not in unpaired]

    def rate(rs):
        return (sum(r["pass"] for r in rs) / len(rs), len(rs)) if rs else (0.0, 0)

    def per_task(split, family, arm):
        out = {}
        for r in rows:
            if r["arm"] == arm and r["split"] == split and (family is None or r["family"] == family):
                out.setdefault(r["task"], []).append(r["pass"])
        return {t: sum(v) / len(v) for t, v in out.items()}

    def paired(split, family, arm):
        """Mean per-task difference against the reference arm, over the tasks both measured."""
        a, b = per_task(split, family, arm), per_task(split, family, ref)
        both = sorted(set(a) & set(b))
        if not both:
            return None, 0
        return sum(a[t] - b[t] for t in both) / len(both), len(both)

    fams = {"A": "user-visible change (CHANGELOG)", "B": "money (billing)", "C": "new exporter",
            "D": "control (plain bugs)", "E": "time (clock)"}
    out = ["# Benchmark — Haiku 4.5, one column per harness", "",
           f"_{datetime.now().isoformat(timespec='minutes')} · {len(rows)} valid rollouts · "
           f"{len(invalid)} invalid · judge: the lab oracle · reference arm: `{ref}`_", "",
           "Intervals are Wilson over **rollouts** and ignore that repeats of one task are "
           "correlated, so they are description, not inference. The gain column is the mean "
           "**per-task** difference against the reference arm, over the tasks both arms measured.", ""]

    if unpaired:
        out += [f"> **Incomplete:** {len(unpaired)} task(s) left out because their arms were not "
                f"measured the same number of times — run `bench.py run` again to complete them: "
                + ", ".join(f"{t} (" + ", ".join(f"{a} {c.get(a, 0)}" for a in arms) + ")"
                            for t, c in sorted(unpaired.items())), ""]
    planned = [t["id"] for t in json.loads(TASKS.read_text())["tasks"]] if TASKS.exists() else []
    measured = set(counts)
    if [t for t in planned if t not in measured]:
        out += [f"> **Not measured:** {len([t for t in planned if t not in measured])} of "
                f"{len(planned)} prepared task(s) have no valid rollout in any arm: "
                + ", ".join(t for t in planned if t not in measured), ""]

    for split in ("holdout", "train"):
        if not any(r["split"] == split for r in rows):
            continue
        out += [f"## {split}", "", "| Family | " + " | ".join(arms) + " | " +
                " | ".join(f"gain {a}" for a in arms if a != ref) + " | tasks |",
                "|---" * (1 + len(arms) + len([a for a in arms if a != ref]) + 1) + "|"]
        for f in list("ABCDE") + [None]:
            cells, gains = [], []
            for arm in arms:
                rs = [r for r in rows if r["split"] == split and r["arm"] == arm
                      and (f is None or r["family"] == f)]
                pr, n = rate(rs)
                lo, hi = wilson(pr, n)
                cells.append(f"{pr:.0%} ({n}) [{lo:.0%}–{hi:.0%}]" if n else "—")
            for arm in arms:
                if arm == ref:
                    continue
                g, nt = paired(split, f, arm)
                gains.append(f"{g:+.0%}" if g is not None else "—")
            ntasks = len({r["task"] for r in rows if r["split"] == split and (f is None or r["family"] == f)})
            if not ntasks:
                continue
            label = f"{f} {fams[f]}" if f else "**all**"
            out.append(f"| {label} | " + " | ".join(cells) + " | " + " | ".join(gains) + f" | {ntasks} |")
        out.append("")

    out += ["## What each arm costs", "",
            "| Arm | always-on chars | CLAUDE.md | items | tokens/rollout | $/rollout | s/rollout | turns | tool calls | read CONTRIBUTING |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for arm in arms:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        def mean(k):
            vals = [r.get(k) for r in rs if isinstance(r.get(k), (int, float))]
            return sum(vals) / len(vals) if vals else 0.0
        c = chars.get(arm, {})
        items = ", ".join(sorted(c.get("skills", []) + c.get("rules", []))) or "—"
        rc = [r.get("read_contributing") for r in rs if r.get("read_contributing") is not None]
        out.append(f"| {arm} | {c.get('always_on_chars', '?')} | {c.get('claude_md_chars', '?')} | {items} "
                   f"| {mean('tokens'):,.0f} | {mean('cost_usd'):.3f} | {mean('secs'):.0f} "
                   f"| {mean('turns'):.1f} | {mean('tool_calls'):.1f} "
                   f"| {(sum(rc) / len(rc) if rc else 0):.0%} |")

    out += ["", "## Why rollouts failed", "", "| Arm | verdict | count |", "|---|---|---|"]
    for arm in arms:
        counts = {}
        for r in rows:
            if r["arm"] == arm and not r["pass"]:
                counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        for v, c in sorted(counts.items(), key=lambda x: -x[1]):
            out.append(f"| {arm} | {v} | {c} |")

    if invalid:
        out += ["", "## Invalid rollouts (excluded)", "", "| Arm | reason | count |", "|---|---|---|"]
        counts = {}
        for r in invalid:
            counts[(r["arm"], r.get("verdict") or f"rc {r.get('rc')}")] = \
                counts.get((r["arm"], r.get("verdict") or f"rc {r.get('rc')}"), 0) + 1
        for (arm, why), c in sorted(counts.items(), key=lambda x: -x[1]):
            out.append(f"| {arm} | {why} | {c} |")

    out += ["", "## What loaded, per arm", ""]
    for arm in arms:
        rs = [r for r in rows if r["arm"] == arm]
        items = {}
        for r in rs:
            for name in (r.get("visible") or []):
                items.setdefault(name, {"visible": 0, "fired": 0})["visible"] += 1
            for name in set((r.get("skills") or []) + (r.get("rules") or [])):
                items.setdefault(name, {"visible": 0, "fired": 0})["fired"] += 1
        if not items:
            continue
        out.append(f"**{arm}** ({len(rs)} rollouts)")
        for name, c in sorted(items.items()):
            out.append(f"- `{name}`: in context in {c['visible']}, loaded/used in {c['fired']}")
        out.append("")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "REPORT.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "arms", "run", "report"])
    ap.add_argument("--k", type=int, default=3,
                    help="rollouts per task per arm (the holdout's k)")
    ap.add_argument("--train-k", type=int, default=0,
                    help="a different k for the TRAIN split (0 = same as --k)")
    ap.add_argument("--split", default="", choices=["", "holdout", "train"],
                    help="measure only this split — the ablation arms are holdout-only")
    ap.add_argument("--arms", default="none,evolved")
    ap.add_argument("--only", default="")
    ap.add_argument("--exclude", default="",
                    help="task ids to leave out, identically in every arm (§5.1)")
    ap.add_argument("--jobs", default="auto", help="rollouts at once: auto (default) or a number")
    args = ap.parse_args()
    if args.cmd in ("prepare", "run"):
        guard.protect(REPO, f"run `bench.py {args.cmd}` against")
    # Guard the exact files a command writes, not the directory that holds them:
    # BENCH_OUT for D0 is lab/bench/, where results.jsonl and REPORT.md are evidence
    # and arms.json is not. Guarding the directory would protect neither (it is not
    # itself listed) and guarding it loosely would refuse harmless writes.
    for f in {"prepare": ("tasks.json",), "run": ("results.jsonl",),
              "arms": ("arms.json",), "report": ("REPORT.md",)}[args.cmd]:
        guard.protect(OUT / f, f"have `bench.py {args.cmd}` write")
    {"prepare": cmd_prepare, "arms": cmd_arms, "run": cmd_run,
     "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
