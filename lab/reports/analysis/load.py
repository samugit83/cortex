"""load.py — read `reports/data/` and answer the questions the tables ask of it.

One place knows where the rows live and what the columns mean. Everything above
this file takes lists of dicts and returns numbers, so a reader who wants to check
a table can read the table's code without first learning the directory layout.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent
# CORTEX_REPORT_DATA points the analysis at another copy of the rows — a reviewer's
# own, or a scratch set that exercises a section before its real data exists
DATA = Path(os.environ.get("CORTEX_REPORT_DATA") or REPORTS / "data")
CORTEX = REPORTS.parent.parent

FAMILIES = {"A": "user-visible change (CHANGELOG)", "B": "money (billing)",
            "C": "new exporter", "D": "control (plain bugs)", "E": "time (clock)"}
RULE_FAMILIES = ("A", "B", "C", "E")          # D is the control: it has no house rule
CORTEX_COMMANDS = ("harvest", "evolve", "prune")    # installed by `cortex init`, not the CLI's
ARM_ORDER = ("none", "none2", "evolved", "kitchen", "accept-all", "flat",
             "desc-only", "ideal", "swapped")


def rows(name):
    p = DATA / name
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


class Data:
    """Everything the report is allowed to know, loaded once."""

    def __init__(self):
        self.runs = rows("runs.jsonl")
        self.sessions = rows("sessions.jsonl")
        self.cycles = rows("cycles.jsonl")
        self.sweeps = rows("sweeps.jsonl")
        self.rollouts = rows("rollouts.jsonl")
        self.items = rows("items.jsonl")
        self.gates = rows("gates.jsonl")
        self.prune = rows("prune.jsonl")                        # the Haiku experiment (H10)
        self.prune_mc = rows("prune-model-change.jsonl")        # /prune under Sonnet (H14)
        self.scope = rows("scope.jsonl")
        self.external = rows("external.jsonl")
        # the prune passes' own rollouts (the export above records only their verdicts), and
        # what every rollout read through git, from Claude Code's own session records; both
        # made by analysis/extract_*.py from data that does not ship
        self.prune_sweeps = rows("prune-sweeps.jsonl")
        self.transcripts = rows("transcripts.jsonl")
        try:
            self.transcript_cover = json.loads((DATA / "transcripts-coverage.json").read_text())
        except (OSError, ValueError):
            self.transcript_cover = {}
        self._scored = None
        # the programme's MEASURED spend, per block, written by `usage-guard spend --json`:
        # the gate and prune testbeds, structlog and the Sonnet /prune pass have no
        # runs.jsonl row, so summing runs.jsonl missed a third of the money
        try:
            self.spend = json.loads((DATA / "spend.json").read_text())
        except (OSError, ValueError):
            self.spend = {}

    # ---- run selection ---------------------------------------------------
    def of_kind(self, *kinds):
        return [r for r in self.runs if r.get("kind") in kinds]

    @property
    def evaluation(self):
        """The runs a primary endpoint may use: evaluation runs, Jev off.

        The judge is never in a primary. A run that had one is excluded here rather
        than filtered out later, so a primary cannot accidentally include one.
        """
        return [r["run"] for r in self.of_kind("evaluation")
                if not (r.get("jev") or {}).get("enabled")]

    @property
    def control(self):
        return [r["run"] for r in self.of_kind("control")]

    @property
    def development(self):
        return [r["run"] for r in self.of_kind("development")]

    def remeasure_of(self, runs):
        """The re-measurements of these runs (D0R for D0), or the runs themselves.

        A re-measurement is the SAME harness benchmarked again with the replicates'
        tooling on the replicates' holdout (brief §4.4: "D0 re-measured on the
        expanded holdout"), so it is the like-for-like number wherever D0 is set
        against R1…Rn. D0's own benchmark — fifteen holdout tasks, the development
        tooling — stays D0's report. A re-measurement carries only benchmark rows;
        D0's sessions, cycles and items are D0's alone.
        """
        re_ = [r["run"] for r in self.of_kind("remeasure") if r.get("of") in runs]
        return re_ or list(runs)

    def same_harness(self, mc_runs):
        """The run whose harness a model-change run re-measures (R1), so that "the
        same harness's gain under each model" (brief §4.8) compares R1 with M1 — not
        M1 with the pooled replicates, which are four different harnesses."""
        of = [r.get("of") for r in self.runs if r["run"] in mc_runs and r.get("of")]
        return sorted(set(of)) or self.evaluation

    def code_only(self, split="holdout"):
        """The `none` arm on a CONTROL run's final code.

        The control wrote the same fixes with no harness at all, so this is what
        the code alone teaches — the thing an evaluation run's gain has to beat.
        It is not a harness comparison and is never pooled with one.
        """
        return self.bench(runs=self.control, arms=("none",), split=split)

    def bench(self, runs=None, arms=None, split=None, valid_only=True):
        out = [r for r in self.rollouts if r.get("source") == "bench"]
        if valid_only:
            out = [r for r in out if r.get("valid")]
        if runs is not None:
            out = [r for r in out if r["run"] in runs]
        if arms is not None:
            out = [r for r in out if r.get("arm") in arms]
        if split is not None:
            out = [r for r in out if r.get("split") == split]
        return out

    # ---- the exclusion rule, applied in one place ------------------------
    def complete_case_tasks(self, runs, arms=("none", "evolved"), split="holdout"):
        """The tasks measured in EVERY one of `runs`, under every arm in `arms`.

        `PREREGISTRATION.md` §5.1 makes this the primary set and the all-valid set
        the secondary one, decided before any run existed — so that a task dropping
        out of one run cannot quietly change what "the holdout" means.
        """
        seen = defaultdict(set)
        for r in self.bench(runs=runs, arms=arms, split=split):
            seen[(r["run"], r["arm"])].add(r["task"])
        need = [(run, arm) for run in runs for arm in arms]
        if not need or any(k not in seen for k in need):
            return sorted(set.intersection(*seen.values())) if seen else []
        return sorted(set.intersection(*(seen[k] for k in need)))

    def excluded(self):
        """Per run: the holdout scenarios excluded before its benchmark, and why."""
        out = {}
        for r in self.runs:
            if isinstance(r.get("excluded"), dict):          # shipped in the row itself
                out[r["run"]] = r["excluded"]
                continue
            p = Path(r.get("repo", "")).parent / "excluded.json"
            if p.is_file():
                try:
                    out[r["run"]] = json.loads(p.read_text())
                except ValueError:
                    pass
        return out

    # ---- firing ----------------------------------------------------------
    def firing(self, run, arm="evolved", split=None):
        """{item: {"visible": n, "fired": n, "by_family": {...}, "rollouts": n}}"""
        sel = self.bench(runs=[run], arms=[arm], split=split)
        per_family = defaultdict(int)
        for r in sel:
            per_family[r["family"]] += 1
        out = defaultdict(lambda: {"visible": 0, "fired": 0,
                                   "by_family": defaultdict(lambda: {"visible": 0, "fired": 0}),
                                   "rollouts": 0})
        for r in sel:
            for name in (r.get("visible") or []):
                out[name]["visible"] += 1
                out[name]["by_family"][r["family"]]["visible"] += 1
            for name in set((r.get("fired") or []) + (r.get("rules") or [])):
                out[name]["fired"] += 1
                out[name]["by_family"][r["family"]]["fired"] += 1
        for name in out:
            out[name]["rollouts"] = len(sel)
            # `rollouts` per family is the denominator the tier rubric's third
            # criterion asks for: "its fire rate ON ITS OWN FAMILY'S ROLLOUTS". Divided
            # by `visible` instead, a rule scores 1.00 everywhere it loads — a rule is
            # never chosen, so fired-given-visible is 1 by construction and the
            # criterion could not distinguish anything.
            for fam, n in per_family.items():
                out[name]["by_family"].setdefault(fam, {"visible": 0, "fired": 0})
                out[name]["by_family"][fam]["rollouts"] = n
            out[name]["by_family"] = {k: dict(v) for k, v in out[name]["by_family"].items()}
        return {k: dict(v) for k, v in out.items()}

    def foreign_skills(self, arms=("none", "evolved")):
        """Skills the agent invoked that no harness in the programme ever contained.

        They are not the lab's and not the user's: `run`, `update-config` and
        `fewer-permission-prompts` ship inside the pinned Claude Code binary, so they
        are available in every arm of every rollout. What matters is whether reaching
        for them differs by arm. Returns {"names": {name: rollouts}, "by_arm": {arm:
        (rollouts invoking one, rollouts)}} over the primary arms' valid bench rows.
        """
        harness = {i.get("name") for i in self.items}
        for r in self.rollouts:
            harness |= set(r.get("visible") or []) | set(r.get("rules") or [])
        # Cortex's own commands (`cortex init` installs them in every repository) are not
        # the CLI's: they are counted apart, in `own`
        harness |= set(CORTEX_COMMANDS)
        names, by_arm = defaultdict(int), {a: [0, 0] for a in arms}
        own = defaultdict(int)
        # the evaluation runs only: Sonnet's and structlog's rollouts run other models
        # and another repository, and are never pooled with these
        for r in self.bench(runs=self.evaluation, arms=arms):
            f = set(r.get("fired") or []) - harness
            for n in set(r.get("fired") or []) & set(CORTEX_COMMANDS):
                own[n] += 1
            by_arm[r["arm"]][1] += 1
            if f:
                by_arm[r["arm"]][0] += 1
                for n in f:
                    names[n] += 1
        return {"names": dict(sorted(names.items(), key=lambda kv: -kv[1])),
                "by_arm": {a: tuple(v) for a, v in by_arm.items()}, "own": dict(own)}

    # ---- score.sh's own verdicts ------------------------------------------
    def scored(self):
        """Every candidate the evaluation runs swept, with the verdict score.sh gives it
        when its rules are applied again to the recorded rollouts (rescore.py), keyed by
        (run, name). The journals are written by the model that runs /evolve; where the
        two differ, the report states the scorer's verdict and the journal's beside it."""
        if self._scored is None:
            import rescore
            self._scored = {(c["run"], c["name"]): c for c in rescore.candidates()}
        return self._scored

    def journal_fate(self, run, name):
        """A candidate's fate as its run's journal records it (the development run has no
        re-scored sweeps): `kept`, `killed-regression` (gate 2 or 3 among the gates it
        records), `killed` (other gates), `killed (no gate recorded)`, or None."""
        cs = [c for c in self.cycles if c["run"] == run and c.get("name") in (name, f"{name} (re-tested)")
              and c.get("verdict") in ("KEEP", "KILL")]
        if not cs:
            return None
        c = cs[-1]
        if c["verdict"] == "KEEP":
            return "kept"
        g = {str(x) for x in (c.get("gates_failed") or [])}
        if not g:
            return "killed (no gate recorded)"
        return "killed-regression" if g & {"2", "3"} else "killed"

    def rule_fate(self, run, name):
        """`kept`, `killed-regression` (gate 2 or 3 in the confirm), `killed` (any other
        gate), or `unscored` (score.sh returned RERUN and never decided); None where the
        rules have no sweep of it, as in the development run."""
        c = self.scored().get((run, name))
        if not c:
            return None
        if c["verdict"] == "KEEP":
            return "kept"
        if c["verdict"] == "KILL":
            conf = [s for s in c["sweeps"] if s["phase"] == "confirm"]
            return ("killed-regression" if conf and {"gate2", "gate3"} & set(conf[-1]["failed"])
                    else "killed")
        return "unscored"

    def kept(self, run):
        return [i for i in self.items if i["run"] == run and i["fate"] == "kept"]

    def buried(self, run):
        return [i for i in self.items if i["run"] == run and i["fate"] == "buried"]

    def arms_of(self, run):
        r = next((x for x in self.runs if x["run"] == run), None)
        return (r or {}).get("arms") or {}

    def arm_meta(self, runs, arm, key=None):
        """An arm's recorded metadata from whichever run actually has it.

        Asking `runs[0]` was wrong twice over: the order in runs.jsonl is export
        order, not run order, and an arm only exists on the runs that measured it.
        Looking it up positionally silently returned None and printed
        "always-on None → None chars" in a hypothesis verdict.
        """
        for run in runs:
            v = (self.arms_of(run) or {}).get(arm)
            if v:
                return v.get(key) if key else v
        return None if key else {}


def z(x):
    """An exact tie is +0, not -0: float summation leaves -1e-17 behind, and "-0.0
    points" reads as a (tiny) loss. Only values that are zero to 12 places change."""
    return x if x != x else round(x, 12) + 0.0


def pct(x, nan="—"):
    return nan if x != x else f"{x * 100:.0f}%"


def signed(x, nan="—"):
    return nan if x != x else f"{z(x) * 100:+.0f}"


def ci(lo, hi):
    return "—" if lo != lo or hi != hi else f"[{z(lo) * 100:+.0f}, {z(hi) * 100:+.0f}]"


def table(path, title, header, body_rows, note=None):
    """Write one table as Markdown AND as CSV, from one list of rows, so the two
    can never disagree."""
    import csv
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    md = [f"# {title}", ""]
    if note:
        md += [note, ""]
    md.append("| " + " | ".join(header) + " |")
    md.append("|" + "---|" * len(header))
    for r in body_rows:
        md.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    path.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with open(path.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in body_rows:
            w.writerow(["" if c is None else c for c in r])
    return path.with_suffix(".md")
