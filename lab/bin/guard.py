"""guard — refuse to write to the finished development run.

D0 (`cortex-lab` and `lab/state/state.json`) is evidence, not a workspace: every
number in the report's development-run column comes from it, and a single
`lab build --force` or stray `autopilot` would destroy it silently. §3.1 of the
brief therefore asks that the tools refuse to run against it at all.

The protected paths are listed in `lab/D0-PROTECTED.txt`, in Cortex — never in
the lab repository itself, so that switching the guard on leaves D0 byte for byte
as the development run ended. Lines are absolute paths (`~` allowed); blank lines
and `#` comments are ignored.

A tool calls `protect(path, what)` before anything that writes. The escape hatch
is deliberate and loud: `LAB_ALLOW_D0=1`, which the report must record as a
deviation if it is ever used.
"""
import os
import sys
from pathlib import Path

LIST = Path(__file__).resolve().parent.parent / "D0-PROTECTED.txt"
ALLOW = "LAB_ALLOW_D0"


def protected_paths():
    if not LIST.exists():
        return []
    out = []
    for line in LIST.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(Path(os.path.expanduser(line)))
    return out


def _resolve(p):
    """The path as it will be written to, whether or not it exists yet."""
    p = Path(os.path.expanduser(str(p)))
    try:
        return p.resolve()
    except (OSError, RuntimeError):
        return p.absolute()


def is_protected(path):
    """The protected path this one falls under, or None.

    Both directions count. A tool writing *into* a protected directory is the
    obvious case; a tool writing the protected file itself is the same thing one
    level up. A sibling whose name merely starts with the same characters
    (`cortex-lab-R1` beside `cortex-lab`) is NOT protected — that is the whole
    point of the isolated copies, so the comparison is on path parts.
    """
    target = _resolve(path)
    for prot in protected_paths():
        p = _resolve(prot)
        if target == p or p in target.parents:
            return p
    return None


def protect(path, what="write"):
    """Stop, unless the operator has said out loud that they mean it."""
    hit = is_protected(path)
    if hit is None:
        return
    if os.environ.get(ALLOW) == "1":
        print(f"lab: {ALLOW}=1 — allowing {what} on protected {hit} "
              f"(record this in DEVIATIONS.md)", file=sys.stderr)
        return
    sys.exit(
        f"lab: refusing to {what} {path}\n"
        f"  It is under {hit}, which is the finished development run D0 and is\n"
        f"  evidence for the report. Point the tools somewhere else:\n"
        f"    LAB_REPO=.../cortex-lab-R1 LAB_STATE=.../R1/state.json BENCH_OUT=.../R1/bench\n"
        f"  If you really mean to write to D0, set {ALLOW}=1 and say so in DEVIATIONS.md.")
