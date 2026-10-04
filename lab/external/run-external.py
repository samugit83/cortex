#!/usr/bin/env python3
"""run-external.py — the whole loop on a repository nobody in this project built.

  run-external.py setup      build the working repo, split the tasks, cortex init
  run-external.py train      the training sessions, with /harvest and /evolve
  run-external.py bench [--k 5] [--arms none,evolved]
  run-external.py export     -> reports/data/external.jsonl

This is the block the programme counts as its single most valuable one, because it
answers the hardest attack on the whole paper: *"you built the repository, the
house rules and the tasks, so of course it works."*

Nothing here is invented for the occasion:

* the **repository** is `hynek/structlog`, chosen by a rule fixed before any
  candidate was inspected (`SELECTION.md`);
* the **tasks** are its own commits, mined and validated by `mine-tasks.py`: the
  implementation reverted at its own commit, the tests kept as the specification;
* the **house rule** is not ours either — it is `ruff` with `select = ["ALL"]`,
  the project's own configuration;
* the **corrections** are the repository's own CI output, pasted back verbatim,
  because there is no scripted teacher here to play the user;
* the **judge** is its own test suite plus its own linter.

The split is temporal and fixed before the first session: the eight **older**
commits train, the four **newest** are the holdout. Training on the past and
testing on the future is the split that cannot leak.
"""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORTEX = HERE.parent.parent
WORKSPACE = CORTEX.parent / "cortex-eval"
EXT = WORKSPACE / "external"
RUN = WORKSPACE / "runs" / "X1"
REPO = RUN / "structlog"
TASKS = EXT / "structlog-tasks.json"
DATA = CORTEX / "lab" / "reports" / "data"
MODEL = "claude-haiku-4-5-20251001"
# The Python every rollout, check and session sees: structlog's test tools and NOT
# structlog itself, first on PATH, with PYTHONPATH=src. Cortex validates and measures
# each harvested task in a fresh `git clone` of the repository, which has no .venv,
# and runs its check as `cd <clone> && env <rollout_env> bash check.sh`; /harvest
# teaches `python3 -m pytest …`, and this machine's python3 has no pytest at all.
# Without this every structlog task would fail preflight on its FIXED state, be
# quarantined, and /evolve would refuse to run (min_valid_tasks) — H14 would have
# measured "no gain" for an infrastructure reason. structlog is left out on purpose:
# if PYTHONPATH were ever lost, `import structlog` fails loudly instead of quietly
# importing some other copy's code.
SANDBOX_VENV = RUN / "sandbox-venv"
# The lint stage runs the ruff the PROJECT pinned at that commit (its
# .pre-commit-config.yaml), not whatever ruff is newest. Today's ruff with
# select=["ALL"] finds 51-56 errors in structlog's own upstream commits — rules that
# did not exist when the code was written — so every task was unsolvable as
# defined, and every session was "corrected" for lint in files it never touched.
# Under its own pin each of the twelve upstream fixes is clean. A `ruff` dispatcher
# replaces the sandbox Python's binary: it reads the checkout's pin and runs that
# version, so `ruff …` and `python -m ruff …` both get the project's own linter.
RUFFS = RUN / "ruff"
RUFF = SANDBOX_VENV / "bin" / "ruff"
DISPATCH = r"""#!/usr/bin/env bash
# ruff, as the project pinned it at this checkout (.pre-commit-config.yaml)
root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ver=$(python3 - "$root/.pre-commit-config.yaml" <<'EOF'
import re, sys
try:
    t = open(sys.argv[1]).read()
except OSError:
    sys.exit(0)
m = re.search(r"ruff-pre-commit\s*\n\s*rev:\s*v?([0-9.]+)", t)
print(m.group(1) if m else "")
EOF
)
bin="__RUFFS__/$ver/bin/ruff"
if [ -z "$ver" ] || [ ! -x "$bin" ]; then
  echo "ruff dispatcher: no installed ruff for this checkout's pin '${ver:-none}'" >&2
  exit 2
fi
exec "$bin" "$@"
"""


def ruff_pin(sha):
    import re as _re
    t = sh(["git", "show", f"{sha}:.pre-commit-config.yaml"], cwd=REPO).stdout
    m = _re.search(r"ruff-pre-commit\s*\n\s*rev:\s*v?([0-9.]+)", t)
    return m.group(1) if m else None


def install_ruffs(shas):
    pins = sorted({v for v in (ruff_pin(x) for x in shas) if v})
    for v in pins:
        if not (RUFFS / v / "bin" / "ruff").exists():
            sh(["uv", "venv", str(RUFFS / v), "--python", "3.12", "-q"], quiet=False)
            sh(["uv", "pip", "install", "--python", str(RUFFS / v / "bin" / "python"), "-q",
                f"ruff=={v}"], quiet=False)
    RUFF.unlink(missing_ok=True)
    RUFF.write_text(DISPATCH.replace("__RUFFS__", str(RUFFS)))
    RUFF.chmod(0o755)
    return pins
TEST_DEPS = ("pytest pytest-asyncio freezegun simplejson pretend rich better-exceptions "
             "twisted time-machine ruff").split()
DENY = ["Bash(sudo:*)", "Bash(git push:*)", "Bash(curl:*)", "Bash(wget:*)", "Bash(ssh:*)",
        "ScheduleWakeup", "CronCreate", "RemoteTrigger", "WebFetch", "WebSearch"]
MAX_CORRECTIONS = 3
HOLDOUT = ("X01", "X02", "X03", "X04")      # the four NEWEST commits; fixed here


def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    RUN.mkdir(parents=True, exist_ok=True)
    with open(RUN / "run.log", "a") as fh:
        fh.write(line + "\n")


def sh(cmd, cwd=None, env=None, timeout=None, quiet=True):
    p = subprocess.run(cmd, cwd=cwd, env=env or os.environ, capture_output=True,
                       text=True, timeout=timeout)
    if not quiet and p.returncode != 0:
        log(f"  ! {' '.join(str(c) for c in cmd)} -> {p.returncode}")
    return p


def sandbox_path():
    return f"{SANDBOX_VENV / 'bin'}{os.pathsep}" + os.environ.get("PATH", "")


def env_for(cortex_home, jev="off"):
    env = dict(os.environ)
    # the sessions see the same Python as the sweeps, so a check the agent writes and
    # tries here is the check that will run in a clone
    env["PATH"] = f"{cortex_home / 'bin'}{os.pathsep}" + sandbox_path()
    env["PYTHONPATH"] = "src"
    env["JEV_ENABLED"] = "1" if jev == "on" else "0"
    if jev != "on":
        env["JEV_API_KEY"] = ""
    env["DISABLE_AUTOUPDATER"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def py(repo):
    return str(Path(repo) / ".venv" / "bin" / "python")


# ------------------------------------------------------------------ oracle --
def check(repo, task, timeout=300):
    """The repository's own judgement: its tests, then its linter.

    Two parts, and the order matters. The tests say whether the change works; the
    linter says whether it was done the way this project does things. That is the
    same shape as the lab's oracle, except that here we wrote neither half.
    """
    t = sh([py(repo), "-m", "pytest", "-q", "-p", "no:cacheprovider", *task["tests"]],
           cwd=repo, timeout=timeout)
    if t.returncode != 0:
        return "test", (t.stdout + t.stderr)[-2500:]
    rest = ["tests"] + [f"--ignore={x}" for x in task["tests"]]
    s = sh([py(repo), "-m", "pytest", "-q", "-p", "no:cacheprovider", *rest],
           cwd=repo, timeout=timeout)
    if s.returncode != 0:
        return "suite", (s.stdout + s.stderr)[-2500:]
    lint = sh([str(RUFF), "check", "src", "tests"], cwd=repo, timeout=120)
    if lint.returncode != 0:
        return "lint", (lint.stdout + lint.stderr)[-2500:]
    return "ok", ""


CORRECTION = {
    "test": "CI is red. `python -m pytest {tests}` fails:\n\n```\n{out}\n```\n\nPlease fix it.",
    "suite": "Your change broke other tests. The rest of the suite is red now:\n\n"
             "```\n{out}\n```\n\nPlease fix what broke.",
    "lint": "The tests pass but CI is still red: `ruff check src tests` reports:\n\n"
            "```\n{out}\n```\n\nThis project lints with `select = [\"ALL\"]`. Please fix it.",
}


# ------------------------------------------------------------------- setup --
def broken_state(repo, task, env):
    """That commit's tree, with the implementation reverted to its parent."""
    sh(["git", "checkout", "-q", "-f", task["sha"]], cwd=repo, env=env)
    sh(["git", "clean", "-qfd", "--", "src", "tests"], cwd=repo, env=env)
    for f in task["src"]:
        sh(["git", "checkout", task["parent"], "--", f], cwd=repo, env=env)


# Cortex's own files. Everything else in the training repository is structlog's.
HARNESS = (".evolve", ".claude", "CLAUDE.md", ".gitignore")


def training_state(repo, task, env):
    """broken_state() for the TRAINING repository, where the harness must persist.

    Each task lives at its own commit, so the code jumps through structlog's history
    from one session to the next. broken_state() jumps with `git checkout -f`, and
    in the training repository that took Cortex with it: config, harvested tasks,
    lessons, evolved items and CLAUDE.md are committed on OUR branch, upstream
    commits do not contain them, and a checkout removes them. Every session would
    have started from an empty harness — the loop could never accumulate anything
    (found by replaying the setup on a clone before the run: `cortex status` read
    0 tasks, 0 lessons after the first jump).

    Here HEAD never moves: the code is restored from the task's commit, the harness
    from where the loop left it, and the implementation reverted to its parent —
    the same broken state mine-tasks.py validated, with the loop's memory intact.
    """
    prev = sh(["git", "rev-parse", "HEAD"], cwd=repo, env=env).stdout.strip()
    r = sh(["git", "restore", f"--source={task['sha']}", "--staged", "--worktree", "--", "."],
           cwd=repo, env=env)
    if r.returncode != 0:
        sys.exit(f"training_state {task['id']}: restore from {task['sha'][:8]} failed: {r.stderr[-300:]}")
    keep = [x for x in HARNESS
            if sh(["git", "cat-file", "-e", f"{prev}:{x}"], cwd=repo, env=env).returncode == 0]
    r = sh(["git", "restore", f"--source={prev}", "--staged", "--worktree", "--", *keep],
           cwd=repo, env=env)
    if r.returncode != 0:
        sys.exit(f"training_state {task['id']}: harness restore failed: {r.stderr[-300:]}")
    sh(["git", "clean", "-qfd", "--", "src", "tests"], cwd=repo, env=env)
    for f in task["src"]:
        sh(["git", "checkout", task["parent"], "--", f], cwd=repo, env=env)


def clone_selftest(env):
    """Prove it the way Cortex will use it: a fresh clone, no .venv, the check's own
    environment — `python3 -m pytest` must run, and `import structlog` must resolve
    INSIDE the clone. Setup stops here rather than let eight sessions harvest tasks
    that preflight would then quarantine."""
    import tempfile
    renv = json.loads((REPO / ".evolve" / "config.json").read_text()).get("rollout_env") or {}
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / "clone"
        sh(["git", "clone", "-q", str(REPO), str(w)], env=env)
        cenv = dict(os.environ, **{k: str(v) for k, v in renv.items()})
        where = sh(["python3", "-c", "import structlog, os; print(os.path.realpath(structlog.__file__))"],
                   cwd=str(w), env=cenv).stdout.strip()
        if not where.startswith(os.path.realpath(str(w))):
            sys.exit(f"in a clone, structlog imports from {where or 'nowhere'}, not the clone")
        t = sh(["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_utils.py"],
               cwd=str(w), env=cenv, timeout=300)
        if t.returncode != 0:
            sys.exit(f"in a clone, `python3 -m pytest` does not run: {(t.stdout + t.stderr)[-400:]}")
        want = ruff_pin(sh(["git", "rev-parse", "HEAD"], cwd=str(w)).stdout.strip())
        for cmd in (["ruff", "--version"], ["python3", "-m", "ruff", "--version"]):
            got = sh(cmd, cwd=str(w), env=cenv).stdout.strip()
            if not want or not got.endswith(want):
                sys.exit(f"in a clone, `{' '.join(cmd)}` gives {got!r}, not the pinned ruff {want}")
    log("  clone self-test: python3 -m pytest runs in a bare clone and imports the clone's structlog")
    log(f"  clone self-test: `ruff` and `python3 -m ruff` both run the pinned ruff {want}")


def cmd_setup(a):
    doc = json.loads(TASKS.read_text())
    tasks = doc["tasks"]
    RUN.mkdir(parents=True, exist_ok=True)
    env = env_for(Path(a.cortex).resolve(), a.jev)
    if REPO.exists() and a.force:
        shutil.rmtree(REPO)
    if not REPO.exists():
        log(f"cloning {doc['repo']} -> {REPO}")
        sh(["git", "clone", "-q", doc["repo"], str(REPO)], cwd=str(RUN), env=env, quiet=False)
        log("building its venv (installed against THIS clone, or every revert is invisible)")
        sh(["uv", "venv", str(REPO / ".venv"), "--python", "3.12", "-q"], quiet=False)
        sh(["uv", "pip", "install", "--python", py(REPO), "-q", "-e", str(REPO),
            *"pytest pytest-asyncio freezegun simplejson pretend rich better-exceptions "
             "twisted time-machine ruff".split()], quiet=False)
        where = sh([py(REPO), "-c", "import structlog,os;print(os.path.dirname(structlog.__file__))"]).stdout.strip()
        if str(REPO) not in where:
            sys.exit(f"the venv imports from {where}, not {REPO}")
        log(f"  imports resolve to {where}")
    if not (SANDBOX_VENV / "bin" / "python3").exists():
        log(f"building the sandbox Python (test tools only, no structlog) -> {SANDBOX_VENV}")
        sh(["uv", "venv", str(SANDBOX_VENV), "--python", "3.12", "-q"], quiet=False)
        sh(["uv", "pip", "install", "--python", str(SANDBOX_VENV / "bin" / "python"), "-q",
            *TEST_DEPS], quiet=False)
    pins = install_ruffs([doc["base"]] + [t["sha"] for t in tasks] + [t["parent"] for t in tasks])
    log(f"  ruff as the project pinned it: {', '.join(pins)} (dispatcher at {RUFF})")
    sh(["git", "checkout", "-q", "-f", doc["base"]], cwd=REPO, env=env)
    sh(["cortex", "init", str(REPO)], cwd=REPO, env=env, quiet=False)
    cfg = REPO / ".evolve" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    # Two fixes, both found before the run. The indent is the line's own: four spaces
    # in a file that uses two nest the key a level deeper, and `cortex config` refuses
    # (the gate testbed met this once). And the model is pinned WHATEVER its value:
    # `cortex init` writes `model: ""`, which this used to skip because it matched only
    # a line already containing "claude" — and "" means "whatever the CLI defaults to",
    # which on this machine is set by the operator's interactive `/model` (it read
    # "opus" when checked). Every structlog sweep would have run on that model.
    out, block = [], None
    for line in text.splitlines():
        st = line.strip()
        ind = line[:len(line) - len(line.lstrip())]
        if line and not line[0].isspace() and st.endswith(":"):
            block = st[:-1]
        if st.startswith("sandbox_root:"):
            out.append(f"{ind}sandbox_root: {RUN / 'sandbox'}   # this run only")
        elif st.startswith("rollout_env:"):
            out.append(line)
            sub = ind + "  "
            out.append(f'{sub}PATH: "{sandbox_path()}"   # the sandbox Python first (see SANDBOX_VENV)')
            out.append(f'{sub}PYTHONPATH: "src"                # the clone\'s own structlog')
            out.append(f'{sub}DISABLE_AUTOUPDATER: "1"')
        elif st.startswith("model:") and block == "baseline":
            out.append(f"{ind}model: {MODEL}   # pinned: the programme's rollout model")
        else:
            out.append(line)
    cfg.write_text("\n".join(out) + "\n", encoding="utf-8")
    if sh(["cortex", "config"], cwd=REPO, env=env, quiet=False).returncode != 0:
        sys.exit("cortex config refused the edited config.yaml")
    compiled = json.loads((REPO / ".evolve" / "config.json").read_text())
    if compiled.get("model") != MODEL:
        sys.exit(f"the rollout model is {compiled.get('model')!r}, not {MODEL}: refusing to train")
    renv = compiled.get("rollout_env") or {}
    if not str(renv.get("PATH", "")).startswith(str(SANDBOX_VENV)) or renv.get("PYTHONPATH") != "src":
        sys.exit(f"rollout_env did not compile as intended: {renv}")
    log(f"  config: model {compiled.get('model')} · sandbox {RUN / 'sandbox'} · rollout_env PATH+PYTHONPATH")
    clone_selftest(env)
    sh(["git", "add", "-A"], cwd=REPO, env=env)
    sh(["git", "commit", "-q", "-m", "Cortex: init"], cwd=REPO, env=env)

    # Sessions run in the order a developer lived them, oldest commit first, so the
    # harness is carried forward in time and then tested on the four newest commits.
    # (The mined order was newest first; the selection rule fixes the split, not the order, and no
    # session had run when this was set.)
    def when(t):
        return sh(["git", "log", "-1", "--format=%ct", t["sha"]], cwd=REPO, env=env).stdout.strip()
    train = sorted((t for t in tasks if t["id"] not in HOLDOUT), key=when)
    split = {"train": [t["id"] for t in train],
             "holdout": [t["id"] for t in tasks if t["id"] in HOLDOUT],
             "train_order": "chronological, oldest commit first"}
    (RUN / "split.json").write_text(json.dumps(
        {"rule": "temporal: the four NEWEST mined commits are the holdout, the older "
                 "eight train. Training on the past and testing on the future is the "
                 "split that cannot leak. Fixed before the first session.",
         **split, "base": doc["base"], "repo": doc["repo"],
         "at": datetime.now().isoformat(timespec="seconds")}, indent=1) + "\n")
    log(f"train {split['train']}\nholdout {split['holdout']}")
    (RUN / "manifest.json").write_text(json.dumps(
        {"run": "X1", "kind": "external", "repo": str(REPO), "source": doc["repo"],
         "base": doc["base"], "cortex_home": str(Path(a.cortex).resolve()),
         "cortex_tag": sh(["git", "describe", "--tags", "--always"],
                          cwd=Path(a.cortex)).stdout.strip(),
         "model": MODEL, "jev": a.jev, "control": False,
         "created": datetime.now().isoformat(timespec="seconds")}, indent=1) + "\n")


# ------------------------------------------------------------------- train --
def turn(prompt, repo, env, resume=None, what="", timeout=900):
    cmd = ["claude", "--model", MODEL, "--permission-mode", "bypassPermissions",
           "--output-format", "json", "--max-turns", "40"]
    if resume:
        cmd += ["--resume", resume]
    cmd += ["--disallowedTools", *DENY, "-p", prompt]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                           timeout=timeout, env=env)
        out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        rc = p.returncode
    except subprocess.TimeoutExpired:
        out, rc = {}, 124
    res = {"what": what, "rc": rc, "session": out.get("session_id") or resume,
           "cost": out.get("total_cost_usd"), "turns": out.get("num_turns"),
           "secs": round(time.time() - t0), "result": (out.get("result") or "")[-600:]}
    with open(RUN / "turns.json", "a") as fh:
        fh.write(json.dumps({**res, "t": datetime.now().isoformat(timespec="seconds")}) + "\n")
    log(f"   turn {what}: {res['secs']}s ${res['cost']} rc={rc}")
    return res


def cmd_train(a):
    doc = json.loads(TASKS.read_text())
    split = json.loads((RUN / "split.json").read_text())
    by_id = {t["id"]: t for t in doc["tasks"]}
    env = env_for(Path(json.loads((RUN / "manifest.json").read_text())["cortex_home"]), a.jev)
    state_file = RUN / "state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}

    for tid in split["train"]:
        if state.get(tid, {}).get("status") == "done":
            log(f"{tid}: already done")
            continue
        task = by_id[tid]
        log(f"{tid} {task['title'][:70]}")
        training_state(REPO, task, env)
        sh(["git", "add", "-A"], cwd=REPO, env=env)
        sh(["git", "commit", "-q", "-m", f"{tid}: the state the user found"], cwd=REPO, env=env)
        base = sh(["git", "rev-parse", "HEAD"], cwd=REPO, env=env).stdout.strip()

        t = turn(task["prompt"], str(REPO), env, what=f"{tid} prompt")
        sess = t["session"]
        verdicts = []
        for i in range(MAX_CORRECTIONS + 1):
            v, out = check(REPO, task)
            verdicts.append(v)
            log(f"   check: {v}")
            if v == "ok" or i == MAX_CORRECTIONS:
                break
            t = turn(CORRECTION[v].format(tests=" ".join(task["tests"]), out=out),
                     str(REPO), env, resume=sess, what=f"{tid} correction {v}")
        if verdicts[-1] != "ok":
            log(f"FINDING {tid}: still '{verdicts[-1]}' after {MAX_CORRECTIONS} corrections")
        turn("/harvest", str(REPO), env, resume=sess, what=f"{tid} /harvest")
        sh(["git", "add", "-A"], cwd=REPO, env=env)
        sh(["git", "commit", "-q", "-m", f"{tid}: {task['title'][:60]}"], cwd=REPO, env=env)
        state[tid] = {"status": "done", "verdicts": verdicts, "base": base,
                      "corrections": sum(1 for v in verdicts[:-1] if v != "ok"),
                      "tasks_after": sorted(p.name for p in (REPO / ".evolve" / "tasks").glob("*")
                                            if p.is_dir() and p.name[0].isdigit())}
        state_file.write_text(json.dumps(state, indent=1) + "\n")

        # /evolve after every session, exactly as the lab's autopilot does: it
        # stops itself with BARREN when nothing recurs yet
        for n in range(8):
            while (REPO / ".evolve" / "runs" / ".lock").exists() and \
                    subprocess.run(["flock", "-n", str(REPO / ".evolve/runs/.lock"), "true"]).returncode != 0:
                time.sleep(20)
            before = sorted((REPO / ".evolve" / "candidate").glob("*"))
            r = turn("/evolve", str(REPO), env, what=f"{tid} /evolve #{n + 1}")
            time.sleep(4)
            text = (r["result"] or "").lower()
            if "barren" in text or "nothing to learn" in text:
                log(f"   /evolve: BARREN")
                break
            after = sorted((REPO / ".evolve" / "candidate").glob("*"))
            if not after and before:
                break
            if "keep" in text or "kill" in text:
                break
        sh(["git", "add", "-A"], cwd=REPO, env=env)
        sh(["git", "commit", "-q", "-m", f"cortex: after {tid}"], cwd=REPO, env=env, quiet=True)
    log("training finished")


# ------------------------------------------------------------------- bench --
def harness_dir(root, arm, env):
    h = root / arm
    shutil.rmtree(h, ignore_errors=True)
    (h / "skills").mkdir(parents=True)
    (h / "rules").mkdir(parents=True)
    if arm == "evolved":
        for d in ("skills", "rules"):
            s = REPO / ".claude" / d
            if s.is_dir():
                shutil.copytree(s, h / d, dirs_exist_ok=True)
        shutil.copy2(REPO / "CLAUDE.md", h / "CLAUDE.md")
    else:
        first = sh(["git", "log", "--reverse", "--format=%H", "--", "CLAUDE.md"],
                   cwd=REPO, env=env).stdout.split()
        text = sh(["git", "show", f"{first[0]}:CLAUDE.md"], cwd=REPO, env=env).stdout \
            if first else "# structlog\n"
        (h / "CLAUDE.md").write_text(text.rstrip("\n") + "\n")   # `git show` already ends in one
    return h


def cmd_bench(a):
    doc = json.loads(TASKS.read_text())
    split = json.loads((RUN / "split.json").read_text())
    by_id = {t["id"]: t for t in doc["tasks"]}
    env = env_for(Path(json.loads((RUN / "manifest.json").read_text())["cortex_home"]), a.jev)
    arms = [x for x in a.arms.split(",") if x]
    root = RUN / "sandbox" / "harness"
    hs = {arm: harness_dir(root, arm, env) for arm in arms}
    results = RUN / "bench.jsonl"
    done = set()
    if results.exists():
        for line in results.read_text().splitlines():
            r = json.loads(line)
            if r.get("valid", 1):          # one that could not run is measured again
                done.add((r["task"], r["arm"], r["r"]))

    jobs = [(tid, arm, r) for tid in split["holdout"] for r in range(1, a.k + 1)
            for arm in arms if (tid, arm, r) not in done]
    if not jobs:
        log("bench: nothing left to run")
        return
    log(f"bench: {len(jobs)} rollouts, {a.jobs} at a time")
    q = queue.Queue()
    for j in jobs:
        q.put(j)
    lock = threading.Lock()

    def sandbox(k):
        w = RUN / "sandbox" / f"work-{k}"
        if not (w / ".git").exists():
            shutil.rmtree(w, ignore_errors=True)
            sh(["git", "clone", "-q", str(REPO), str(w)], cwd=str(RUN), env=env)
            sh(["uv", "venv", str(w / ".venv"), "--python", "3.12", "-q"])
            sh(["uv", "pip", "install", "--python", py(w), "-q", "-e", str(w),
                *"pytest pytest-asyncio freezegun simplejson pretend rich "
                 "better-exceptions twisted time-machine ruff".split()])
        return w

    def one(k, tid, arm, r):
        w = sandbox(k)
        task = by_id[tid]
        sh(["git", "fetch", "-q", str(REPO), "+refs/heads/*:refs/remotes/src/*"], cwd=w, env=env)
        broken_state(w, task, env)
        for d in ("skills", "rules"):
            shutil.rmtree(w / ".claude" / d, ignore_errors=True)
            shutil.copytree(hs[arm] / d, w / ".claude" / d)
        shutil.copy2(hs[arm] / "CLAUDE.md", w / "CLAUDE.md")
        t0 = time.time()
        try:
            p = subprocess.run(["claude", "-p", task["prompt"], "--output-format", "json",
                                "--permission-mode", "acceptEdits", "--model", MODEL],
                               cwd=w, capture_output=True, text=True, timeout=900, env=env)
            out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
            rc = p.returncode
        except (subprocess.TimeoutExpired, ValueError):
            out, rc = {}, 124
        v, _ = check(w, task)
        row = {"run": "X1", "repo": "hynek/structlog", "task": tid, "arm": arm, "r": r,
               "split": "holdout", "family": "external",
               "pass": int(v == "ok"), "verdict": v, "valid": int(rc in (0, 124)),
               "rc": rc, "secs": round(time.time() - t0),
               "cost_usd": out.get("total_cost_usd"), "turns": out.get("num_turns"),
               "t": datetime.now().isoformat(timespec="seconds")}
        with lock:
            with open(results, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            log(f"  {tid} {arm:8} r{r} -> {'PASS' if row['pass'] else 'fail ' + v} "
                f"({row['secs']}s ${row['cost_usd']})")

    def worker(k):
        while True:
            try:
                tid, arm, r = q.get_nowait()
            except queue.Empty:
                return
            try:
                one(k, tid, arm, r)
            except Exception as ex:                        # noqa: BLE001
                with lock:
                    log(f"  {tid} {arm} r{r} DID NOT RUN: {type(ex).__name__}: {ex}")

    ts = [threading.Thread(target=worker, args=(k,), daemon=True) for k in range(1, a.jobs + 1)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    log("bench finished")


def cmd_export(a):
    rows = [json.loads(l) for l in (RUN / "bench.jsonl").read_text().splitlines()] \
        if (RUN / "bench.jsonl").exists() else []
    per = {}
    for r in rows:
        if not r["valid"]:
            continue
        k = (r["task"], r["arm"])
        d = per.setdefault(k, {"passed": 0, "n": 0})
        d["passed"] += r["pass"]
        d["n"] += 1
    # Did the loop change the harness at all? If `evolved` is byte-identical to `none`
    # the benchmark is an A/A, and no difference it shows can be the loop's.
    import filecmp
    root = RUN / "sandbox" / "harness"
    def same(a, b):
        if not (a.exists() and b.exists()):
            return None
        c = filecmp.dircmp(a, b)
        # content, not bytes: the arm builder once wrote the base CLAUDE.md with one extra
        # trailing newline, which made two identical harnesses compare as different
        text_same = all((a / f).read_text(errors="replace").rstrip() ==
                        (b / f).read_text(errors="replace").rstrip() for f in c.diff_files)
        return not (c.left_only or c.right_only or c.funny_files) and text_same and \
            all(same(a / d, b / d) for d in c.common_dirs)
    identical = same(root / "none", root / "evolved")
    items = sorted(p.name for d in ("skills", "rules") for p in (REPO / ".claude" / d).glob("*")) \
        if (REPO / ".claude").is_dir() else []
    out = [{"run": "X1", "repo": "hynek/structlog", "task": t, "arm": arm, "split": "holdout",
            "passed": v["passed"], "n": v["n"], "rate": v["passed"] / v["n"] if v["n"] else 0,
            "harness_identical": identical, "evolved_items": items}
           for (t, arm), v in sorted(per.items())]
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "external.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in out), encoding="utf-8")
    # the raw rollouts go into the same file every other rollout lives in
    roll = DATA / "rollouts.jsonl"
    keep = [l for l in roll.read_text().splitlines() if '"run": "X1"' not in l] \
        if roll.exists() else []
    with open(roll, "w") as fh:
        for l in keep:
            fh.write(l + "\n")
        for r in rows:
            fh.write(json.dumps({**r, "source": "bench"}, sort_keys=True) + "\n")
    print(f"{len(out)} cells, {len(rows)} rollouts -> {DATA / 'external.jsonl'}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("setup", cmd_setup), ("train", cmd_train),
                     ("bench", cmd_bench), ("export", cmd_export)):
        p = sub.add_parser(name)
        p.add_argument("--cortex", default=str(CORTEX.parent / "cortex-eval-v1.0"))
        p.add_argument("--jev", default="off", choices=["off", "on"])
        p.add_argument("--force", action="store_true")
        if name == "bench":
            p.add_argument("--k", type=int, default=5)
            p.add_argument("--arms", default="none,evolved")
            p.add_argument("--jobs", type=int, default=6)
        p.set_defaults(func=fn)
    a = ap.parse_args()
    return a.func(a) or 0


if __name__ == "__main__":
    sys.exit(main())
