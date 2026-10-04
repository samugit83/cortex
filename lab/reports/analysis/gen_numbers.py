#!/usr/bin/env python3
"""gen_numbers.py — every number the paper quotes, as LaTeX macros.

  python3 lab/reports/analysis/gen_numbers.py   -> paper/generated/numbers.tex

The paper never types a number. Each macro is read from lab/reports/ — the scorecard
the report wrote, or the rows themselves through the report's own analysis code — so
if the data moves, the paper moves with it, and `grep` can prove a number's origin.
Needs the analysis environment (numpy): run it through `make numbers`.
"""
import json
import re
import sys
from pathlib import Path

CORTEX = Path(__file__).resolve().parents[3]
PAPER = CORTEX / "paper"                      # the paper's sources, kept outside the repository
sys.path.insert(0, str(CORTEX / "lab" / "reports" / "analysis"))
import load                                   # noqa: E402
import stats as S                             # noqa: E402
import rescore                                # noqa: E402

DATA = CORTEX / "lab" / "reports" / "data"
OUT = PAPER / "generated" / "numbers.tex"


def tex(x):
    """A signed number as typeset text: a real minus sign, never a hyphen."""
    s = str(x).strip()
    if s in ("+0.0", "-0.0"):                  # zero carries no sign, in the text as in the figures
        return "0.0"
    return s.replace("-", r"\textminus{}", 1) if s.startswith("-") else s


def pts(v):
    return tex(f"{v * 100:+.1f}")


def interval(s):
    """'[+34.1, +74.1] …' -> ('+34.1', '+74.1')"""
    m = re.search(r"\[\s*([+-]?[0-9.]+)%?\s*,\s*([+-]?[0-9.]+)%?\s*\]", s or "")
    if not m:
        raise SystemExit(f"no interval in {s!r}")
    return m.group(1), m.group(2)


def need(pattern, s, what):
    m = re.search(pattern, s or "")
    if not m:
        raise SystemExit(f"gen_numbers.py: cannot read {what} from {s!r}")
    return m


def main():
    d = load.Data()
    cards = json.loads((DATA / "scorecard.json").read_text())
    cards = {c["id"]: c for c in (cards if isinstance(cards, list) else cards.get("hypotheses", []))}
    spend = json.loads((DATA / "spend.json").read_text())
    M = {}

    # the primary result
    h1 = cards["H1"]
    M["HoneEst"] = tex(need(r"([+-][0-9.]+)", h1["estimate"], "H1").group(1))
    M["HoneLo"], M["HoneHi"] = map(tex, interval(h1["interval"]))
    p = float(need(r"permutation p = ([0-9.e-]+)", h1["evidence"], "H1 p").group(1))
    # the text quotes the exact p and says it is the smallest the test can return: no
    # shuffle of the arm labels reached the observed gain
    if abs(p - 1 / (S.N_PERM + 1)) > 1e-6:
        raise SystemExit(f"gen_numbers.py: H1's permutation p ({p}) is not the test's floor")
    M["HoneP"] = f"= {p:.4f}"
    M["HoneTasks"] = need(r"(\d+) complete-case scenario-run pairs", h1["evidence"], "H1 tasks").group(1)
    h2 = cards["H2"]
    M["HtwoEst"] = tex(need(r"([+-][0-9.]+)", h2["estimate"], "H2").group(1))
    M["HtwoLo"], M["HtwoHi"] = map(tex, interval(h2["interval"]))
    M["HtwoSpurious"] = need(r"(\d+) spurious", h2["estimate"], "H2 spurious").group(1)

    # the A/A floor, recomputed exactly as report.py computes it
    ev = d.evaluation
    aa = S.cells(d.bench(runs=ev, arms=("none", "none2"), split="holdout"),
                 "none", "none2", families=list("ABCDE"), split="holdout")
    lo, hi, _ = S.two_way_bootstrap(aa)
    M["AAEst"], M["AALo"], M["AAHi"] = pts(S.paired_mean(aa)), pts(lo), pts(hi)

    # the gates against known answers
    h5 = cards["H5"]
    m = need(r"false KEEP (\d+)/(\d+); harmful kept (\d+)/(\d+) \(score.sh: (\d+) KILL, (\d+) RERUN\); "
             r"positives kept (\d+)/(\d+)", h5["estimate"], "H5")
    (M["PlaceboKept"], M["Placebos"], _harmful_kept, M["Harmful"], h5_kill, h5_rerun,
     M["PositivesKept"], M["Positives"]) = m.groups()
    M["PlaceboUpper"] = interval(h5["interval"])[1] + r"\%"
    h6 = cards["H6"]
    M["AcceptAllEst"] = tex(need(r"([+-][0-9.]+)", h6["estimate"], "H6").group(1))
    M["AcceptAllLo"], M["AcceptAllHi"] = map(tex, interval(h6["interval"]))

    # the margins §5 states in words, as the scorecard prints them
    M["MarginDFamily"] = tex(need(r"lower bound above ([+-]?\d+)", h2["margin"], "H2 margin").group(1))
    not_better = need(r"upper bound below ([+-]\d+)", h6["margin"], "H6 margin").group(1)
    if need(r"upper bound below ([+-]\d+)", cards["H7"]["margin"], "H7 margin").group(1) != not_better:
        raise SystemExit("gen_numbers.py: H6 and H7 no longer share a margin; the text says they do")
    M["MarginNotBetter"] = tex(not_better)
    M["MarginClose"] = need(r"within (\d+) points", cards["H8"]["margin"], "H8 margin").group(1)
    M["MarginDescShare"] = need(r"at least (\d+)%", cards["H12"]["margin"], "H12 margin").group(1) + r"\%"
    # and the one the hypothesis table states besides: H5's bar on kept placebos
    M["MarginPlaceboUpper"] = need(r"upper bound below (\d+)%", h5["margin"], "H5 margin").group(1) + r"\%"
    mp = need(r"at least (\d+) of (\d+) positives kept", h5["margin"], "H5 margin, known-good")
    if mp.group(2) != M["Positives"]:
        raise SystemExit("gen_numbers.py: H5's margin counts the known-good candidates differently from its estimate")
    M["MarginPositives"] = mp.group(1)

    # context cost
    h8 = cards["H8"]
    m = need(r"([0-9.]+) points AHEAD OF `kitchen` · always-on (\d+) vs kitchen (\d+), ideal (\d+)",
             h8["estimate"], "H8")
    gap, evolved, kitchen, ideal = m.groups()
    M["KitchenGap"] = gap
    M["EvolvedChars"], M["KitchenChars"], M["IdealChars"] = (
        f"{int(x):,}".replace(",", "{,}") for x in (evolved, kitchen, ideal))
    M["KitchenRatio"] = f"{int(kitchen) / int(evolved):.1f}"
    # the interval is printed as kitchen − evolved; the text quotes evolved − kitchen
    klo, khi = (float(x) for x in interval(h8["interval"]))
    M["KitchenLo"], M["KitchenHi"] = tex(f"{-khi + 0.0:+.1f}"), tex(f"{-klo + 0.0:+.1f}")
    # which run measured the ceiling arms (only one did)
    runs = [json.loads(l) for l in (DATA / "runs.jsonl").read_text().splitlines() if l.strip()]
    arms_of = {r["run"]: (r.get("arms") or {}) for r in runs}
    kruns = [r for r in ev if "kitchen" in arms_of.get(r, {})]
    if len(kruns) != 1:
        raise SystemExit(f"gen_numbers.py: expected one run with a kitchen arm, found {kruns}")
    M["KitchenRun"] = kruns[0]
    # every item the loop kept is path-scoped: the evolved arm adds no always-on text, and
    # its CLAUDE.md is the one `cortex init` wrote — the same file the no-harness arm has
    for r in ev:
        a = arms_of[r]
        if a["evolved"]["item_chars"] != 0 or a["evolved"]["claude_md_chars"] != a["none"]["claude_md_chars"]:
            raise SystemExit(f"gen_numbers.py: {r}'s evolved arm adds always-on text — revise the text")
    M["InitClaudeChars"] = f"{arms_of[ev[0]]['none']['claude_md_chars']:,}".replace(",", "{,}")
    # the kitchen arm appends the contribution guide (rstripped) after a newline, plus one
    guide = (CORTEX / "lab" / "seed" / "CONTRIBUTING.md").read_text(encoding="utf-8").rstrip()
    if int(kitchen) != arms_of[ev[0]]["none"]["claude_md_chars"] + len(guide) + 2:
        raise SystemExit("gen_numbers.py: the kitchen arm is not CLAUDE.md + the seed's CONTRIBUTING.md")
    M["GuideChars"] = f"{len(guide):,}".replace(",", "{,}")

    # what survives
    kept = [i for i in d.items if i["run"] in ev and i.get("fate") == "kept"]
    M["KeptItems"] = str(len(kept))
    M["KeptSkills"] = str(sum(1 for i in kept if i.get("kind") == "skill"))
    M["KeptRules"] = str(sum(1 for i in kept if i.get("kind") == "rule"))

    # /prune against known answers: four planted items, and R1's four own items
    pr = [json.loads(l) for l in (DATA / "prune.jsonl").read_text().splitlines() if l.strip()]
    M["PruneTested"] = str(len(pr))
    M["PruneMatched"] = str(sum(1 for r in pr if r.get("matches")))
    M["Planted"] = str(sum(1 for r in pr if r.get("planted")))
    M["PlantedMatched"] = str(sum(1 for r in pr if r.get("planted") and r.get("matches")))
    # the planted items the pass should delete: the placebo always-on skills
    M["PlantedPlacebos"] = str(sum(1 for r in pr if r.get("planted") and r.get("expected") == "ACCEPT"))
    if any("placebo" not in r.get("role", "") for r in pr if r.get("planted") and r.get("expected") == "ACCEPT"):
        raise SystemExit("gen_numbers.py: a planted item that should be deleted is not a placebo")
    m = need(r"(\d+) of (\d+) matched", cards["H10"]["estimate"], "H10")
    if m.groups() != (M["PruneMatched"], M["PruneTested"]):
        raise SystemExit("gen_numbers.py: prune.jsonl and the scorecard's H10 disagree")

    # the loop's own decisions, scored again from the rollouts by the rules of Table 2
    cs = rescore.candidates()
    items_ev = [i for i in d.items if i["run"] in ev]
    M["LoopWritten"] = str(len(items_ev))
    M["LoopSwept"] = str(len(cs))
    M["LoopKilled"] = str(sum(1 for c in cs if c["verdict"] == "KILL"))
    M["LoopUnscored"] = str(sum(1 for c in cs if c["verdict"] == "RERUN" and c["recorded"] == "buried"))
    if sum(1 for c in cs if c["verdict"] == "KEEP") != len(kept):
        raise SystemExit("gen_numbers.py: the rules and the loop disagree on what was kept")
    ex = next(c for c in cs if (c["run"], c["name"]) == ("R3", "exporter-checklist-v2"))
    ex_conf = next(x for x in ex["sweeps"] if x["phase"] == "confirm")
    M["SweepExampleTasks"] = str(ex_conf["tasks"])
    M["SweepExampleExposed"] = str(len(ex_conf["exposed"]))

    # loaded or chosen: runs in which a candidate was offered, and in which it acted
    # (the loop's sweeps, and the gate test's screens and confirms; tiers as each sweep
    # recorded them)
    offered = {"always": [0, 0], "gated": [0, 0]}
    for r in d.rollouts:
        if (r.get("source") == "sweep" and r["run"] in ev and r.get("arm") == "cand"
                and r.get("candidate_tier") in offered and r.get("valid", 1)):
            if r["candidate"] in (r.get("visible") or []):
                offered[r["candidate_tier"]][0] += 1
                offered[r["candidate_tier"]][1] += r["candidate"] in (r.get("fired") or [])
    gates = [json.loads(l) for l in (DATA / "gates.jsonl").read_text().splitlines() if l.strip()]
    for g in gates:
        for ph in ("screen", "confirm"):
            sc = g.get(ph) or {}
            if sc.get("candidate_tier") in offered:
                offered[sc["candidate_tier"]][0] += sc.get("candidate_visible_runs") or 0
                offered[sc["candidate_tier"]][1] += sc.get("candidate_fired_runs") or 0
    M["AlwaysOnOffered"], M["AlwaysOnInvoked"] = map(str, offered["always"])
    if offered["always"][1] != 0:
        raise SystemExit("gen_numbers.py: an always-on candidate was opened; the introduction says none was")
    M["GatedOffered"], M["GatedInvoked"] = map(str, offered["gated"])
    # the gate test's screens, by the scorer's own verdict (score.sh RERUN is not a KILL)
    for kind, key in (("harmful", "Harmful"), ("placebo", "Placebo")):
        rs = [g for g in gates if g["type"].startswith(kind)]
        M[f"Gate{key}Killed"] = str(sum(1 for g in rs if (g.get("screen") or {}).get("verdict") == "KILL"))
        M[f"Gate{key}Unscored"] = str(sum(1 for g in rs if (g.get("screen") or {}).get("verdict") == "RERUN"))
    if (M["GateHarmfulKilled"], M["GateHarmfulUnscored"]) != (h5_kill, h5_rerun):
        raise SystemExit("gen_numbers.py: the scorecard's H5 and the gate test's rows disagree on harm")

    # a stronger model
    h14 = cards["H14"]
    m = need(r"(\d+) of (\d+) decided item\(s\) removable.*gains ([+-][0-9.]+) under Haiku "
             r"\((\w+)\) and ([+-][0-9.]+) under (\S+)", h14["estimate"], "H14")
    (M["RemovableItems"], M["DecidedItems"], haiku, M["ModelChangeSource"], sonnet, model) = m.groups()
    M["HaikuGain"], M["SonnetGain"] = tex(haiku), tex(sonnet)
    M["SonnetLo"], M["SonnetHi"] = map(tex, interval(h14["interval"]))
    M["StrongModel"] = model.replace("_", r"\_")

    # the study's design, as run (§4): read from the rows, and checked against each other
    import csv
    from collections import defaultdict as dd
    fam = {r["family"]: r for r in csv.DictReader(open(CORTEX / "lab" / "reports" / "tables" / "T1-the-lab.csv"))}
    for f, r in fam.items():
        M[f"TrainFam{f}"], M[f"HoldFam{f}"] = r["train"], r["holdout"]
    if sum(int(r["train"]) for r in fam.values()) != len({x["task"] for x in d.bench(runs=ev, split="train")}):
        raise SystemExit("gen_numbers.py: T1's training counts do not add up to the benchmark's")
    sessions = [json.loads(l) for l in (DATA / "sessions.jsonl").read_text().splitlines() if l.strip()]
    per_run = {r: sum(1 for x in sessions if x["run"] == r) for r in list(ev) + ["C1"]}
    if len(set(per_run.values())) != 1:
        raise SystemExit(f"gen_numbers.py: runs played different numbers of sessions: {per_run}")
    M["SessionsPerRun"] = str(next(iter(per_run.values())))
    M["Rounds"] = str(max(x["round"] for x in sessions if x["run"] in ev))
    ks = dd(set)
    for r in d.rollouts:
        if r.get("source") == "bench" and r["run"] in list(ev) + ["C1"]:
            primary = r.get("arm") in ("none", "evolved")
            ks[("primary" if primary else "ablation", r.get("split"))].add(r.get("r") or 0)
    kmax = {key: max(v) for key, v in ks.items()}
    M["PrimaryK"], M["TrainK"], M["AblationK"] = (str(kmax[("primary", "holdout")]),
                                                  str(kmax[("primary", "train")]),
                                                  str(kmax[("ablation", "holdout")]))
    mk = {max(r.get("r") or 0 for r in d.rollouts if r.get("source") == "bench" and r["run"] == "M1"
              and r.get("split") == "holdout")}
    M["ModelChangeK"] = str(mk.pop())
    # exclusions: T2 lists, per scenario, the runs it was excluded from
    excl = [(r["id"], r["excluded from"]) for r in
            csv.DictReader(open(CORTEX / "lab" / "reports" / "tables" / "T2-scenarios.csv"))
            if r.get("excluded from", "—") not in ("", "—")]
    if len(excl) != 1:
        raise SystemExit(f"gen_numbers.py: the text names one excluded scenario, T2 lists {excl}")
    M["ExcludedScenario"], M["ExcludedFrom"] = excl[0]
    rule_tasks = [{x["task"] for x in d.bench(runs=[r], split="holdout") if x.get("family") in "ABCE"}
                  for r in ev]
    M["CompleteTasks"] = str(len(set.intersection(*rule_tasks)))
    if len(set.intersection(*rule_tasks)) * len(ev) != int(M["HoneTasks"]):
        raise SystemExit("gen_numbers.py: complete-case tasks x runs is not H1's cell count")
    gates_all = [json.loads(l) for l in (DATA / "gates.jsonl").read_text().splitlines() if l.strip()]
    M["GateCandidates"] = str(len(gates_all))
    M["PlaceboTopic"] = str(sum(1 for g in gates_all if g["type"] == "placebo-topic"))
    M["PlaceboMoment"] = str(sum(1 for g in gates_all if g["type"] == "placebo-moment"))
    M["RunOneItems"] = str(sum(1 for i in d.items if i["run"] == "R1" and i.get("fate") == "kept"))
    ext = [json.loads(l) for l in (DATA / "external.jsonl").read_text().splitlines() if l.strip()]
    M["SecondRepo"] = ext[0]["repo"].split("/")[-1]
    M["SecondRepoSlug"] = ext[0]["repo"]
    a8 = (CORTEX / "lab" / "reports" / "appendix" / "A8-external-tasks.md").read_text()
    M["SecondRepoBase"] = need(r"at base `([0-9a-f]{7,40})`", a8, "the second repository's base commit").group(1)
    M["SecondRepoHoldout"] = str(len({e["task"] for e in ext if e["split"] == "holdout"}))
    M["SecondRepoK"] = str(max(e["n"] for e in ext))
    M["BootReps"] = f"{S.N_BOOT:,}".replace(",", "{,}")
    M["PermReps"] = f"{S.N_PERM:,}".replace(",", "{,}")
    mani0 = json.loads((DATA / "manifest.json").read_text())
    # the rollout model, as every evaluation sweep row recorded it
    models = {r.get("model") for r in d.rollouts if r.get("source") == "sweep" and r["run"] in ev}
    if len(models) != 1:
        raise SystemExit(f"gen_numbers.py: the evaluation sweeps ran more than one model: {models}")
    M["RolloutModel"] = models.pop()
    # the CLI's own skills: invoked in the primary arms, though no harness contains them
    items_all = {i["name"] for i in d.items}
    gates_names = {g["name"] for g in gates_all}
    plants = {r.get("item") for r in
              (json.loads(l) for l in (DATA / "prune.jsonl").read_text().splitlines() if l.strip())}
    ours = items_all | gates_names | plants | set(load.CORTEX_COMMANDS)
    for arm in ("none", "evolved"):
        rs = [r for r in d.rollouts if r.get("source") == "bench" and r["run"] in ev
              and r.get("arm") == arm and r.get("valid", 1)]
        hit = sum(1 for r in rs if set(r.get("fired") or []) - ours)
        M[f"Bundled{arm.capitalize()}"] = f"{100 * hit / len(rs):.1f}\\%"

    # the same two models by name, for the prose (claude-haiku-4-5-20251001 -> Claude Haiku 4.5)
    def model_name(mid):
        fam, major, minor = need(r"^claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$", mid, "a model id").groups()
        return f"Claude {fam.capitalize()} {major}" + (f".{minor}" if minor else "")
    M["RolloutModelName"], M["StrongModelName"] = model_name(M["RolloutModel"]), model_name(model)
    # the development run's cost is kept apart from the programme's (manifest; spend.json omits it)
    if abs(mani0["cost_usd"]["programme_measured"] - spend["total"]) > 0.005:
        raise SystemExit("gen_numbers.py: manifest and spend.json disagree on the programme's cost")
    M["DevSpend"] = f"{mani0['cost_usd']['development_run_D0']:,.0f}".replace(",", "{,}")

    # the release whose scripts and data regenerate the paper: this checkout's, as its tag
    version = (CORTEX / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"gen_numbers.py: VERSION holds {version!r}, not a version such as 1.0.1")
    M["ReleaseTag"] = "v" + version

    # scale and cost
    M["EvalRuns"] = str(len(ev))
    M["HoldoutTasks"] = str(len({r["task"] for r in d.bench(runs=ev, split="holdout")}))
    M["TrainTasks"] = str(len({r["task"] for r in d.bench(runs=ev, split="train")}))
    M["Rollouts"] = f"{len(d.rollouts):,}".replace(",", "{,}")
    M["Spend"] = f"{spend['total']:,.0f}".replace(",", "{,}")
    M["BudgetCap"] = f"{spend['cap']:,.0f}".replace(",", "{,}")

    # the design's parameters: the defaults `cortex init` writes, AT THE FROZEN TAG —
    # the paper describes the system as evaluated, not as it may have changed since
    import subprocess
    def at_tag(path):
        return subprocess.run(["git", "show", f"v1.0-eval:{path}"], cwd=CORTEX,
                              capture_output=True, text=True, check=True).stdout
    tmpl = at_tag("bin/cortex")
    def conf(key):
        return need(rf"\n\s*{key}:\s*([0-9.]+)", tmpl, f"config {key}").group(1)
    M["KScreen"], M["KConfirm"] = conf("screen"), conf("confirm")
    # why the per-sweep cap was raised: a confirm over every training task, both arms
    M["ConfirmSweepRollouts"] = str(int(M["TrainTasks"]) * int(M["KConfirm"]) * 2)
    M["RegressionTolerance"] = conf("regression_tolerance")
    M["MinNetRuns"] = conf("min_net_runs")
    M["MaxInvalidPct"] = f"{float(conf('max_invalid_rate')) * 100:.0f}\\%"
    M["MinThemeOccurrences"] = conf("min_theme_occurrences")
    M["StopAfterBarren"] = conf("stop_after_barren_cycles")
    # the other side of the theme bar: a cause behind this many currently failing tasks
    M["MinThemeFailingTasks"] = need(r"explains \*\*(\d+) or more\*\* currently-failing tasks",
                                     at_tag("commands/evolve.md"), "theme failing-task bar").group(1)
    # an overloaded machine: more than this many runnable processes per CPU
    M["OverloadFactor"] = need(r"\.load > \((\d+) \* \$cpus\)", at_tag("bin/score.sh"), "overload factor").group(1)
    # how often the lab's scripted reviewer sends the agent back
    M["MaxCorrections"] = need(r"\nMAX_CORRECTIONS = (\d+)", (CORTEX / "lab" / "bin" / "autopilot").read_text(),
                               "MAX_CORRECTIONS").group(1)
    # the settings our runs changed from those defaults (lab/rounds/round-00.md §0.4,
    # copied byte for byte into every run by lab/bin/run-eval)
    r00 = (CORTEX / "lab" / "rounds" / "round-00.md").read_text()
    changed = dict((k, (a, b)) for k, a, b in
                   re.findall(r"\n\| `([\w.]+)` \| ([^|]+?) \| ([^|]+?) \|", r00))
    M["StopAfterBarrenEval"] = changed["collection.stop_after_barren_cycles"][1]
    M["MaxRunsDefault"], M["MaxRunsEval"] = changed["measurement.max_runs_per_cycle"]
    if changed["collection.stop_after_barren_cycles"][0] != M["StopAfterBarren"]:
        raise SystemExit("gen_numbers.py: round-00.md's default barren limit is not the tag's")
    M["AlwaysOnBudget"] = f"{int(conf('always_on_budget_chars')):,}".replace(",", "{,}")
    M["RolloutTimeoutMin"] = f"{int(conf('rollout_timeout_s')) // 60}"
    # the implementation's size at the tag: the scripts and the command prompts
    files = subprocess.run(["git", "ls-tree", "-r", "--name-only", "v1.0-eval", "bin/", "hooks/", "commands/"],
                           cwd=CORTEX, capture_output=True, text=True, check=True).stdout.split()
    code = [f for f in files if f.endswith((".sh", ".py")) or f == "bin/cortex"]
    prompts = [f for f in files if f.endswith(".md")]
    M["ImplCodeLines"] = f"{sum(at_tag(f).count(chr(10)) for f in code):,}".replace(",", "{,}")
    M["ImplCodeFiles"] = str(len(code))
    M["ImplPromptLines"] = f"{sum(at_tag(f).count(chr(10)) for f in prompts):,}".replace(",", "{,}")
    M["ImplJevLines"] = f"{at_tag('bin/jev.py').count(chr(10)):,}".replace(",", "{,}")
    # the Claude Code version every evaluated rollout ran, and the minimum the tag demands
    mani = json.loads((DATA / "manifest.json").read_text())
    M["ClaudeCodeVersion"] = need(r"([0-9.]+)", " ".join(mani["claude_code"]), "CLI version").group(1)
    M["MinClaudeVersion"] = need(r"\n\s*min_claude_version:\s*\"?([0-9.]+)", tmpl, "min version").group(1)

    results(d, M, cards, ev, gates_all, sessions, at_tag)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by lab/reports/analysis/gen_numbers.py from lab/reports/ — do not edit", ""]
    lines += [rf"\newcommand{{\{k}}}{{{v}}}" for k, v in sorted(M.items())]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"{len(M)} numbers -> {OUT}")


def results(d, M, cards, ev, gates_all, sessions, at_tag):
    """§5: what the Results text quotes beyond the scorecard's headline numbers. Every
    comparison uses the lab's own arm_pair (the scorecard's definition); where the text
    reads a pattern into the numbers, a check below stops the build if the data move."""
    import csv
    import math
    import rebuild as RB
    from collections import defaultdict

    def rate(v, places=1):                     # a pass rate as typeset text: 87.5\%
        return f"{100 * v:.{places}f}" + r"\%"

    def stop(why):
        raise SystemExit(f"gen_numbers.py (§5): {why} — revise the text")

    fams = tuple(load.RULE_FAMILIES)
    T6 = list(csv.DictReader(open(CORTEX / "lab" / "reports" / "tables" / "T6-items.csv")))
    fam_of = {(r["run"], r["name"]): r["family"] for r in T6 if r["fate"] == "kept"}
    fam_all = {(r["run"], r["name"]): r["family"] for r in T6}

    # ---- held-out gain ------------------------------------------------------------------
    h0 = need(r"A(\d+)% B(\d+)% C(\d+)% D(\d+)% E(\d+)%", cards["H0"]["estimate"], "H0").groups()
    for f, v in zip("ABCDE", h0):
        M[f"NoneRate{f}"] = v + r"\%"
    # H0's printed margin asks every rule family below a bar; the lab's code passes three of
    # four (rebuild.py), and the pre-registration sets no number. The text says E misses it.
    bar = int(need(r"at least three of A/B/C/E below (\d+)%", cards["H0"]["margin"], "H0 margin").group(1))
    if "the stricter reading, all four below 50%, is not met" not in cards["H0"]["evidence"]:
        stop("the scorecard no longer says the stricter reading of H0 is not met")
    below = [f for f, v in zip("ABCDE", h0) if f in fams and int(v) < bar]
    if sorted(set(fams) - set(below)) != ["E"] or cards["H0"]["verdict"] != "SUPPORTED":
        stop("H0's margin is not missed by E alone, or H0 is no longer supported")
    M["HzeroBar"] = f"{bar}" + r"\%"
    M["HzeroBelowN"] = str(len(below))
    dbar = int(need(r"D at or above (\d+)%", cards["H0"]["margin"], "H0 margin, family D").group(1))
    if int(h0[3]) < dbar:
        stop("family D is below H0's bar for it, and the text says it is above")
    M["HzeroBarD"] = f"{dbar}" + r"\%"
    # the premise the lab rests on: without a harness, the agent does not read the guide
    rs = [r for r in d.bench(runs=ev, arms=("none",), split="holdout") if r.get("read_contributing") is not None]
    M["GuideReadNone"] = rate(sum(1 for r in rs if r["read_contributing"]) / len(rs))
    # each rule family, complete-case, with Holm across the four
    ps = []
    for f in fams:
        r = RB.arm_pair(d, ev, "none", "evolved", families=(f,), complete_case=True)
        M[f"Fam{f}Est"], M[f"Fam{f}Lo"], M[f"Fam{f}Hi"] = pts(r["mean"]), pts(r["lo"]), pts(r["hi"])
        ps.append(r["p"])
    holm = S.holm(ps)
    if max(holm) >= 0.001:
        stop("a rule family's Holm-adjusted p is not below 0.001")
    # the text gives one value for the four families: they must all round to it
    if len({f"{h:.4f}" for h in holm}) != 1:
        stop("the four rule families' Holm-adjusted p differ")
    M["FamHolmP"] = f"= {holm[0]:.4f}"
    # ... and says that no shuffle reached any family's gain: each raw p is the test's floor
    if any(abs(p_ - 1 / (S.N_PERM + 1)) > 1e-9 for p_ in ps):
        stop("a rule family's permutation p is not the test's floor")
    # the A/A pair: which run measured it (the same run as the ceiling arms)
    aa_runs = sorted({run for run, _t in S.cells(d.bench(runs=ev, arms=("none", "none2"), split="holdout"),
                                                "none", "none2", families=list("ABCDE"), split="holdout")})
    if len(aa_runs) != 1:
        stop("the A/A arm ran in more than one run")
    M["AARun"] = aa_runs[0]
    # its permutation p, and the scenarios on which the two measurements differ
    raa = RB.arm_pair(d, aa_runs, "none", "none2", families=tuple("ABCDE"), complete_case=False)
    if pts(raa["mean"]) != M["AAEst"]:
        stop("the A/A pair is not the one the introduction quotes")
    M["AAP"] = f"{raa['p']:.2f}"
    differ = [v for v in raa["cells"].values() if v[1] != v[2]]
    if not differ or any(v[1] < v[2] for v in differ):
        stop("the A/A's differing scenarios do not all favour the first measurement")
    M["AADiffering"] = str(len(differ))
    # on the rule families alone, the families every ablation comparison uses
    aar = S.cells(d.bench(runs=aa_runs, arms=("none", "none2"), split="holdout"), "none", "none2",
                  families=list(fams), split="holdout")
    lo, hi, _ = S.two_way_bootstrap(aar)
    M["AARuleEst"], M["AARuleLo"], M["AARuleHi"] = pts(S.paired_mean(aar)), pts(lo), pts(hi)
    m = need(r"all-valid set: ([+-][0-9.]+) \[([+-][0-9.]+), ([+-][0-9.]+)\]",
             cards["H1"]["evidence"], "H1 all-valid")
    M["HoneAllEst"], M["HoneAllLo"], M["HoneAllHi"] = map(tex, m.groups())
    # the runs, one by one: which gained least, and the others' range
    pool = RB.arm_pair(d, ev, "none", "evolved", families=fams, complete_case=True)
    if pts(pool["mean"]) != M["HoneEst"]:
        stop("the pooled pair is not the scorecard's H1")
    per = defaultdict(lambda: ([], []))
    for (run, _t), (_f, pa, pb, _na, _nb) in pool["cells"].items():
        per[run][0].append(pa)
        per[run][1].append(pb)
    runrate = {run: (sum(a) / len(a), sum(b) / len(b)) for run, (a, b) in per.items()}
    narrow = min(runrate, key=lambda k: runrate[k][1])
    M["NarrowRun"] = narrow
    M["NarrowPoolNone"], M["NarrowPoolEvolved"] = rate(runrate[narrow][0]), rate(runrate[narrow][1])
    others = [v[1] for k, v in runrate.items() if k != narrow]
    M["OthersPoolLo"], M["OthersPoolHi"] = rate(min(others)), rate(max(others))
    # training against held-out: the same pair on the training scenarios, which the benchmark
    # replays for none and evolved; descriptive, beside the primary
    seen = RB.arm_pair(d, ev, "none", "evolved", families=fams, split="train", complete_case=True)
    M["SeenGainEst"], M["SeenGainLo"], M["SeenGainHi"] = pts(seen["mean"]), pts(seen["lo"]), pts(seen["hi"])
    M["SeenTasks"] = str(len({t for _r, t in seen["cells"]}))

    def pooled(rows, arm, f=fams):             # pass rate over rollouts, as in tab:main
        xs = [r["pass"] for r in rows if r["arm"] == arm and r["family"] in f and r.get("valid")]
        return sum(xs) / len(xs)
    lift = {}
    for key, rows in (("Seen", seen["rows"]), ("Held", pool["rows"])):
        M[f"{key}NoneRate"], M[f"{key}EvolvedRate"] = rate(pooled(rows, "none")), rate(pooled(rows, "evolved"))
        for f in fams:
            lift[key, f] = pooled(rows, "evolved", (f,))
            M[f"{key}Evo{f}"] = rate(lift[key, f])
    M["SeenNoneE"], M["HeldNoneE"] = (rate(pooled(r_, "none", ("E",))) for r_ in (seen["rows"], pool["rows"]))
    # what the text reads into them: a larger gain on the training scenarios, more from a
    # lower baseline there than from the evolved rate; the evolved rate falling most in C,
    # and there in every run; B's fall all NarrowRun's (without it, the rate rose); E's rate
    # holding (under five points) while its gain falls, its held-out baseline the higher
    base_gap = pooled(pool["rows"], "none") - pooled(seen["rows"], "none")
    evo_gap = pooled(seen["rows"], "evolved") - pooled(pool["rows"], "evolved")
    if not (seen["mean"] > pool["mean"] and base_gap > evo_gap > 0):
        stop("training against held-out no longer reads: larger gain, more from the baseline")
    fall = {f: lift["Seen", f] - lift["Held", f] for f in fams}
    if max(fall, key=fall.get) != "C":
        stop("the evolved rate no longer falls most in C")
    for run in ev:
        sr = [r_ for r_ in seen["rows"] if r_["run"] == run]
        hr = [r_ for r_ in pool["rows"] if r_["run"] == run]
        if pooled(sr, "evolved", ("C",)) <= pooled(hr, "evolved", ("C",)):
            stop(f"the evolved rate on C does not fall in {run}")
    rest = [run for run in ev if run != narrow]
    sr = [r_ for r_ in seen["rows"] if r_["run"] in rest]
    hr = [r_ for r_ in pool["rows"] if r_["run"] in rest]
    if not (fall["B"] > 0 and pooled(hr, "evolved", ("B",)) > pooled(sr, "evolved", ("B",))):
        stop(f"B's evolved rate no longer falls only because of {narrow}")
    seen_e = RB.arm_pair(d, ev, "none", "evolved", families=("E",), split="train", complete_case=True)
    held_e = RB.arm_pair(d, ev, "none", "evolved", families=("E",), complete_case=True)
    if not (abs(fall["E"]) < 0.05 and seen_e["mean"] > held_e["mean"]
            and pooled(pool["rows"], "none", ("E",)) > pooled(seen["rows"], "none", ("E",))):
        stop("E's evolved rate no longer holds while its gain falls on an easier baseline")
    # corrections per session (H4): what the lab computed, over all sessions
    es = [x for x in sessions if x["run"] in ev]
    cs_ = [x for x in sessions if x["run"] in d.control]
    ce, cc = sum(x["corrections"] for x in es), sum(x["corrections"] for x in cs_)
    M["CorrEval"], M["SessEval"], M["CorrControl"], M["SessControl"] = map(str, (ce, len(es), cc, len(cs_)))
    M["CorrEvalRate"], M["CorrControlRate"] = f"{ce / len(es):.2f}", f"{cc / len(cs_):.2f}"
    if f"{ce / len(es) - cc / len(cs_):+.2f}" != need(r"([+-][0-9.]+)", cards["H4"]["estimate"], "H4").group(1):
        stop("the corrections differ from the scorecard's H4")
    if len(d.control) != 1:
        stop("the text speaks of a single control run")
    # the smallest one-sided p a permutation of the run labels can reach with these runs
    M["HfourMinP"] = f"{1 / math.comb(len(ev) + len(d.control), len(d.control)):.1f}"
    # the development run, re-measured (H13)
    m = need(r"D0 ([+-][0-9.]+) \(on its own (\d+)-task holdout: ([+-][0-9.]+)\), replicates ([+-][0-9.]+)",
             cards["H13"]["estimate"], "H13")
    M["DzeroGain"], M["DzeroOwnTasks"], M["DzeroOwn"] = tex(m.group(1)), m.group(2), tex(m.group(3))
    # D0's own figure is over the rule-family scenarios of its own held-out set
    d0own = RB.arm_pair(d, d.development, "none", "evolved", families=fams, complete_case=False)
    if pts(d0own["mean"]) != M["DzeroOwn"]:
        stop("D0's own gain is not over its rule-family scenarios")
    M["DzeroOwnRuleTasks"] = str(len({t for _r, t in d0own["cells"]}))
    if tex(m.group(4)) != M["HoneAllEst"] or tuple(map(tex, interval(cards["H13"]["interval"]))) != (
            M["HoneAllLo"], M["HoneAllHi"]):
        stop("H13 is not compared with the all-valid interval")
    # H13's margin sets one run's gain against the interval of the mean of R1 to R4; a single
    # run varies more, so the text also gives the range of the runs' own gains on that set
    own_gain = {run: S.paired_mean(S.cells(d.bench(runs=[run], arms=("none", "evolved"), split="holdout"),
                                           "none", "evolved", families=list(fams), split="holdout"))
                for run in ev}
    M["RunGainAllLo"], M["RunGainAllHi"] = pts(min(own_gain.values())), pts(max(own_gain.values()))
    if not 100 * min(own_gain.values()) <= float(m.group(1)) <= 100 * max(own_gain.values()):
        stop("the development run's gain is outside the range of the evaluation runs' own gains")
    # the runs, counted (the text never types a count)
    M["ControlRuns"] = str(len(d.control))
    # the held-out scenarios the development run did not have: written after it
    d0_hold = {r["task"] for r in d.bench(runs=d.development, split="holdout")}
    held_all = {r["task"] for r in d.bench(runs=ev, split="holdout")}
    if not d0_hold or not d0_hold < held_all or str(len(d0_hold)) != M["DzeroOwnTasks"]:
        stop("the development run's held-out scenarios are not a part of the present ones")
    M["HoldoutLate"] = str(len(held_all) - len(d0_hold))

    # ---- what the loop did --------------------------------------------------------------
    cyc = [json.loads(l) for l in (DATA / "cycles.jsonl").read_text().splitlines() if l.strip()]
    evc = [c for c in cyc if c["run"] in ev and c.get("is_cycle")]
    M["LoopCycles"] = str(len(evc))
    M["LoopBarren"] = str(sum(1 for c in evc if c.get("verdict") == "BARREN"))
    # the cycles that swept a candidate. A candidate with no journal entry of its own was
    # swept inside another candidate's cycle: the text says one cycle swept more than one
    # candidate, and names its run (gen_diagram_data.py checks it against the cycles it draws)
    active = len(evc) - int(M["LoopBarren"])
    M["LoopActive"] = str(active)
    journaled = {(c["run"], c["name"]) for c in evc if c.get("verdict") != "BARREN"}
    extra = [c for c in rescore.candidates() if (c["run"], c["name"]) not in journaled]
    if len(extra) != 1 or len(journaled) != active or int(M["LoopSwept"]) != active + len(extra):
        stop("the candidates swept without a journal entry of their own are not one, in one cycle")
    M["SplitCycleSwept"], M["SplitCycleRun"] = str(len(extra) + 1), extra[0]["run"]
    sweeps = [json.loads(l) for l in (DATA / "sweeps.jsonl").read_text().splitlines() if l.strip()]
    by_phase = defaultdict(int)
    for s in sweeps:
        if s["run"] in ev:
            by_phase[s["phase"]] += s.get("rollouts") or 0
    M["LoopRollouts"] = f"{sum(by_phase.values()):,}".replace(",", "{,}")
    M["LoopConfirmRollouts"] = f"{by_phase['confirm']:,}".replace(",", "{,}")
    cs = rescore.candidates()
    rechecked = [c for c in cs if c.get("rechecked")]
    M["Rechecked"] = str(len(rechecked))
    M["RecheckKept"] = str(sum(1 for c in rechecked if c["verdict"] == "KEEP"))
    # scope: three runs chose the same globs, the narrow run named files
    same = {}
    for run in ev:
        if run == narrow:
            continue
        g = {}
        for (r_, n), f in fam_of.items():
            if r_ == run:
                g.setdefault(f, set()).update(next(i for i in d.items if i["run"] == run and i["name"] == n)["paths"])
        same[run] = g
    if len({json.dumps({f: sorted(p) for f, p in sorted(g.items())}) for g in same.values()}) != 1:
        stop("the runs other than the narrow one do not share their scopes")
    # ... and differ in form only for exporters: a gated skill in two, a rule in the third
    kinds = {f: sorted(next(i for i in d.items if i["run"] == r_ and i["name"] == n)["kind"]
                       for (r_, n), ff in fam_of.items() if r_ in same and ff == f) for f in fams}
    if kinds["C"] != ["rule", "skill", "skill"] or any(set(kinds[f]) != {"rule"} for f in fams if f != "C"):
        stop("the other runs' forms are not as the text describes them")
    # every kept skill is an exporter checklist gated on the plugins directory
    ks = [i for i in d.items if i["run"] in ev and i.get("fate") == "kept" and i.get("kind") == "skill"]
    if any(i.get("paths") != ["shop/plugins/**"] or fam_of[(i["run"], i["name"])] != "C" for i in ks):
        stop("a kept skill is not an exporter checklist on shop/plugins/**")

    def loaded(run, names, fam, split):
        rs_ = [r for r in d.bench(runs=[run], arms=("evolved",), split=split)
               if r.get("family") == fam and r.get("valid", 1)]
        return sum(1 for r in rs_ if set(names) & set(r.get("fired") or [])), len(rs_)
    money = [n for (r_, n), f in fam_of.items() if r_ == narrow and f == "B"]
    clock = [n for (r_, n), f in fam_of.items() if r_ == narrow and f == "E"]
    files = {p for n in money for p in next(i for i in d.items if i["run"] == narrow and i["name"] == n)["paths"]}
    if any("*" in p for p in files):
        stop("the narrow run's money rules are not lists of files")
    M["NarrowMoneyRules"], M["NarrowMoneyFiles"] = str(len(money)), str(len(files))
    M["NarrowMoneyFired"], M["NarrowMoneyN"] = map(str, loaded(narrow, money, "B", "holdout"))
    M["NarrowClockFired"], M["NarrowClockN"] = map(str, loaded(narrow, clock, "E", "holdout"))
    nb = [(pa, pb) for (run, _t), (f, pa, pb, _na, _nb) in pool["cells"].items() if run == narrow and f == "B"]
    M["NarrowMoneyNone"] = rate(sum(a for a, _ in nb) / len(nb))
    M["NarrowMoneyEvolved"] = rate(sum(b for _, b in nb) / len(nb))
    if M["NarrowMoneyEvolved"] != M["NarrowMoneyNone"]:
        stop("the narrow run's money pass rate did not stay the same in both arms")
    broad = [loaded(run, [n for (r_, n), f in fam_of.items() if r_ == run and f == "B"], "B", "holdout")
             for run in ev if run != narrow]
    M["BroadMoneyFiredMin"] = str(min(a for a, _ in broad))
    if M["NarrowMoneyFired"] != "0" or len({n for _, n in broad}) != 1 or str(broad[0][1]) != M["NarrowMoneyN"]:
        stop("the money rules' loading is not as the text describes it")
    # how the narrow run got there. Its clock rule replaced a shop-wide one that the gates
    # killed on a recheck (a task that never failed lost a run, then lost one again) ...
    order = [c["name"] for c in cs if c["run"] == narrow]          # the order of the sweeps
    killed = [c for c in cs if c["run"] == narrow and c["verdict"] == "KILL" and c.get("rechecked")]
    if ([fam_all.get((narrow, c["name"])) for c in killed] != ["E"]
            or order.index(killed[0]["name"]) > min(order.index(n) for n in clock)):
        stop("the narrow run's recheck KILL is not a clock rule swept before its narrow one")
    kc = {s["phase"]: s for s in killed[0]["sweeps"]}
    if (kc["confirm"]["failed"] != ["gate3"] or kc["confirm"]["regressed"] != kc["recheck"]["regressed"]
            or len(kc["confirm"]["regressed"]) != 1
            or any(abs(kc[p]["D"] - 1 / kc[p]["k"]) > 1e-9 for p in ("confirm", "recheck"))):
        stop("the clock rule's KILL is not one run lost on a protected task, twice")
    if len(clock) != 1 or M["NarrowClockFired"] == M["NarrowClockN"]:
        stop("the narrow run has not one clock rule, or it loaded on every held-out clock task")
    M["NarrowClockFiles"] = str(len(next(i for i in d.items if i["run"] == narrow and i["name"] == clock[0])["paths"]))
    # and the clock family's held-out pass rate in that run, which fell
    ne = [(pa, pb) for (run, _t), (f, pa, pb, _na, _nb) in pool["cells"].items() if run == narrow and f == "E"]
    ne_a, ne_b = sum(a for a, _ in ne) / len(ne), sum(b for _, b in ne) / len(ne)
    if not ne_b < ne_a:
        stop("the narrow run's clock family did not fall")
    M["NarrowClockNone"], M["NarrowClockEvolved"] = rate(ne_a), rate(ne_b)
    # ... and its first money rule, on all of shop/billing/**, was buried by the /evolve agent
    # although the rules left it unscored: its confirm lost no run on any task, but the event
    # stream of some rollouts could not be read (exposure unknown), so score.sh said RERUN
    unscored = [c for c in cs if c["run"] == narrow and c["verdict"] == "RERUN" and c["recorded"] == "buried"]
    if len(unscored) != 1 or fam_all.get((narrow, unscored[0]["name"])) != "B":
        stop("the narrow run has not exactly one unscored burial, of a money rule")
    ub = unscored[0]
    uconf = [s for s in ub["sweeps"] if s["phase"] == "confirm"]
    if (not uconf or uconf[-1]["D"] != 0 or uconf[-1]["regressed"] or not uconf[-1]["unknown"]
            or order.index(ub["name"]) > min(order.index(n) for n in money)
            or next(i for i in d.items if i["run"] == narrow and i["name"] == ub["name"])["paths"] != ["shop/billing/**"]):
        stop("the buried money rule is not a shop/billing/** rule swept first, unscored, with no drop")
    if sorted(c["name"] for c in cs if c["run"] == narrow and fam_all.get((narrow, c["name"])) == "B") != sorted(
            money + [ub["name"]]):
        stop("the narrow run proposed money rules beyond the buried broad one and the kept narrow ones")
    # the next cycle proposed the first narrow rule, citing the regression that never happened
    if min(order.index(n) for n in money) != order.index(ub["name"]) + 1:
        stop("the first narrow money rule did not follow the buried broad one")
    M["BroadMoneyTasks"] = str(uconf[-1]["tasks"])
    M["BroadMoneyNetRuns"] = str(round(uconf[-1]["net_runs"]))
    M["BroadMoneyUnknown"] = str(uconf[-1]["unknown"])
    # H3, the tier rubric, as the lab's script scores it
    rub = [x for x in RB.tier_rubric(d, ev) if x.get("measurable")]
    good = sum(1 for x in rub if x["score"] == 3)
    if f"{good} of {len(rub)}" not in cards["H3"]["estimate"]:
        stop("the rubric does not reproduce H3")
    M["RubricGood"], M["RubricScored"] = str(good), str(len(rub))
    paths = {(i["run"], i["name"]): i.get("paths") for i in d.items}
    wide = [x for x in rub if paths[(x["run"], x["name"])] == ["shop/**"]]
    fails = [x for x in rub if x["score"] < 3]
    if any(x not in wide or x["area"] or not (x["form"] and x["scope"]) for x in fails):
        stop("an H3 failure is not a shop-wide rule failing the third part only")
    if not all(x["scope"] for x in rub):
        stop("the lab's script no longer passes every path-scoped item on scope")
    M["ShopWidePassed"] = str(sum(1 for x in wide if x["area"]))
    M["ShopWideLo"] = f"{100 * min(min(x['own_rate'], x['other_rate']) for x in wide):.0f}" + r"\%"
    M["ShopWideHi"] = f"{100 * max(max(x['own_rate'], x['other_rate']) for x in wide):.0f}" + r"\%"
    M["ShopWideMargin"] = f"{100 * max(x['own_rate'] - x['other_rate'] for x in wide if x['area']):.2f}"
    # read as written (§11.2), a rule on shop/** reaches every family (scope), and an exporter
    # duty, which the task names, belongs in a skill (form): an upper bound on what passes
    kind_of = {(i["run"], i["name"]): i.get("kind") for i in d.items}
    c_rules = [x for x in rub if fam_of[(x["run"], x["name"])] == "C" and kind_of[(x["run"], x["name"])] == "rule"]
    M["ExporterRules"] = str(len(c_rules))
    M["RubricLiteralMax"] = str(len(rub) - len(wide) - len(c_rules))
    if any(x in wide for x in c_rules):
        stop("an exporter rule is also a shop-wide rule")

    # the loop's own KILLs that rest on a regression gate in their confirm, and those that
    # failed nothing else
    def confirm_failed(c):
        cf = [s for s in c["sweeps"] if s["phase"] == "confirm"]
        return set(cf[-1]["failed"]) if cf else set()
    reg = [c for c in cs if c["verdict"] == "KILL" and {"gate2", "gate3"} & confirm_failed(c)]
    M["LoopKilledRegression"] = str(len(reg))
    M["LoopKilledRegressionOnly"] = str(sum(1 for c in reg if confirm_failed(c) <= {"gate2", "gate3"}))
    if [c["name"] for c in reg if confirm_failed(c) <= {"gate2", "gate3"}] != [killed[0]["name"]]:
        stop("the one KILL on a regression alone is not the narrow run's clock rule")

    # ---- the gate test ------------------------------------------------------------------
    screen = lambda g: g.get("screen") or {}
    pos = [g for g in gates_all if g["type"] == "positive"]
    plac = [g for g in gates_all if g["type"].startswith("placebo")]
    M["FisherP"] = f"{S.fisher(sum(g['verdict'] == 'KEEP' for g in pos), sum(g['verdict'] != 'KEEP' for g in pos), sum(g['verdict'] == 'KEEP' for g in plac), sum(g['verdict'] != 'KEEP' for g in plac))[1]:.3f}"
    if any(screen(g).get("candidate_fired_runs") for g in plac):
        stop("a placebo was opened on its screen")
    if any(not any(x.startswith("gate5") for x in screen(g).get("gates_failed", []))
           for g in plac if screen(g).get("verdict") == "KILL"):
        stop("a placebo was killed without failing gate 5")
    if any(t["base"] or t["cand"] for g in plac if screen(g).get("verdict") == "RERUN" for t in screen(g)["per_task"]):
        stop("an unscored placebo screen had a task that passed in some run")
    runs8 = {screen(g).get("rollouts", 0) // 2 for g in gates_all}
    if len(runs8) != 1:
        stop("the screens ran different numbers of candidate rollouts")
    M["ScreenCandRollouts"] = str(runs8.pop())
    if any(screen(g).get("candidate_visible_runs") != int(M["ScreenCandRollouts"]) for g in plac):
        stop("a placebo was not listed in every candidate rollout of its screen")
    noise = [g for g in gates_all if screen(g).get("gain", 0) > 0 and screen(g).get("candidate_fired_runs") == 0]
    M["GateNoiseGain"] = str(len(noise))
    M["GateNoisePlacebo"] = str(sum(1 for g in noise if g["type"].startswith("placebo")))
    M["GateNoiseHarmful"] = str(sum(1 for g in noise if g["type"] == "harmful"))
    M["GateNoisePositive"] = str(sum(1 for g in noise if g["type"] == "positive"))
    # how many of those gains were a single run on a single task (one delta of 1/k)
    def single(g):
        ups = [t["delta"] for t in screen(g)["per_task"] if t["delta"] > 0]
        return len(ups) == 1 and abs(ups[0] - 1 / screen(g)["k"]) < 1e-9
    M["GateNoiseSingle"] = str(sum(1 for g in noise if single(g)))
    hrules = [g for g in gates_all if g["type"] == "harmful" and screen(g).get("candidate_tier") != "always"]
    if any(screen(g).get("verdict") != "RERUN" or not screen(g).get("uninformative")
           or screen(g).get("candidate_fired_runs") != screen(g).get("rollouts", 0) // 2 for g in hrules):
        stop("the harmful rules were not all loaded in every rollout and left unscored")
    M["HarmfulRules"] = str(len(hrules))
    pathless = [g["name"] for g in hrules if screen(g).get("candidate_tier") == "rule-always"]
    if len(pathless) != 1:
        stop("the gate test has not exactly one harmful rule without paths")
    M["HarmfulPathlessRule"] = pathless[0]
    if sum(1 for g in hrules if screen(g).get("protected_broken")) != 1:
        stop("the text says one harmful screen broke a task that passed without it")
    lost = [g for g in pos if g["verdict"] != "KEEP"]
    if any(screen(g).get("candidate_tier") != "always" or screen(g).get("candidate_fired_runs") for g in lost):
        stop("a lost positive was not an always-on skill that was never opened")
    if sorted(screen(g).get("candidate_tier") for g in pos if g["verdict"] == "KEEP") != ["gated", "rule"]:
        stop("the kept positives are not a rule and a gated skill")
    # accept-all: the one run that measured it, and the burial it undoes
    acc_runs = [r for r in ev if any(True for _ in d.bench(runs=[r], arms=("accept-all",), split="holdout"))]
    if len(acc_runs) != 1:
        stop("accept-all ran in more than one run")
    M["AcceptAllRun"] = acc_runs[0]
    buried = [c for c in cs if c["run"] == acc_runs[0] and c["verdict"] != "KEEP"]
    if len(buried) != 1 or buried[0]["verdict"] != "RERUN" or buried[0]["recorded"] != "buried":
        stop("accept-all does not add exactly one candidate the rules left unscored")
    bs = [r for r in d.rollouts if r.get("source") == "sweep" and r.get("sweep") == buried[0]["sweeps"][0]["sweep"]]
    if len(buried[0]["sweeps"]) != 1 or not bs or not all(r["pass"] for r in bs):
        stop("the buried candidate's only sweep is not a screen that passed every run")
    loss = {}
    for f in "ACE":
        r = RB.arm_pair(d, acc_runs, "evolved", "accept-all", families=(f,), complete_case=False)
        M[f"AcceptAllFam{f}"], loss[f] = pts(r["mean"]), r["mean"]
    if fam_all.get((acc_runs[0], buried[0]["name"])) != "E" or not abs(loss["E"]) < min(abs(loss["A"]), abs(loss["C"])):
        stop("accept-all's loss is not mostly outside the family of the rule it adds")
    # ... though the added rule, on shop/**, was in context in every A and C rollout
    for f in "AC":
        rs_ = [r for r in d.bench(runs=acc_runs, arms=("accept-all",), split="holdout")
               if r.get("family") == f and r.get("valid", 1)]
        if not rs_ or not all(buried[0]["name"] in (r.get("fired") or []) for r in rs_):
            stop("the added rule was not in context in every A and C rollout of accept-all")
    racc = RB.arm_pair(d, acc_runs, "evolved", "accept-all", families=fams, complete_case=False)
    if pts(racc["mean"]) != M["AcceptAllEst"]:
        stop("accept-all's pair is not the scorecard's H6")
    M["AcceptAllP"] = f"{racc['p']:.3f}"

    # ---- the ablations, in the one run that measured them -------------------------------
    run1 = M["KitchenRun"]
    if run1 != M["AARun"]:
        stop("the A/A pair and the ablations were measured in different runs")
    # one later batch: every other arm started after the primary arms ended, interleaved
    tt = defaultdict(list)
    for r in d.bench(runs=[run1], split="holdout"):
        tt[r["arm"]].append(r["t"])
    later = [a for a in tt if a not in ("none", "evolved")]
    if (min(min(tt[a]) for a in later) <= max(max(tt["none"]), max(tt["evolved"]))
            or max(min(tt[a]) for a in later) >= min(max(tt[a]) for a in later) or "none2" not in later):
        stop("the ablation arms and none2 did not run as one later batch")

    def arm(a, f=fams):
        return RB.arm_pair(d, [run1], "evolved", a, families=f, complete_case=False)
    cells = arm("kitchen")["cells"]
    M["AblEvolvedRate"] = rate(sum(v[1] for v in cells.values()) / len(cells))
    for a, key in (("kitchen", "Kitchen"), ("flat", "Flat"), ("desc-only", "Desc"), ("ideal", "Ideal"),
                   ("none", "None")):
        r = arm(a)
        M[f"Abl{key}Rate"] = rate(sum(v[2] for v in r["cells"].values()) / len(r["cells"]))
        # the gap, evolved minus the arm, as the introduction quotes kitchen's
        M[f"Abl{key}Gap"] = tex(f"{-100 * r['mean']:.1f}")
        M[f"Abl{key}GapLo"], M[f"Abl{key}GapHi"] = tex(f"{-100 * r['hi'] + 0.0:+.1f}"), tex(f"{-100 * r['lo'] + 0.0:+.1f}")
    if (M["AblKitchenGap"], M["AblKitchenGapLo"], M["AblKitchenGapHi"]) != (M["KitchenGap"], M["KitchenLo"], M["KitchenHi"]):
        stop("the kitchen gap is not the introduction's")
    h7 = need(r"always-on (\d+) → (\d+) chars", cards["H7"]["estimate"], "H7")
    M["FlatChars"] = f"{int(h7.group(2)):,}".replace(",", "{,}")
    # H7 the way its margin reads it, flat minus evolved, for the hypothesis table
    r = arm("flat")
    M["FlatMinusEst"], M["FlatMinusLo"], M["FlatMinusHi"] = pts(r["mean"]), pts(r["lo"] + 0.0), pts(r["hi"] + 0.0)
    if (M["FlatMinusLo"], M["FlatMinusHi"]) != tuple(map(tex, interval(cards["H7"]["interval"]))):
        stop("flat minus evolved is not the scorecard's H7 interval")
    # per family: where each arm's text reached the agent, and where it did not
    def fam_rate(a, f):
        rs_ = [r for r in d.bench(runs=[run1], arms=(a,), split="holdout") if r.get("family") == f and r.get("valid", 1)]
        return sum(r["pass"] for r in rs_) / len(rs_)
    M["FlatRateC"], M["EvolvedRunOneC"] = rate(fam_rate("flat", "C"), 0), rate(fam_rate("evolved", "C"), 0)
    if min(fam_rate("flat", f) for f in "ABE") < 1:
        stop("flat does not pass every A, B and E rollout")
    sk = [n for (r_, n), f in fam_of.items() if r_ == run1 and f == "C"]
    fc = [r for r in d.bench(runs=[run1], arms=("flat",), split="holdout") if r.get("family") == "C" and r.get("valid", 1)]
    if len(sk) != 1 or any(sk[0] in (r.get("fired") or []) for r in fc) or not all(sk[0] in (r.get("visible") or []) for r in fc):
        stop("flat's exporter skill was not listed in every C rollout and opened in none")
    M["DescRateC"] = rate(fam_rate("desc-only", "C"), 0)
    # H12 is stated per family; C is the one family whose skill desc-only could rewrite
    M["NoneRunOneC"] = rate(fam_rate("none", "C"), 0)
    rd = RB.arm_pair(d, [run1], "none", "desc-only", families=("C",), complete_case=False)
    rf = RB.arm_pair(d, [run1], "none", "evolved", families=("C",), complete_case=False)
    share, slo, shi = S.share_recovered(rd["cells"], rf["cells"])
    M["DescShareC"], M["DescShareCLo"], M["DescShareCHi"] = (rate(x, 0) for x in (share, slo, shi))
    if not (share < 0.5):
        stop("desc-only's share on C meets the per-family margin")
    dc = [r for r in d.bench(runs=[run1], arms=("desc-only",), split="holdout") if r.get("family") == "C" and r.get("valid", 1)]
    M["DescOpenedC"], M["DescRolloutsC"] = str(sum(1 for r in dc if sk[0] in (r.get("fired") or []))), str(len(dc))
    M["IdealRateA"], M["IdealRateE"] = rate(fam_rate("ideal", "A"), 0), rate(fam_rate("ideal", "E"), 0)
    M["NoneRunOneA"], M["NoneRunOneE"] = rate(fam_rate("none", "A"), 0), rate(fam_rate("none", "E"), 0)
    ideal = [r for r in d.bench(runs=[run1], arms=("ideal",), split="holdout") if r.get("valid", 1)]
    runs_meta = {r["run"]: r for r in (json.loads(l) for l in (DATA / "runs.jsonl").read_text().splitlines() if l.strip())}
    ideal_skills = runs_meta[run1]["arms"]["ideal"]["skills"]
    always = [s for s in ideal_skills if all(s in (r.get("visible") or []) for r in ideal)]
    M["IdealAlwaysSkills"] = str(len(always))
    M["IdealRollouts"] = str(len(ideal))
    if any(set(always) & set(r.get("fired") or []) for r in ideal):
        stop("an always-on skill of the ideal arm was opened")
    h12 = need(r"(\d+)% of the gain recovered · items actually rewritten — \w+: (\d+) of (\d+)",
               cards["H12"]["estimate"], "H12")
    M["DescRecovered"], M["DescRewritten"], M["DescItems"] = h12.group(1) + r"\%", h12.group(2), h12.group(3)
    M["DescRecoveredLo"], M["DescRecoveredHi"] = (x + r"\%" for x in interval(cards["H12"]["interval"]))

    # ---- a stronger model --------------------------------------------------------------
    mc = [r["run"] for r in d.of_kind("model-change")]
    src = d.same_harness(mc)
    weak = RB.arm_pair(d, src, "none", "evolved", families=fams, complete_case=False)
    strong = RB.arm_pair(d, mc, "none", "evolved", families=fams, complete_case=False)
    if (pts(weak["mean"]), pts(strong["mean"])) != (M["HaikuGain"], M["SonnetGain"]):
        stop("the model change's gains are not the scorecard's H14")
    M["HaikuLo"], M["HaikuHi"] = pts(weak["lo"]), pts(weak["hi"])
    for key, r in (("Haiku", weak), ("Sonnet", strong)):
        M[f"{key}None"] = rate(sum(v[1] for v in r["cells"].values()) / len(r["cells"]))
        M[f"{key}Evolved"] = rate(sum(v[2] for v in r["cells"].values()) / len(r["cells"]))
    # the exporter family: the largest gain left under the stronger model, but not a clear one
    sfam = {f: RB.arm_pair(d, mc, "none", "evolved", families=(f,), complete_case=False) for f in fams}
    if max(sfam, key=lambda f: sfam[f]["mean"]) != "C" or not sfam["C"]["lo"] <= 0 <= sfam["C"]["hi"]:
        stop("under the stronger model C is not the largest gain, or its interval excludes zero")
    M["SonnetFamCEst"], M["SonnetFamCLo"], M["SonnetFamCHi"] = pts(sfam["C"]["mean"]), pts(sfam["C"]["lo"]), pts(sfam["C"]["hi"])
    sb = [r for r in d.bench(runs=mc, arms=("none",), split="holdout") if r.get("family") == "B" and r.get("valid", 1)]
    if not sb or not all(r["pass"] for r in sb):
        stop("the stronger model did not pass every money task without a harness")
    pr = [json.loads(l) for l in (DATA / "prune.jsonl").read_text().splitlines() if l.strip()]
    if len({p["from_run"] for p in pr}) != 1:
        stop("the prune test ran on more than one run's copy")
    M["PruneRun"] = pr[0]["from_run"]
    if M["PruneRun"] != "R1" or M["ModelChangeSource"] != M["PruneRun"]:
        stop("the prune test and the model change are not on R1's harness, whose items §4 counts")
    pm = [json.loads(l) for l in (DATA / "prune-model-change.jsonl").read_text().splitlines() if l.strip()]
    if (sorted(p["item"] for p in pm if p["verdict"] == "ACCEPT") != ["billing-helpers", "exporter-checklist"]
            or sorted(p["item"] for p in pm if p["verdict"] == "REJECT") != ["changelog-requirement", "shop-clock-rule"]):
        stop("the stronger model's prune verdicts are not the ones the text names")

    # the prune sweeps themselves (data/prune-sweeps.jsonl, from extract_prune.py;
    # the lab's export records only the verdicts), scored again by score.sh's replace mode
    rtol, minnet = float(M["RegressionTolerance"]), int(M["MinNetRuns"])
    prs = [json.loads(l) for l in (DATA / "prune-sweeps.jsonl").read_text().splitlines() if l.strip()]

    def score_replace(rs):
        k, item = rs[0]["k"], rs[0]["removed"]
        valid = [r for r in rs if r["valid"]]
        if len(valid) != len(rs) or any(r["fired"] is None for r in valid):
            stop(f"a prune sweep of {item} is not scorable")
        by = defaultdict(list)
        for r in valid:
            by[(r["arm"], r["task"])].append(r["pass"])
        exposed = {r["task"] for r in valid if r["arm"] == "base" and item in (r["visible"] or [])}
        tasks = sorted(t for t in {r["task"] for r in valid} if t in exposed
                       and len(by[("base", t)]) >= k and len(by[("cand", t)]) >= k)
        rate_ = lambda arm, t: sum(by[(arm, t)]) / len(by[(arm, t)])
        delta = {t: rate_("cand", t) - rate_("base", t) for t in tasks}
        kn = round(k * sum(delta.values()))
        drop = max([max(-v, 0) for v in delta.values()] or [0])
        plost = [t for t in tasks if rate_("base", t) == 1 and rate_("cand", t) < 1]
        fired = sum(1 for r in valid if r["arm"] == "base" and item in (r["fired"] or []))
        verdict = ("REJECT" if kn <= -minnet or drop > rtol or plost else
                   "UNMEASURED" if fired == 0 else "ACCEPT")
        return {"verdict": verdict, "kn": kn, "drop": drop, "plost": plost, "fired": fired,
                "base": sum(1 for r in valid if r["arm"] == "base"),
                "lost": [t for t, v in delta.items() if v < 0]}
    groups = defaultdict(list)
    for r in prs:
        groups[(r["run"], r["removed"])].append(r)
    sc = {key: score_replace(rs) for key, rs in groups.items()}
    recorded = {("PRUNE", p["item"]): p["verdict"] for p in pr if p["verdict"] in ("ACCEPT", "REJECT")}
    recorded.update({("M1", p["item"]): p["verdict"] for p in pm})
    if sorted(recorded) != sorted(sc) or any(sc[key]["verdict"] != v for key, v in recorded.items()):
        stop("the prune sweeps, scored again, do not give the recorded verdicts")
    own = [sc[("PRUNE", p["item"])] for p in pr if not p.get("planted")]
    M["PruneOwnMinLoss"] = str(min(-s_["kn"] for s_ in own))
    kept_plant = [p["item"] for p in pr if p.get("planted") and p["verdict"] == "REJECT"]
    if len(kept_plant) != 1:
        stop("more than one planted item was kept")
    kp = sc[("PRUNE", kept_plant[0])]
    kpv = [r for r in groups[("PRUNE", kept_plant[0])] if r["arm"] == "base" and kept_plant[0] in (r["visible"] or [])]
    if kp["fired"] != 0 or len(kpv) != kp["base"]:
        stop("the kept placebo fired in its prune sweep, or was not listed in every base rollout")
    M["PrunePlaceboBase"], M["PrunePlaceboLostTasks"] = str(kp["base"]), str(len(kp["lost"]))
    # the gate test's two moment placebos were planted here byte for byte: how often opened
    bench = CORTEX / "lab" / "bench"
    moment = [p["item"] for p in pr if p.get("planted") and p.get("role", "").startswith("placebo")]
    if len(moment) != 2 or any((bench / "prune-plants" / n / "SKILL.md").read_bytes()
                               != (bench / "gate-candidates" / "placebo-moment" / n / "SKILL.md").read_bytes()
                               for n in moment):
        stop("the prune test's moment placebos are not the gate test's")
    pv = [r for r in prs if r["run"] == "PRUNE" and r["valid"]]
    M["PruneMomentListed"] = f"{sum(1 for r in pv for n in moment if n in (r['visible'] or [])):,}".replace(",", "{,}")
    M["PruneMomentOpened"] = str(sum(1 for r in pv for n in moment if n in (r["fired"] or [])))
    # under the stronger model: the changelog rule's loss, and the clock rule's single run
    sch, scl = sc[("M1", "changelog-requirement")], sc[("M1", "shop-clock-rule")]
    if not (sch["kn"] <= -minnet) or not (scl["kn"] > -minnet and scl["drop"] <= rtol and len(scl["plost"]) == 1
                                          and len(scl["lost"]) == 1):
        stop("the stronger model's two REJECTs are not as the text describes them")
    M["SonnetChangelogLoss"], M["SonnetClockLoss"] = str(-sch["kn"]), str(-scl["kn"])

    # ---- the second repository ----------------------------------------------------------
    h15 = cards["H15"]
    M["ExtAAEst"] = tex(need(r"([+-][0-9.]+) points", h15["estimate"], "H15").group(1))
    M["ExtAALo"], M["ExtAAHi"] = map(tex, interval(h15["interval"]))
    # its training, from the run's own records (data/external-training.json, written by
    # extract_external.py): the sessions, the tasks and lessons they left, and the cycles
    xtr = json.loads((DATA / "external-training.json").read_text())
    xruns = {e["run"] for e in (json.loads(l) for l in (DATA / "external.jsonl").read_text().splitlines() if l.strip())}
    if xruns != {xtr["run"]} or not xtr["base"].startswith(M["SecondRepoBase"]) or not xtr["cycles"]:
        stop("the second repository's training rows are not the benchmark's run and commit, or hold no cycle")
    M["ExtTasks"], M["ExtLessons"] = str(xtr["tasks"]), str(xtr["lessons"])
    M["ExtFirstTime"] = str(sum(1 for x in xtr["sessions"] if x["verdicts"] == ["ok"]))
    if len(xtr["sessions"]) != xtr["tasks"] or M["ExtLessons"] != "1":
        stop("the second repository's sessions did not each leave a task, or its single lesson is not one")
    xrows = [json.loads(l) for l in (DATA / "external.jsonl").read_text().splitlines() if l.strip()]
    if (any(c["verdict"] != "BARREN" for c in xtr["cycles"]) or xtr["kept"]
            or not all(e["harness_identical"] and not e["evolved_items"] for e in xrows)):
        stop("a cycle on the second repository was not barren, or the loop kept an item there")

    # ---- predicting a verdict -----------------------------------------------------------
    h16 = need(r"relevance: lowest KEPT (\d+)% vs highest BURIED (\d+)% · breadth: (\d+)% vs (\d+)%",
               cards["H16"]["estimate"], "H16").groups()
    floor = float(need(r'"relevance_floor":\s*([0-9.]+)', at_tag("bin/jev.py"), "the relevance floor").group(1))
    M["RelevanceFloor"] = f"{floor:.2f}"
    M["RelevanceFloorPct"] = f"{100 * floor:.0f}" + r"\%"     # relevance is quoted in percent
    flagged = [s for s in d.scope if isinstance(s.get("relevance"), (int, float)) and s["relevance"] < floor]
    t19 = {r["run"]: r for r in csv.DictReader(open(CORTEX / "lab" / "reports" / "tables" / "T19-scope.csv"))}
    # the development run, reported apart: its candidates (the journal's fates) do not
    # separate on either predictor, which the text says
    d0s = [s_ for s_ in d.scope if s_.get("run") in d.development]
    jf = lambda s_: d.journal_fate(s_["run"], s_["candidate"])
    for key in ("relevance", "breadth"):
        kv = [s_[key] for s_ in d0s if jf(s_) == "kept" and isinstance(s_.get(key), (int, float))]
        bv = [s_[key] for s_ in d0s if jf(s_) == "killed-regression" and isinstance(s_.get(key), (int, float))]
        if not kv or not bv or min(kv) > max(bv):
            stop(f"the development run's {key} separates, or is missing")
    # the same question on the evaluation runs alone (§4: the development run is never
    # pooled), against the candidates score.sh killed on a regression gate
    vby = {(c["run"], c["name"]): c for c in cs}
    ksc = [s_ for s_ in d.scope if vby.get((s_.get("run"), s_.get("candidate")), {}).get("verdict") == "KEEP"]
    rsc = [s_ for s_ in d.scope if (s_.get("run"), s_.get("candidate")) in {(c["run"], c["name"]) for c in reg}]
    if len(ksc) != len(cs) - int(M["LoopKilled"]) - int(M["LoopUnscored"]) or len(rsc) != len(reg):
        stop("the replay does not cover every evaluation candidate")
    num = lambda xs, key: [x[key] for x in xs if isinstance(x.get(key), (int, float))]
    for key, name in (("relevance", "Rel"), ("breadth", "Breadth")):
        lo_k, hi_r = min(num(ksc, key)), max(num(rsc, key))
        if lo_k > hi_r:
            stop(f"{key} separates on the evaluation runs")
        M[f"{name}KeptLowEval"], M[f"{name}KilledHighEval"] = rate(lo_k, 0), rate(hi_r, 0)
    fe = [s_ for s_ in flagged if s_.get("run") in ev]
    M["FloorFlaggedBuriedEval"] = str(sum(1 for s_ in fe if s_.get("fate") != "kept"))
    M["FloorFlaggedKeptEval"] = str(sum(1 for s_ in fe if s_.get("fate") == "kept"))
    M["FloorSavedEval"] = f"{sum(s_.get('cost_usd') or 0 for s_ in fe if s_.get('fate') != 'kept'):.2f}"
    # the lab's scorecard and T19 state the same comparison on the same runs
    if (tuple(x + r"\%" for x in h16) != (M["RelKeptLowEval"], M["RelKilledHighEval"],
                                          M["BreadthKeptLowEval"], M["BreadthKilledHighEval"])
            or t19["**false alarms, evaluation runs**"]["kind"] != M["FloorFlaggedKeptEval"]
            or t19["**counterfactual, evaluation runs**"]["kind"] != M["FloorFlaggedBuriedEval"]
            or f"**${M['FloorSavedEval']}** saved" != t19["**counterfactual, evaluation runs**"]["cost"]):
        stop("H16 or the relevance floor's counterfactual disagrees with the lab's report")
    h17 = re.findall(r"predicted (\d+)% vs measured (\d+)%", cards["H17"]["estimate"])
    M["JudgeItems"] = str(len(h17))
    M["JudgeItemsDev"] = "2"                   # checked below: the development run's kept gated skills
    M["JudgeOver"] = str(sum(1 for p, m_ in h17 if int(p) > int(m_)))
    M["JudgeTied"] = str(max(sum(1 for p, _ in h17 if p == q) for q, _ in h17))
    M["JudgeMissMax"] = str(max(int(p) - int(m_) for p, m_ in h17))
    if f"n = {len(h17)} items" not in cards["H17"]["interval"]:
        stop("H17 is not over the items the scorecard lists")
    # they are the path-gated skills the runs kept, two of them in the development run
    gated = [i for i in d.items if i.get("fate") == "kept" and i.get("kind") == "skill" and i.get("paths")
             and i["run"] in list(ev) + list(d.development)]
    if len(gated) != len(h17) or str(sum(1 for i in gated if i["run"] in d.development)) != M["JudgeItemsDev"]:
        stop("H17's items are not the kept gated skills, two of them the development run's")
    low = re.findall(r"([\w-]+) predicted (\d+)% vs", cards["H17"]["estimate"])
    low = [n for n, p_ in low if int(p_) < 100]
    d0names = {i["name"] for i in gated if i["run"] in d.development}
    evnames = {i["name"] for i in gated if i["run"] in ev}
    if len(low) != 1 or low[0] not in d0names or low[0] in evnames:
        stop("the one prediction below 100% is not a development-run skill")

    # ---- why held-out rollouts fail: the oracle's first failed check (figure in §5.1) ----
    cc = set.intersection(*[{x["task"] for x in d.bench(runs=[r], split="holdout")} for r in ev])
    why = defaultdict(lambda: defaultdict(int))
    for r in d.bench(runs=ev, arms=("none", "evolved"), split="holdout"):
        if r.get("valid", 1) and r["task"] in cc and r["family"] in fams and not r["pass"]:
            v = "rule" if r.get("verdict") == r["family"] else r.get("verdict")
            why[r["arm"]][v] += 1
            why[r["arm"]]["all"] += 1
            if v == "tampered":
                why[r["arm"]]["tampered_" + r["family"]] += 1
    M["FailNone"], M["FailEvolved"] = str(why["none"]["all"]), str(why["evolved"]["all"])
    M["FailRuleShareNone"] = rate(why["none"]["rule"] / why["none"]["all"], 0)
    M["FailRuleNone"], M["FailRuleEvolved"] = str(why["none"]["rule"]), str(why["evolved"]["rule"])
    M["TamperedNone"], M["TamperedEvolved"] = str(why["none"]["tampered"]), str(why["evolved"]["tampered"])
    if any(k.startswith("tampered_") and k[-1] not in "CE" for a in why for k in why[a]):
        stop("the text says every changed test was in families C and E")
    cfail = [r for r in d.bench(runs=ev, arms=("evolved",), split="holdout")
             if r.get("valid", 1) and r["task"] in cc and r["family"] == "C" and not r["pass"]]
    M["FailCRuleEvolved"] = str(sum(1 for r in cfail if r.get("verdict") == "C"))

    # ---- what a held-out rollout costs, and what the loop cost (§5.4) -------------------
    def per(arm):
        rs = [r for r in d.bench(runs=ev, arms=(arm,), split="holdout") if r.get("valid", 1)]
        return {k: sum(r.get(k) or 0 for r in rs) / len(rs) for k in ("cost_usd", "turns", "secs", "tokens")}
    c0, c1 = per("none"), per("evolved")
    M["CostNone"], M["CostEvolved"] = f"{c0['cost_usd']:.3f}", f"{c1['cost_usd']:.3f}"
    M["CostRise"] = rate(c1["cost_usd"] / c0["cost_usd"] - 1, 0)
    # the rise by family: largest on exporters, whose rule asks for three more artefacts,
    # smallest on the control family, which has no rule to follow
    rise = {}
    for f in "ABCDE":
        cf = lambda arm: [r["cost_usd"] or 0 for r in d.bench(runs=ev, arms=(arm,), split="holdout")
                          if r.get("valid", 1) and r["family"] == f]
        a_, b_ = cf("none"), cf("evolved")
        rise[f] = (sum(b_) / len(b_)) / (sum(a_) / len(a_)) - 1
    if max(rise, key=rise.get) != "C" or min(rise, key=rise.get) != "D":
        stop("the cost rise is not largest on exporters and smallest on the control")
    M["CostRiseC"], M["CostRiseD"] = rate(rise["C"], 0), rate(rise["D"], 0)
    M["CostRiseLo"] = rate(min(rise[f] for f in "ABE"), 0)
    M["CostRiseHi"] = rate(max(rise[f] for f in "ABE"), 0)
    # under the stronger model the harness made rollouts cheaper, not dearer
    mcr = [r["run"] for r in d.of_kind("model-change")]
    sc_ = {arm: [r["cost_usd"] or 0 for r in d.bench(runs=mcr, arms=(arm,), split="holdout") if r.get("valid", 1)]
           for arm in ("none", "evolved")}
    sn, se = (sum(v) / len(v) for v in (sc_["none"], sc_["evolved"]))
    if not se < sn:
        stop("under the stronger model the evolved harness no longer costs less per rollout")
    M["SonnetCostNone"], M["SonnetCostEvolved"] = f"{sn:.3f}", f"{se:.3f}"
    M["TurnsNone"], M["TurnsEvolved"] = f"{c0['turns']:.1f}", f"{c1['turns']:.1f}"
    M["SecsNone"], M["SecsEvolved"] = f"{c0['secs']:.0f}", f"{c1['secs']:.0f}"
    sess = defaultdict(float)
    for s_ in sessions:
        sess[s_["run"]] += s_.get("cost_usd") or 0
    evolve = {r["run"]: r["agent_cost_usd"] - sess[r["run"]] for r in d.runs if r["run"] in ev}
    sweep_usd = {run: sum(s_.get("cost_usd") or 0 for s_ in sweeps if s_["run"] == run) for run in ev}
    M["EvolveCostLo"], M["EvolveCostHi"] = f"{min(evolve.values()):.2f}", f"{max(evolve.values()):.2f}"
    M["SweepCostLo"], M["SweepCostHi"] = f"{min(sweep_usd.values()):.2f}", f"{max(sweep_usd.values()):.2f}"
    M["SessionCostLo"] = f"{min(sess[r] for r in ev):.2f}"
    M["SessionCostHi"] = f"{max(sess[r] for r in ev):.2f}"
    if max(sweep_usd, key=sweep_usd.get) != narrow or max(
            ev, key=lambda r: sum(1 for c in cs if c["run"] == r)) != narrow:
        stop("the narrow run did not sweep the most candidates at the highest cost")

    # ---- invalid rollouts (§4 promises the count) ----------------------------------------
    # every exported rollout, the gate test's sweeps and the prune sweeps: only the
    # development run's sweeps had any
    bad = [r for r in d.rollouts if not r.get("valid", 1)]
    bad_gate = sum((g.get(ph) or {}).get("invalid", 0) or 0 for g in gates_all for ph in ("screen", "confirm"))
    if any(r["run"] not in d.development for r in bad) or bad_gate or any(not r["valid"] for r in prs):
        stop("a run other than the development run had invalid rollouts")
    M["InvalidDev"] = str(len(bad))

    reads(d, M, ev, cs)


def reads(d, M, ev, cs):
    """What rollouts read that their harness did not give them (data/transcripts.jsonl, from
    Claude Code's own session records; extract_transcripts.py), which Limitations quotes,
    and the sweeps the rules were applied to again. Every pattern the text states is checked."""
    from collections import Counter

    def stop(why):
        raise SystemExit(f"gen_numbers.py (limitations): {why} — revise the text")

    def rate(n, k):                             # a pass rate as typeset text: 23.6\%
        return f"{100 * n / k:.1f}" + r"\%"

    # ---- the sweeps the rules were applied to again ------------------------------------
    sw = [json.loads(l) for l in (DATA / "sweeps.jsonl").read_text().splitlines() if l.strip()]
    M["EvalSweeps"] = str(sum(1 for s in sw if s["run"] in ev))
    if sum(len(c["sweeps"]) for c in cs) != int(M["EvalSweeps"]):
        stop("the rules were not applied again to every sweep of the evaluation runs")
    # the one sweep whose exposure could not be read is the broad money rule's confirm
    unk = Counter(r.get("sweep") for r in d.rollouts
                  if r.get("source") == "sweep" and r["run"] in ev and r.get("fired") is None)
    if len(unk) != 1 or next(iter(unk.values())) != int(M["BroadMoneyUnknown"]):
        stop("unknown exposure is not confined to the broad money rule's sweep")

    # ---- what rollouts read: the transcripts ------------------------------------------
    T = [json.loads(l) for l in (DATA / "transcripts.jsonl").read_text().splitlines() if l.strip()]
    report = json.loads((DATA / "transcripts-coverage.json").read_text())
    cover = report["rollouts"]
    M["TranscriptRecorded"] = f"{sum(v['recorded'] for v in cover.values()):,}".replace(",", "{,}")
    M["TranscriptMatched"] = f"{sum(v['matched'] for v in cover.values()):,}".replace(",", "{,}")
    if any(v["recorded"] != v["matched"] for k, v in cover.items() if k.endswith("bench")):
        stop("a benchmark rollout has no transcript")
    M["TranscriptUnmatched"] = str(sum(v["recorded"] - v["matched"] for v in cover.values()))
    has = lambda r, *f: bool(set(f) & set(r["reads"]))
    sel = lambda **kw: [r for r in T if all((r.get(k) in v) if isinstance(v, tuple) else r.get(k) == v
                                             for k, v in kw.items())]
    # the loop's sweeps: two rollouts read a harvested fix, both in one screen's base arm,
    # on one task, in a sweep whose candidate the rules kept
    loop = sel(source="sweep", run=tuple(ev))
    leak = [r for r in loop if has(r, "fix", "store")]
    M["LoopSweepRollouts"] = f"{len(loop):,}".replace(",", "{,}")
    M["LoopFixReads"] = str(len(leak))
    if (len({(r["sweep"], r["task"], r["arm"], r["pass"]) for r in leak}) != 1 or leak[0]["arm"] != "base"
            or leak[0]["pass"] != 1 or leak[0]["phase"] != "screen"):
        stop("the loop's fix reads are not one screen's base arm, on one task, passing")
    held = [c for c in cs if any(s["sweep"] == leak[0]["sweep"] for s in c["sweeps"])]
    if len(held) != 1 or held[0]["verdict"] != "KEEP":
        stop("the screen whose base arm read a fix is not a candidate the rules kept")
    M["LoopFixTask"] = leak[0]["task"]
    # the benchmark's no-harness arm, R1 to R4
    none = sel(source="bench", run=tuple(ev), arm="none")
    nh = [r for r in none if r["split"] == "holdout"]
    M["NoneBenchRollouts"] = str(len(none))
    M["NoneHeldRollouts"] = str(len(nh))
    M["NoneHeldNames"] = str(sum(has(r, "names") for r in nh))
    M["NoneHeldText"] = str(sum(has(r, "text") for r in nh))
    M["NoneBenchNames"] = str(sum(has(r, "names") for r in none))
    M["NoneBenchText"] = str(sum(has(r, "text") for r in none))
    M["NoneBenchFix"] = str(sum(has(r, "fix", "store") for r in none))
    if any(has(r, "fix", "store") for r in nh) or [r["pass"] for r in none if has(r, "fix", "store")] != [0]:
        stop("the no-harness arm's one fix read is not a failed training rollout")
    rule = [r for r in nh if r["family"] in load.RULE_FAMILIES]
    seen = [r for r in rule if has(r, "names")]
    unseen = [r for r in rule if not has(r, "names")]
    M["NoneNamesN"], M["NoneNamesPass"] = str(len(seen)), rate(sum(r["pass"] for r in seen), len(seen))
    M["NoneNoNamesN"], M["NoneNoNamesPass"] = str(len(unseen)), rate(sum(r["pass"] for r in unseen), len(unseen))
    if not sum(r["pass"] for r in seen) / len(seen) < sum(r["pass"] for r in unseen) / len(unseen):
        stop("the no-harness rollouts that saw the items' names no longer pass less often")
    # the ablation arms of R1 that lack the run's items, and desc-only's replaced bodies
    abl = sel(source="bench", run="R1", arm=("none2", "kitchen", "ideal"))
    M["AblLackRollouts"] = str(len(abl))
    M["AblLackNames"] = str(sum(has(r, "names") for r in abl))
    M["AblLackText"] = str(sum(has(r, "text") for r in abl))
    desc = sel(source="bench", run="R1", arm="desc-only")
    M["DescBodySeen"] = str(sum(has(r, "text") for r in desc))
    M["DescBodyRollouts"] = str(len(desc))
    # on the exporter family, the one whose skill the arm rewrote, its passes came from these
    dc = [r for r in desc if r["family"] == "C"]
    M["DescBodySeenC"] = str(sum(has(r, "text") for r in dc))
    M["DescPassC"] = str(sum(r["pass"] for r in dc))
    if sum(r["pass"] for r in dc if has(r, "text")) != sum(r["pass"] for r in dc) or not dc:
        stop("a desc-only exporter pass came from a rollout that did not print the replaced body")
    if f"{100 * sum(r['pass'] for r in dc) / len(dc):.0f}" + r"\%" != M["DescRateC"]:
        stop("desc-only's exporter pass rate is not the one §5 quotes")
    # the gate test: nothing read
    gate = sel(source="sweep", run="GATE")
    M["GateRollouts"] = f"{len(gate):,}".replace(",", "{,}")
    if any(r["reads"] for r in gate):
        stop("a gate-test rollout read something through git")
    # /prune's removal arm: the removed item, through git
    def removal(run):
        rs = sel(source="sweep", run=run, arm="cand")
        return rs, [r for r in rs if has(r, "text")]
    hr, ht = removal("PRUNE")
    M["PruneRemovalRollouts"], M["PruneRemovalText"] = str(len(hr)), str(len(ht))
    M["PruneRemovalNames"] = str(sum(has(r, "names") for r in hr))
    pr = {p["item"]: p["verdict"] for p in
          (json.loads(l) for l in (DATA / "prune.jsonl").read_text().splitlines() if l.strip())}
    if any(pr.get(r["removed"][0]) != "REJECT" for r in ht):
        stop("under the evaluation model, a removal rollout read an item the pass did not keep")
    # the stronger model: the no-harness arm, and the removal arm
    sn = sel(source="bench", run="M1", arm="none")
    M["SonnetNoneRollouts"], M["SonnetNoneText"] = str(len(sn)), str(sum(has(r, "text") for r in sn))
    M["SonnetNoneNames"] = str(sum(has(r, "names") for r in sn))
    snr = [r for r in sn if r["split"] == "holdout" and r["family"] in load.RULE_FAMILIES]
    rd, un = [r for r in snr if has(r, "text")], [r for r in snr if not has(r, "text")]
    M["SonnetReadN"], M["SonnetReadPass"] = str(len(rd)), str(sum(r["pass"] for r in rd))
    M["SonnetUnreadN"], M["SonnetUnreadPass"] = str(len(un)), str(sum(r["pass"] for r in un))
    if abs(sum(r["pass"] for r in rd) / len(rd) - sum(r["pass"] for r in un) / len(un)) > 0.05:
        stop("under the stronger model, reading the items changed the no-harness pass rate")
    mr, mt = removal("M1")
    M["SonnetRemovalRollouts"], M["SonnetRemovalText"] = str(len(mr)), str(len(mt))
    M["SonnetRemovalNames"] = str(sum(has(r, "names") for r in mr))
    pm = {p["item"]: p["verdict"] for p in
          (json.loads(l) for l in (DATA / "prune-model-change.jsonl").read_text().splitlines() if l.strip())}
    acc = [r for r in mr if pm.get(r["removed"][0]) == "ACCEPT"]
    ar, au = [r for r in acc if has(r, "text")], [r for r in acc if not has(r, "text")]
    M["SonnetAccReadN"], M["SonnetAccReadPass"] = str(len(ar)), str(sum(r["pass"] for r in ar))
    M["SonnetAccUnreadN"], M["SonnetAccUnreadPass"] = str(len(au)), str(sum(r["pass"] for r in au))
    if not sum(r["pass"] for r in ar) / len(ar) < sum(r["pass"] for r in au) / len(au):
        stop("the removal rollouts that read an accepted item no longer pass less often")
    sfix = [r for r in sel(run="M1") if has(r, "fix", "store")]
    M["SonnetStoreReads"] = str(len(sfix))
    # all of them the task store, never a later commit, and in both arms of each comparison
    arms_read = Counter((r["source"], r["arm"]) for r in sfix)
    if (any(has(r, "fix") for r in sfix) or not all(arms_read[k] for k in
            (("bench", "none"), ("bench", "evolved"), ("sweep", "base"), ("sweep", "cand")))):
        stop("under the stronger model, the store reads are not the task store in every arm")
    # structlog: the upstream implementation, in training and in the benchmark
    xt = sel(run="X1", source="session")
    M["XTrainSessions"], M["XTrainImpl"] = str(len(xt)), str(sum(has(r, "impl") for r in xt))
    xb = sel(run="X1", source="bench")
    xi, xo = [r for r in xb if has(r, "impl")], [r for r in xb if not has(r, "impl")]
    M["XBenchRollouts"], M["XBenchImpl"] = str(len(xb)), str(len(xi))
    M["XBenchImplPass"] = str(sum(r["pass"] for r in xi))
    M["XBenchOther"], M["XBenchOtherPass"] = str(len(xo)), str(sum(r["pass"] for r in xo))
    arms_ = Counter(r["arm"] for r in xi)
    M["XBenchImplNone"], M["XBenchImplEvolved"] = str(arms_["none"]), str(arms_["evolved"])
    M["XBenchImplFirst"] = str(sum(has(r, "impl_first") for r in xi))
    if not all(has(r, "impl_first") for r in xt if has(r, "impl")):
        stop("the structlog training session read the upstream code only after editing")
    if M["XBenchImplPass"] != M["XBenchImpl"] or M["XTrainImpl"] != "1":
        stop("a structlog rollout that printed the implementation failed, or training is not one session")
    if (not all(r.get("right_first_time") for r in xt if has(r, "impl"))
            or str(sum(r.get("right_first_time", 0) for r in xt)) != M["ExtFirstTime"]
            or M["XTrainSessions"] != M["ExtTasks"]):
        stop("the structlog session that read the fix did not pass at its first attempt, or the "
             "session records and the run's own records count its sessions differently")


if __name__ == "__main__":
    main()
