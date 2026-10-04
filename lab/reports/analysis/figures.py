"""figures.py — F1…F19, PNG at 300 dpi and SVG, from `reports/data/` only.

Three rules, applied everywhere:

* **readable in grayscale.** Colour never carries meaning on its own: every series
  also differs in marker, hatch or line style, because a printed paper is grey.
* **n in every caption.** A figure that does not say how much data it rests on
  invites the reader to assume more than there is.
* **a figure with no data says so** on its own face, rather than being silently
  absent from the report.
"""
from __future__ import annotations

from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
import numpy as np                                   # noqa: E402

import stats as S                                    # noqa: E402
from load import ARM_ORDER, FAMILIES, RULE_FAMILIES  # noqa: E402

FIGURES = None            # set by rebuild.py

# A grayscale-safe sequence: distinct in lightness as well as in hue, and paired
# with a marker and a hatch so that neither channel is load-bearing on its own.
INK = ["#1b1b1b", "#5a5a5a", "#8f8f8f", "#b9b9b9", "#dcdcdc"]
ARM_STYLE = {
    "none":       dict(color="#c9c9c9", hatch="",    marker="o", ls="--"),
    "none2":      dict(color="#e0e0e0", hatch="..",  marker="v", ls=":"),
    "evolved":    dict(color="#2b2b2b", hatch="",    marker="s", ls="-"),
    "kitchen":    dict(color="#7a7a7a", hatch="//",  marker="^", ls="-."),
    "ideal":      dict(color="#4a4a4a", hatch="\\\\", marker="D", ls="-"),
    "accept-all": dict(color="#9a9a9a", hatch="xx",  marker="P", ls="--"),
    "flat":       dict(color="#6a6a6a", hatch="++",  marker="X", ls=":"),
    "desc-only":  dict(color="#3d3d3d", hatch="--",  marker="*", ls="-"),
    "swapped":    dict(color="#888888", hatch="oo",  marker="h", ls="-."),
}


def style(arm):
    return ARM_STYLE.get(arm, dict(color="#555555", hatch="", marker="o", ls="-"))


def save(fig, name, caption):
    # Below everything the axes occupy, tick labels included. At a fixed y=0.005 it
    # was printed over F1 and F2's two-line family labels.
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    y = min([ax.get_tightbbox(r).transformed(inv).y0 for ax in fig.axes if ax.get_visible()]
            or [0.02])
    fig.text(0.01, y - 0.015, caption, fontsize=7, color="#444444", va="top", wrap=True)
    # pdf for the paper: vector, with TrueType fonts (fonttype 42) embedded, which
    # arXiv and the publishers' checkers accept where Type 3 fonts are refused
    plt.rcParams["pdf.fonttype"] = 42
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIGURES / f"{name}.{ext}", dpi=300, bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)
    return FIGURES / f"{name}.png"


def runs_in(rows):
    """How many runs actually contributed these rows."""
    return len({r["run"] for r in rows})


def empty(name, title, why):
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.axis("off")
    ax.text(0.5, 0.6, title, ha="center", fontsize=12, weight="bold")
    ax.text(0.5, 0.35, why, ha="center", fontsize=9, color="#555555")
    return save(fig, name, "No data.")


def _setup(ax, title, ylabel=None, xlabel=None):
    ax.set_title(title, fontsize=11, loc="left")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", color="#eeeeee", lw=0.8)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------- F1 --
def f1_calibration(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, arms=("none",))
    if not rows:
        return empty("F1-calibration", "F1 · Calibration", "no `none` rollouts yet")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for i, split in enumerate(("train", "holdout")):
        vals, errs = [], [[], []]
        for f in "ABCDE":
            k, n, p = S.rate(rows, family=f, split=split)
            lo, hi = S.wilson(k, n)
            vals.append(p if n else 0)
            errs[0].append((p - lo) if n else 0)
            errs[1].append((hi - p) if n else 0)
        x = np.arange(5) + (i - 0.5) * 0.36
        ax.bar(x, vals, 0.34, yerr=errs, capsize=3, label=split,
               color=INK[i * 2], edgecolor="black", lw=0.6,
               hatch="" if i == 0 else "//")
    _setup(ax, "F1 · Without a harness: pass rate per family", "pass rate")
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{f}\n{FAMILIES[f].split(' (')[0]}" for f in "ABCDE"], fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2)
    n = len(rows)
    return save(fig, "F1-calibration",
                f"n = {n} valid `none` rollouts over {runs_in(rows)} run(s). Wilson intervals, "
                "which ignore that repeats of one task are correlated. D is the control family: "
                "it has no house rule and the agent is expected to pass it.")


# ---------------------------------------------------------------------- F2 --
def f2_headline(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, arms=("none", "evolved"), split="holdout")
    if not rows:
        return empty("F2-headline", "F2 · Headline", "no holdout rollouts yet")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for i, arm in enumerate(("none", "evolved")):
        st = style(arm)
        vals, errs = [], [[], []]
        for f in "ABCDE":
            k, n, p = S.rate(rows, family=f, arm=arm)
            lo, hi = S.wilson(k, n)
            vals.append(p if n else 0)
            errs[0].append((p - lo) if n else 0)
            errs[1].append((hi - p) if n else 0)
        x = np.arange(5) + (i - 0.5) * 0.36
        ax.bar(x, vals, 0.34, yerr=errs, capsize=3, label=arm, color=st["color"],
               edgecolor="black", lw=0.7, hatch=st["hatch"])
        # one dot per run, so a reader sees the spread and not only the mean
        for j, f in enumerate("ABCDE"):
            for run in runs:
                rs = [r for r in rows if r["family"] == f and r["arm"] == arm and r["run"] == run]
                if rs:
                    ax.plot(x[j], sum(r["pass"] for r in rs) / len(rs), st["marker"],
                            ms=4, mfc="white", mec="black", mew=0.7, zorder=5)
    _setup(ax, "F2 · Holdout pass rate by family, with and without what Cortex evolved",
           "pass rate on tasks never seen during evolution")
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{f}\n{FAMILIES[f].split(' (')[0]}" for f in "ABCDE"], fontsize=8)
    ax.set_ylim(0, 1.08)
    ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper center")
    ntask = len({r["task"] for r in rows})
    return save(fig, "F2-headline",
                f"n = {len(rows)} valid holdout rollouts over {ntask} tasks and {runs_in(rows)} run(s). "
                "Bars are pooled rollout rates with Wilson intervals (description); open markers "
                "are individual runs. The inference is the paired interval in T4, which resamples "
                "tasks and runs rather than rollouts.")


# ---------------------------------------------------------------------- F3 --
def f3_forest(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, arms=("none", "evolved"))
    if not rows:
        return empty("F3-forest", "F3 · Forest plot", "no rollouts yet")
    entries = []
    for split in ("holdout", "train"):
        for f in list("ABCDE") + [None]:
            fams = [f] if f else list(RULE_FAMILIES)
            cs = S.cells(rows, "none", "evolved", families=fams, split=split)
            if not cs:
                continue
            lo, hi, _ = S.two_way_bootstrap(cs)
            entries.append((f"{split} · {f or 'A+B+C+E'}", S.paired_mean(cs), lo, hi, split))
    # D0 on its own holdout, and D0 re-measured on the replicates' (D0R) when it
    # exists: the second is the like-for-like one, the first is what D0 reported
    for label, dev in (("D0 · own holdout · A+B+C+E", d.development),
                       ("D0 re-measured · holdout · A+B+C+E",
                        [r for r in d.remeasure_of(d.development) if r not in d.development])):
        if not dev:
            continue
        drows = d.bench(runs=dev, arms=("none", "evolved"))
        cs = S.cells(drows, "none", "evolved", families=list(RULE_FAMILIES), split="holdout")
        if cs:
            entries.append((label, S.paired_mean(cs), float("nan"), float("nan"), "D0"))
    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(entries) + 1.6))
    for i, (label, m, lo, hi, split) in enumerate(entries):
        y = len(entries) - i
        mark = "D" if split == "D0" else ("s" if split == "holdout" else "o")
        if lo == lo:
            ax.plot([lo, hi], [y, y], color="#333333", lw=1.4,
                    ls="-" if split == "holdout" else "--")
            ax.plot([lo, hi], [y, y], "|", color="#333333", ms=6)
        ax.plot(m, y, mark, color="black", ms=6,
                mfc="white" if split != "holdout" else "black")
    ax.axvline(0, color="#999999", lw=1, ls=":")
    ax.set_yticks(range(1, len(entries) + 1))
    ax.set_yticklabels([e[0] for e in reversed(entries)], fontsize=8)
    _setup(ax, "F3 · Paired difference, evolved − none", xlabel="percentage points")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(left=min(-0.1, min(e[2] for e in entries if e[2] == e[2]) - 0.05))
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:+.0f}"))
    return save(fig, "F3-forest",
                f"{len(entries)} comparisons over {runs_in(rows)} evaluation run(s). Intervals are the "
                "two-way (crossed) bootstrap over runs and tasks, 10,000 replicates. D0 is the "
                "development run and is marked separately because it is never pooled: it has one "
                "run, so no run-level interval exists for it.")


# ---------------------------------------------------------------------- F4 --
def f4_heatmap(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, split="holdout")
    if not rows:
        return empty("F4-heatmap", "F4 · Per-task heatmap", "no holdout rollouts yet")
    arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]
    tasks = sorted({r["task"] for r in rows}, key=lambda t: (t[1], t))
    grid = np.full((len(tasks), len(arms)), np.nan)
    for i, t in enumerate(tasks):
        for j, a in enumerate(arms):
            sel = [r for r in rows if r["task"] == t and r["arm"] == a]
            if sel:
                grid[i, j] = sum(r["pass"] for r in sel) / len(sel)
    fig, ax = plt.subplots(figsize=(1.1 * len(arms) + 2.5, 0.22 * len(tasks) + 1.8))
    im = ax.imshow(grid, cmap="Greys", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels(arms, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels(tasks, fontsize=6)
    for i in range(len(tasks)):
        for j in range(len(arms)):
            if grid[i, j] == grid[i, j]:
                ax.text(j, i, f"{grid[i, j]:.1f}".lstrip("0") or "0", ha="center", va="center",
                        fontsize=5.5, color="white" if grid[i, j] > 0.55 else "black")
    ax.set_title("F4 · Holdout tasks × arms (pass rate)", fontsize=11, loc="left")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).ax.tick_params(labelsize=7)
    return save(fig, "F4-heatmap",
                f"{len(tasks)} holdout tasks × {len(arms)} arms, pooled over {runs_in(rows)} run(s), "
                f"{len(rows)} valid rollouts. A blank cell was not measured.")


# ---------------------------------------------------------------------- F5 --
def f5_corrections(d):
    if not d.sessions:
        return empty("F5-corrections", "F5 · Corrections", "no sessions exported yet")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    groups = [("evaluation", d.evaluation, "-", "s"), ("control", d.control, "--", "o"),
              ("development (D0)", d.development, ":", "D")]
    n_any = 0
    for (label, runs, ls, mk), colour in zip(groups, INK):
        if not runs:
            continue
        per = defaultdict(list)
        for s in d.sessions:
            if s["run"] in runs and s.get("round"):
                per[s["round"]].append(s["corrections"])
        if not per:
            continue
        n_any += sum(len(v) for v in per.values())
        xs = sorted(per)
        ax.plot(xs, [np.mean(per[x]) for x in xs], ls, marker=mk, color=colour,
                label=f"{label} ({len(runs)} run(s))", lw=1.6, ms=5)
    if not n_any:
        return empty("F5-corrections", "F5 · Corrections", "no sessions with a round")
    _setup(ax, "F5 · Corrections per session, over the rounds", "corrections per session", "round")
    ax.legend(fontsize=8, frameon=False)
    ax.set_xticks(range(1, 11))
    return save(fig, "F5-corrections",
                f"n = {n_any} sessions. Each round's scenarios differ, so the curve is not a "
                "controlled comparison on its own: only the difference between the evaluation and "
                "control lines, on the SAME scenarios, is evidence for H4 (T9).")


# ---------------------------------------------------------------------- F6 --
def f6_items_over_rounds(d):
    if not d.cycles:
        return empty("F6-items", "F6 · Items kept", "no cycles exported yet")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    plotted = 0
    for run, colour in zip([r["run"] for r in d.runs], INK * 4):
        cs = [c for c in d.cycles if c["run"] == run and c.get("is_cycle")]
        if not cs:
            continue
        cs.sort(key=lambda c: c.get("journal_index", 0))
        keeps = np.cumsum([1 if c["verdict"] == "KEEP" else 0 for c in cs])
        ax.step(range(1, len(cs) + 1), keeps, where="post", lw=1.6, color=colour,
                ls=":" if run in d.development else "-", label=run)
        plotted += 1
    if not plotted:
        return empty("F6-items", "F6 · Items kept", "no counted cycles")
    _setup(ax, "F6 · Items kept, over the cycles", "items kept (cumulative)", "/evolve cycle")
    ax.legend(fontsize=8, frameon=False, ncol=3)
    return save(fig, "F6-items",
                f"{plotted} run(s). D0, the development run, is dotted. The x axis is cycles, not "
                "rounds: a round can contain several cycles or none.")


# ---------------------------------------------------------------------- F7 --
def f7_replicate_matrix(d):
    runs = [r["run"] for r in d.runs if r["kind"] in ("evaluation", "development")]
    if not runs:
        return empty("F7-replicate", "F7 · Replicate matrix", "no runs yet")
    from tables import _own_family
    grid = np.zeros((len(runs), 4))
    labels = np.full((len(runs), 4), "", dtype=object)
    for i, run in enumerate(runs):
        for it in d.kept(run):
            fam = _own_family(it["name"], d, run)
            if fam in RULE_FAMILIES:
                j = RULE_FAMILIES.index(fam)
                grid[i, j] = 1
                labels[i, j] = it["kind"][0].upper() + ("g" if it.get("paths") else "a")
    fig, ax = plt.subplots(figsize=(5.5, 0.5 * len(runs) + 2))
    ax.imshow(grid, cmap="Greys", vmin=0, vmax=1.6, aspect="auto")
    ax.set_xticks(range(4))
    ax.set_xticklabels([f"{f}\n{FAMILIES[f].split(' (')[0]}" for f in RULE_FAMILIES], fontsize=8)
    ax.set_yticks(range(len(runs)))
    ax.set_yticklabels(runs, fontsize=8)
    for i in range(len(runs)):
        for j in range(4):
            ax.text(j, i, labels[i, j] or "—", ha="center", va="center", fontsize=8,
                    color="white" if grid[i, j] else "#666666")
    ax.set_title("F7 · Which families each run learned", fontsize=11, loc="left")
    return save(fig, "F7-replicate",
                f"{len(runs)} run(s) × 4 rule families. A cell says the form that survived: "
                "`Sg` a gated skill, `Sa` an always-on skill, `Rg` a path-scoped rule, "
                "`Ra` a path-less rule, `—` nothing was kept. D is left out: nothing should be "
                "learned for the control family, and nothing was.")


# ---------------------------------------------------------------------- F8 --
def f8_cost_vs_rate(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, split="holdout")
    if not rows:
        return empty("F8-cost-vs-rate", "F8 · Always-on cost against pass rate", "no rollouts yet")
    fig, ax = plt.subplots(figsize=(7, 4))
    n = 0
    for arm in ARM_ORDER:
        sel = [r for r in rows if r["arm"] == arm and r["family"] in RULE_FAMILIES]
        if not sel:
            continue
        chars = None
        for run in runs:
            chars = (d.arms_of(run).get(arm) or {}).get("always_on_chars", chars)
        if chars is None:
            continue
        st = style(arm)
        p = sum(r["pass"] for r in sel) / len(sel)
        ax.plot(chars, p, st["marker"], ms=10, color=st["color"], mec="black", mew=0.8)
        ax.annotate(arm, (chars, p), textcoords="offset points", xytext=(7, 4), fontsize=8)
        n += len(sel)
    _setup(ax, "F8 · What a harness costs on every turn, against what it buys",
           "holdout pass rate, A+B+C+E", "always-on characters (CLAUDE.md + always-on items)")
    return save(fig, "F8-cost-vs-rate",
                f"n = {n} valid holdout rollouts on the rule families, over {runs_in(rows)} run(s). "
                "Up and to the left is better: the same pass rate for fewer characters in every "
                "single turn's context.")


# ---------------------------------------------------------------------- F9 --
def f9_firing(d):
    runs = d.evaluation or d.development
    names, grid = [], []
    for run in runs:
        for name, f in sorted(d.firing(run).items()):
            byf = f.get("by_family", {})
            row = []
            for fam in "ABCDE":
                v = byf.get(fam, {})
                row.append((v.get("fired", 0) / v["visible"]) if v.get("visible") else np.nan)
            names.append(f"{run} · {name}")
            grid.append(row)
    if not grid:
        return empty("F9-firing", "F9 · Firing heatmap", "no firing data yet")
    g = np.array(grid)
    fig, ax = plt.subplots(figsize=(6.5, 0.42 * len(names) + 2))
    im = ax.imshow(g, cmap="Greys", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{f}\n{FAMILIES[f].split(' (')[0]}" for f in "ABCDE"], fontsize=8)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7)
    for i in range(len(names)):
        for j in range(5):
            if g[i, j] == g[i, j]:
                ax.text(j, i, f"{g[i, j]:.0%}", ha="center", va="center", fontsize=6.5,
                        color="white" if g[i, j] > 0.55 else "black")
    ax.set_title("F9 · When an item was in context, how often it was used", fontsize=11, loc="left")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).ax.tick_params(labelsize=7)
    return save(fig, "F9-firing",
                f"{len(names)} item-run pairs. A blank cell means the item was never in context "
                "for that family. A rule is loaded rather than chosen, so its cells are 100 % "
                "wherever it is visible; a skill's cells are the description doing its work.")


# --------------------------------------------------------------------- F10 --
def f10_gates(d):
    if not d.gates:
        return empty("F10-gates", "F10 · Gate calibration", "the gate testbed has not run")
    kinds = sorted({g["type"] for g in d.gates})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8))
    # score.sh's own verdict (the confirm's where there was one): a RERUN decided nothing
    sv = lambda g: ((g.get("confirm") or {}).get("verdict") or (g.get("screen") or {}).get("verdict")
                    or g["verdict"])
    keep = np.array([sum(1 for g in d.gates if g["type"] == k and sv(g) == "KEEP") for k in kinds])
    kill = np.array([sum(1 for g in d.gates if g["type"] == k and sv(g) == "KILL") for k in kinds])
    rerun = np.array([sum(1 for g in d.gates if g["type"] == k and sv(g) == "RERUN") for k in kinds])
    x = np.arange(len(kinds))
    ax1.bar(x, keep, 0.6, label="KEEP", color="#2b2b2b", edgecolor="black", lw=0.6)
    ax1.bar(x, kill, 0.6, bottom=keep, label="KILL", color="#d8d8d8", edgecolor="black",
            lw=0.6, hatch="//")
    ax1.bar(x, rerun, 0.6, bottom=keep + kill, label="RERUN (not judged)", color="white",
            edgecolor="black", lw=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(kinds, rotation=20, ha="right", fontsize=8)
    _setup(ax1, "F10a · score.sh's verdict by candidate type", "candidates")
    ax1.legend(fontsize=8, frameon=False)
    net = [g.get("net_runs") for g in d.gates
           if g["type"].startswith("placebo") and isinstance(g.get("net_runs"), (int, float))]
    if net:
        ax2.hist(net, bins=12, color="#9a9a9a", edgecolor="black", lw=0.6)
        ax2.axvline(0, color="black", ls=":", lw=1)
    else:
        ax2.text(0.5, 0.5, "no net_runs recorded", ha="center", fontsize=9, color="#666666")
    _setup(ax2, "F10b · Placebos: measured net runs", "placebos", "net runs (gain − regression)")
    return save(fig, "F10-gates",
                f"n = {len(d.gates)} candidates with a known right answer. KEEP, KILL and RERUN "
                "are score.sh's verdicts; a RERUN means no task in the screen could show a gain, "
                "so no gate judged the candidate. No placebo was opened by the agent, so every "
                "placebo KILL is gate 5. T8 gives the rates with their exact intervals.")


# --------------------------------------------------------------------- F11 --
def f11_gain_vs_regression(d):
    """Every confirm sweep of the evaluation runs, scored again from its rollouts by
    score.sh's rules (rescore.py): the runs it gained and its worst drop on one task. The
    journals' own gain and regression figures are written by the /evolve agent and are
    not used."""
    pts = []
    for (run, name), c in d.scored().items():
        conf = [x for x in c["sweeps"] if x["phase"] == "confirm"]
        if conf:
            pts.append((conf[-1]["G"] * conf[-1]["k"], conf[-1]["D"], c["verdict"], run))
    if not pts:
        return empty("F11-gain-regression", "F11 · Gain against regression",
                     "no confirm sweep of an evaluation run has been recorded")
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for verdict, mk, col in (("KEEP", "o", "#1b1b1b"), ("KILL", "X", "#9a9a9a"),
                             ("RERUN", "s", "#ffffff")):
        sel = [p for p in pts if p[2] == verdict]
        if sel:
            ax.scatter([p[0] for p in sel], [p[1] for p in sel], marker=mk, s=70,
                       facecolor=col, edgecolor="black", lw=0.8, label=verdict, zorder=3)
    for x, y, _v, run in pts:
        ax.annotate(run, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=6.5,
                    color="#666666")
    ax.axhline(0.34, color="#666666", ls="--", lw=1)
    ax.annotate("regression tolerance 0.34", (ax.get_xlim()[0], 0.35), fontsize=7, color="#666666")
    _setup(ax, "F11 · Every confirm sweep: what it gained and what it broke",
           "worst drop on any single task", "gain, in runs")
    ax.legend(fontsize=8, frameon=False)
    return save(fig, "F11-gain-regression",
                f"n = {len(pts)} confirm sweeps of the evaluation runs, scored again from their "
                "rollouts by score.sh's rules. The dashed line is the pre-set tolerance: a drop "
                "above it on one task fails gate 2, however much the candidate gained. A drop of "
                "one run in three sits just below it; on a task the live harness never failed it "
                "fails gate 3, and a recheck then decides.")


# --------------------------------------------------------------------- F12 --
def f12_failure_taxonomy(d):
    runs = d.evaluation or d.development
    rows = [r for r in d.bench(runs=runs, split="holdout") if not r["pass"]]
    if not rows:
        return empty("F12-failures", "F12 · Failure taxonomy", "no failures to classify")
    arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]
    verdicts = sorted({r["verdict"] for r in rows if r.get("verdict")})
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bottom = np.zeros(len(arms))
    for i, v in enumerate(verdicts):
        vals = [sum(1 for r in rows if r["arm"] == a and r.get("verdict") == v) for a in arms]
        ax.bar(arms, vals, 0.62, bottom=bottom, label=v, color=INK[i % len(INK)],
               edgecolor="black", lw=0.6, hatch=["", "//", "..", "xx", "\\\\"][i % 5])
        bottom += np.array(vals, dtype=float)
    _setup(ax, "F12 · Why rollouts failed, per arm", "failed rollouts")
    ax.legend(fontsize=8, frameon=False, ncol=3)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    return save(fig, "F12-failures",
                f"n = {len(rows)} failed holdout rollouts over {runs_in(rows)} run(s). "
                "`tampered` means the rollout changed the test QA committed, which is the failure "
                "mode a harness is most likely to change: an agent that knows the house rule has "
                "less reason to bend the test.")


# --------------------------------------------------------------------- F13 --
def f13_noise(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, split="holdout")
    if not rows:
        return empty("F13-noise", "F13 · Noise", "no rollouts yet")
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))
    per = defaultdict(list)
    for r in rows:
        if r["arm"] == "none":
            per[(r["run"], r["task"])].append(r["pass"])
    spread = [sum(v) / len(v) for v in per.values() if len(v) > 1]
    axes[0].hist(spread, bins=np.linspace(0, 1, 11), color="#9a9a9a", edgecolor="black", lw=0.6)
    _setup(axes[0], "F13a · `none`: per-task pass rate", "tasks", "pass rate")

    cs = S.cells(rows, "none", "evolved", families=["D"], split="holdout")
    diffs = [b - a for _k, (_f, a, b, _na, _nb) in cs.items()]
    if diffs:
        axes[1].hist(diffs, bins=np.linspace(-1, 1, 17), color="#c9c9c9", edgecolor="black", lw=0.6)
        axes[1].axvline(0, color="black", ls=":", lw=1)
    _setup(axes[1], "F13b · family D: evolved − none, per task", "tasks", "difference")

    aa = S.cells(rows, "none", "none2", families=list("ABCDE"), split="holdout")
    if aa:
        lo, hi, draws = S.two_way_bootstrap(aa)
        axes[2].hist(draws, bins=40, color="#dcdcdc", edgecolor="black", lw=0.4)
        axes[2].axvline(0, color="black", ls=":", lw=1.2)
        axes[2].axvline(S.paired_mean(aa), color="black", lw=1.4)
        axes[2].set_xlabel(f"A/A: none2 − none\n{S.paired_mean(aa) * 100:+.1f} "
                           f"[{lo * 100:+.1f}, {hi * 100:+.1f}]", fontsize=8)
    else:
        axes[2].text(0.5, 0.5, "the A/A arm has not run", ha="center", fontsize=9, color="#666666")
    _setup(axes[2], "F13c · the A/A check", "bootstrap replicates")
    return save(fig, "F13-noise",
                f"{len(spread)} task-run cells in `none`; {len(diffs)} paired differences in "
                "family D; the A/A panel is 10,000 bootstrap replicates of two arms that are the "
                "same harness built by the same code. If that interval excludes zero, every other "
                "result here is suspect until it is explained.")


# --------------------------------------------------------------------- F14 --
def f14_cost(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, split="holdout")
    if not rows:
        return empty("F14-cost", "F14 · Cost per rollout", "no rollouts yet")
    arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]
    metrics = [("tokens", "tokens"), ("cost_usd", "$"), ("secs", "seconds"),
               ("turns", "turns"), ("tool_calls", "tool calls")]
    fig, axes = plt.subplots(1, len(metrics), figsize=(2.3 * len(metrics) + 1, 3.4))
    for ax, (key, label) in zip(axes, metrics):
        vals = []
        for a in arms:
            v = [r[key] for r in rows if r["arm"] == a and isinstance(r.get(key), (int, float))]
            vals.append(np.mean(v) if v else 0)
        ax.bar(arms, vals, 0.62, color=[style(a)["color"] for a in arms],
               edgecolor="black", lw=0.6)
        _setup(ax, label, None)
        plt.setp(ax.get_xticklabels(), rotation=60, ha="right", fontsize=7)
    fig.suptitle("F14 · What a rollout costs, per arm", fontsize=11, x=0.02, ha="left")
    have = sum(1 for r in rows if isinstance(r.get("turns"), int))
    return save(fig, "F14-cost",
                f"n = {len(rows)} holdout rollouts. Turns and tool calls exist for {have} of them: "
                "they were added with sweep row schema 3, so rollouts recorded before that carry "
                "no value and are left out of those two panels rather than counted as zero.")


# --------------------------------------------------------------------- F15 --
def f15_description(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs, arms=("none", "evolved", "desc-only"), split="holdout")
    if not any(r["arm"] == "desc-only" for r in rows):
        return empty("F15-description", "F15 · The description test",
                     "the `desc-only` arm has not run")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for i, arm in enumerate(("none", "desc-only", "evolved")):
        st = style(arm)
        vals = []
        for f in "ABCDE":
            _k, n, p = S.rate(rows, family=f, arm=arm)
            vals.append(p if n else 0)
        ax.bar(np.arange(5) + (i - 1) * 0.28, vals, 0.26, label=arm, color=st["color"],
               edgecolor="black", lw=0.7, hatch=st["hatch"])
    _setup(ax, "F15 · Does the description carry the effect?", "holdout pass rate")
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{f}\n{FAMILIES[f].split(' (')[0]}" for f in "ABCDE"], fontsize=8)
    ax.legend(fontsize=8, frameon=False, ncol=3)
    return save(fig, "F15-description",
                f"n = {len(rows)} holdout rollouts. `desc-only` keeps each skill's name, "
                "description and paths and replaces its body with neutral filler of about the "
                "same length. Whatever it recovers of `evolved`'s gain was never coming from the "
                "body.")


# --------------------------------------------------------------------- F16 --
def f16_model_change(d):
    mc = [r["run"] for r in d.of_kind("model-change")]
    if not mc:
        return empty("F16-model-change", "F16 · A stronger model",
                     "the model-change study has not run")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    src = d.same_harness(mc)
    for i, (label, runs) in enumerate(((f"Haiku 4.5 ({', '.join(src)}'s harness)", src),
                                       ("stronger model, same harness", mc))):
        rows = d.bench(runs=runs, arms=("none", "evolved"), split="holdout")
        vals = []
        for f in "ABCDE":
            cs = S.cells(rows, "none", "evolved", families=[f], split="holdout")
            vals.append(S.paired_mean(cs) if cs else 0)
        ax.bar(np.arange(5) + (i - 0.5) * 0.36, vals, 0.34, label=label, color=INK[i * 2],
               edgecolor="black", lw=0.7, hatch="" if i == 0 else "//")
    ax.axhline(0, color="#999999", lw=1)
    _setup(ax, "F16 · The same harness, two models", "paired gain, evolved − none")
    ax.set_xticks(range(5))
    ax.set_xticklabels(list("ABCDE"), fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    return save(fig, "F16-model-change",
                "The two models are never pooled. A smaller gain under the stronger model is the "
                "expected result — it may already follow some house rules — and is a finding, "
                "not a failure.")


# --------------------------------------------------------------------- F17 --
def f17_external(d):
    if not d.external:
        return empty("F17-external", "F17 · A repository we did not build",
                     "the second repository has not been run")
    arms = sorted({e["arm"] for e in d.external})
    fig, ax = plt.subplots(figsize=(6, 3.8))
    vals, errs = [], [[], []]
    for a in arms:
        k = sum(e.get("passed", 0) for e in d.external if e["arm"] == a)
        n = sum(e.get("n", 0) for e in d.external if e["arm"] == a)
        p = k / n if n else 0
        lo, hi = S.wilson(k, n)
        vals.append(p)
        errs[0].append(p - lo)
        errs[1].append(hi - p)
    ax.bar(arms, vals, 0.5, yerr=errs, capsize=4,
           color=[style(a)["color"] for a in arms], edgecolor="black", lw=0.7)
    _setup(ax, "F17 · Holdout pass rate on a repository nobody here built", "pass rate")
    ax.set_ylim(0, 1.05)
    n = sum(e.get("n", 0) for e in d.external)
    return save(fig, "F17-external",
                f"n = {n} rollouts over 4 holdout tasks mined from the repository's own history. "
                "Few tasks, one run, real-world noise: this is corroboration, not a second primary "
                "result, and it is never pooled with the lab.")


# --------------------------------------------------------------------- F18 --
def f18_scope(d):
    if not d.scope:
        return empty("F18-scope", "F18 · Scope prediction", "scope-replay has not been run")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    fates = {"kept": ("o", "#1b1b1b"), "killed-regression": ("X", "#9a9a9a"),
             "killed": ("s", "#c9c9c9"), "unscored": ("D", "#ffffff")}
    sc = [s for s in d.scope if s.get("run") in d.evaluation]
    for ax, key, title, floor in ((ax1, "relevance", "F18a · relevance (the judge)", 0.35),
                                  (ax2, "breadth", "F18b · glob breadth (the free control)", None)):
        n = 0
        for fate, (mk, col) in fates.items():
            xs = [s[key] for s in sc if d.rule_fate(s["run"], s["candidate"]) == fate
                  and isinstance(s.get(key), (int, float))]
            ys = list(range(len(xs)))
            if xs:
                ax.scatter(xs, np.arange(len(xs)) + 0.5, marker=mk, s=80, facecolor=col,
                           edgecolor="black", lw=0.8, label=fate)
                n += len(xs)
        if floor is not None:
            ax.axvline(floor, color="black", ls="--", lw=1.2)
            ax.annotate("relevance floor 0.35", (floor, 0.1), fontsize=7, rotation=90,
                        color="#444444")
        _setup(ax, title, None, key)
        ax.set_xlim(-0.05, 1.05)
        if not n:
            ax.text(0.5, 0.5, "not available", ha="center", fontsize=9, color="#666666")
    ax1.legend(fontsize=8, frameon=False)
    ax1.set_ylabel("candidates", fontsize=9)
    return save(fig, "F18-scope",
                f"n = {len(sc)} candidates of the evaluation runs, each with score.sh's verdict "
                "(the development run's are in T18). A prediction is computed from the "
                "candidate's own text and its run's task suite, never from the verdict. Breadth is "
                "on the right as the control: if it separates the fates too, the judge is "
                "unnecessary and that is the finding.")


# --------------------------------------------------------------------- F19 --
def f19_trigger(d):
    pts = [(s["predicted_fire_rate"], s["measured_fire_rate"], s.get("candidate"))
           for s in d.scope
           if isinstance(s.get("predicted_fire_rate"), (int, float))
           and isinstance(s.get("measured_fire_rate"), (int, float))]
    if not pts:
        return empty("F19-trigger", "F19 · Trigger prediction",
                     "no predicted fire rate is available (the judge was never reachable)")
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot([0, 1], [0, 1], ":", color="#999999", lw=1)
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=90, facecolor="#2b2b2b",
               edgecolor="black", lw=0.8)
    for x, y, name in pts:
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(7, 4), fontsize=7)
    _setup(ax, "F19 · Predicted against measured fire rate", "measured", "predicted")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return save(fig, "F19-trigger",
                f"n = {len(pts)} live items. Far too few for a correlation to mean anything: "
                "the pairs and their rank order are the result, and no r is quoted.")
