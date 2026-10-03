#!/usr/bin/env python3
"""mine-tasks.py — turn a real repository's own history into validated tasks.

  mine-tasks.py --repo .../structlog --base <sha> --want 12 [--out tasks.json]

The lab's tasks were written by the people who built the lab, which is the hardest
single attack on the whole paper: *"of course it works, you wrote the repository,
the house rules and the tasks."* The answer is to take a repository nobody here
built and let its own history write the tasks (the Skill Issue / SWE-smith
approach).

For each commit that changed both implementation and tests:

  broken state = that commit, with the IMPLEMENTATION reverted to its parent
                 (the tests stay at the commit — they are the specification)
  check        = exactly the test files that commit touched
  reference    = the commit's own implementation change

A task is kept only if all three hold, which is the same standard `lab validate`
applies to the lab's own scenarios:

  1. the check **fails** on the broken state — otherwise the task tests nothing;
  2. the check **passes** once the real implementation is restored — otherwise the
     task is unsolvable and would score zero in every arm;
  3. the rest of the suite still passes on the broken state — otherwise the task
     is entangled with an unrelated breakage.

The user's prompt is written from the commit subject and body **with the fix
removed**: it says what was wrong, never which lines to change. Where the commit
names a file, the name stays — a real user would say it.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def git(repo, *args, check=False):
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {p.stderr}")
    return p.stdout


def files_of(repo, sha):
    out = git(repo, "show", "--name-only", "--format=", sha).split()
    return [f for f in out if f.endswith(".py")]


def split_paths(files, src_dirs, test_dirs):
    src = [f for f in files if any(f.startswith(d) for d in src_dirs)]
    tst = [f for f in files if any(f.startswith(d) for d in test_dirs)]
    return src, tst


# Trailers, bullet lists, issue references, PR separators and review chatter. The
# test is not "is this line true" but "would a user say it": a user reports a
# symptom, they do not tell you which construct the linter prefers.
PROMPT_NOISE = re.compile(
    r"^(closes|fixes|refs|signed-off-by|co-authored-by|see |cc |\s*\*|\s*-\s|#\d"
    r"|-{3,}|={3,}|https?://|\[.*\]\(|the .* isn't specified|b/c |ruff |mypy |lint)", re.I)


def prompt_from(repo, sha, tests):
    """The user's words: the commit subject and the human half of its body, with
    trailers, bullet lists and issue references stripped. It must describe the
    problem; it must not describe the patch."""
    subject = git(repo, "log", "-1", "--format=%s", sha).strip()
    body = git(repo, "log", "-1", "--format=%b", sha).strip()
    lines = [l.strip() for l in body.splitlines()
             if l.strip() and not PROMPT_NOISE.match(l.strip())]
    # a conventional-commit prefix is noise to a user ("fix(processors): ...")
    subject = re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", subject)
    text = subject[0].upper() + subject[1:] if subject else ""
    if lines:
        text += ". " + " ".join(lines[:3])
    if not text.endswith("."):
        text += "."
    where = ", ".join(tests)
    return (f"{text} The tests for this are in {where} and they are failing. "
            f"Please fix it.")


def run_tests(venv, repo, paths, timeout=300):
    cmd = [str(venv), "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths]
    try:
        p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--venv", default=None, help="the python that runs its tests")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--want", type=int, default=12)
    ap.add_argument("--scan", type=int, default=400, help="commits to walk back")
    ap.add_argument("--src", default="src/")
    ap.add_argument("--tests", default="tests/")
    ap.add_argument("--out", default="tasks.json")
    ap.add_argument("--work", default=None)
    ap.add_argument("--build-venv", action="store_true",
                    help="build a venv installed against the WORK CLONE (almost always right)")
    ap.add_argument("--deps", default="pytest pytest-asyncio freezegun simplejson pretend "
                                      "rich better-exceptions twisted time-machine",
                    help="extra packages the repository's tests need")
    a = ap.parse_args()

    repo = Path(a.repo).resolve()
    venv = Path(a.venv or (repo / ".venv" / "bin" / "python")).resolve()
    work = Path(a.work or (repo.parent / f"{repo.name}-mine")).resolve()
    src_dirs, test_dirs = [a.src], [a.tests]
    base = git(repo, "rev-parse", a.base, check=True).strip()

    print(f"repo {repo}\nbase {base[:10]}\nwalking back {a.scan} commits for "
          f"({a.src}, {a.tests}) pairs")
    shas = git(repo, "log", "--format=%H", f"-{a.scan}", base).split()

    shutil.rmtree(work, ignore_errors=True)
    git(repo.parent, "clone", "-q", str(repo), str(work), check=True)

    # The venv must be installed against the WORK CLONE, not the original. An
    # editable install of the original shadows the clone's `src/` through its
    # import finder, so every revert this script makes has no effect on what
    # `import structlog` resolves to — and the first version of this script
    # rejected all 50 candidates for exactly that reason, with the reference fix
    # "failing" a check that was never running against it.
    if a.build_venv:
        wv = work / ".venv"
        print(f"  building a venv against the work clone: {wv}")
        subprocess.run(["uv", "venv", str(wv), "--python", "3.12", "-q"], check=True)
        subprocess.run(["uv", "pip", "install", "--python", str(wv / "bin" / "python"),
                        "-q", "-e", str(work), *a.deps.split()], check=True)
        venv = wv / "bin" / "python"
    # prove it: the clone's own source must be what the tests import
    check = subprocess.run([str(venv), "-c",
                            "import structlog,os;print(os.path.dirname(structlog.__file__))"],
                           capture_output=True, text=True)
    where = check.stdout.strip()
    if where and str(work) not in where:
        sys.exit(f"mine-tasks: the venv imports the package from {where}, not from the work "
                 f"clone {work}. Every revert would be invisible. Pass --build-venv.")
    print(f"  imports resolve to {where or '(unknown)'}")

    found, rejected = [], []
    for sha in shas:
        if len(found) >= a.want:
            break
        files = files_of(repo, sha)
        src, tst = split_paths(files, src_dirs, test_dirs)
        if not src or not tst:
            continue
        parent = git(repo, "rev-parse", f"{sha}^", check=False).strip()
        if not parent:
            continue
        short = f"{sha[:8]}"
        # the broken state: this commit, implementation reverted to the parent
        git(work, "checkout", "-q", "-f", sha)
        git(work, "clean", "-qfdx", "--", a.src, a.tests)
        ok = True
        for f in src:
            if subprocess.run(["git", "checkout", parent, "--", f], cwd=work,
                              capture_output=True).returncode != 0:
                ok = False
        if not ok:
            rejected.append({"sha": sha, "why": "the implementation does not exist in the parent"})
            continue
        t0 = time.time()
        rc_broken, out_broken = run_tests(venv, work, tst)
        if rc_broken == 0:
            rejected.append({"sha": sha, "why": "the check passes on the broken state"})
            continue
        if rc_broken == 124:
            rejected.append({"sha": sha, "why": "the check timed out"})
            continue
        # The REST of the suite must be unaffected, or the task is entangled with an
        # unrelated breakage. "The rest" excludes the task's own test files, which
        # are supposed to be red in the broken state — including them made every
        # mined task look entangled the first time this ran.
        rest = ["tests"] + [f"--ignore={t}" for t in tst]
        rc_rest, out_rest = run_tests(venv, work, rest, timeout=300)
        entangled = rc_rest != 0
        # the reference fix restores the real implementation
        git(work, "checkout", sha, "--", *src)
        rc_fixed, out_fixed = run_tests(venv, work, tst)
        secs = round(time.time() - t0)
        if rc_fixed != 0:
            rejected.append({"sha": sha, "why": "the reference fix does not pass the check"})
            continue
        found.append({
            "id": f"X{len(found) + 1:02d}", "sha": sha, "parent": parent,
            "title": git(repo, "log", "-1", "--format=%s", sha).strip()[:110],
            "prompt": prompt_from(repo, sha, tst),
            "src": src, "tests": tst,
            "check": f"python -m pytest -q {' '.join(tst)}",
            "broken_rc": rc_broken, "fixed_rc": rc_fixed,
            "suite_clean_on_broken": not entangled,
            "rest_tail": out_rest.strip().splitlines()[-1:],
            "secs": secs,
            "broken_tail": out_broken.strip().splitlines()[-1:],
        })
        print(f"  [{len(found):2}] {short} {found[-1]['title'][:62]:62} "
              f"{'' if not entangled else '(suite also red)'} {secs}s")

    git(work, "checkout", "-q", "-f", base)
    out = {"repo": str(repo), "base": base, "mined": len(found),
           "rejected": len(rejected), "want": a.want,
           "reject_reasons": rejected[:60], "tasks": found}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"\n{len(found)} valid task(s), {len(rejected)} rejected -> {a.out}")
    by = {}
    for r in rejected:
        by[r["why"]] = by.get(r["why"], 0) + 1
    for why, n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {n:4}  {why}")
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
