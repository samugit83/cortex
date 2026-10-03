"""tables.py — T1…T20, each from `reports/data/` and nothing else.

Every table writes both Markdown and CSV from one list of rows, so the two can
never disagree, and every one degrades to a row saying what is missing rather than
raising when a block of the programme has not run yet. A half-finished programme
should still rebuild, and the gaps should be visible in the report rather than in a
traceback.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import stats as S
from load import ARM_ORDER, DATA, FAMILIES, RULE_FAMILIES, Data, ci, pct, signed, table

TABLES = None          # set by rebuild.py


def out(name):
    return TABLES / name


def missing(name, title, what):
    return table(out(name), title, ["status"], [[f"not available: {what}"]])


# ------------------------------------------------------------------- T1-T2 --
def t1_the_lab(d):
    import types
    from pathlib import Path
    src = (Path(__file__).resolve().parents[3] / "lab" / "bin" / "scenarios.py").read_text()
    m = types.ModuleType("sc")
    exec(compile(src, "scenarios.py", "exec"), m.__dict__)
    rule = {"A": "every user-visible change gets a CHANGELOG line under [Unreleased]",
            "B": "amounts are integer cents; scale them with the rates helpers",
            "C": "a new exporter needs module, registry entry, docs row and golden file",
            "D": "— (control: no house rule)",
            "E": "read the time through shop.clock, never datetime.now()"}
    mistake = {"A": "fixes the code, forgets the CHANGELOG",
               "B": "int(rate.split('.')[0]) or float arithmetic",
               "C": "writes the exporter module and stops",
               "D": "—",
               "E": "calls date.today() directly"}
    check = {"A": "a new `+- ` line in CHANGELOG.md since the base commit",
             "B": "tools/lint.py, money", "C": "tools/lint.py, exporters",
             "D": "the task's own test and the suite", "E": "tools/lint.py, time"}
    form = {"A": "a moment -> always-on skill", "B": "an area it reads -> rule on shop/billing/**",
            "C": "an area it creates in -> gated skill on shop/plugins/**",
            "D": "nothing should be learned", "E": "repo-wide -> always-on skill"}
    body = []
    for f in "ABCDE":
        tr = [s for s in m.SCENARIOS if s["family"] == f and s["split"] == "train"]
        ho = [s for s in m.SCENARIOS if s["family"] == f and s["split"] == "holdout"]
        body.append([f, FAMILIES[f], rule[f], mistake[f], check[f], form[f], len(tr), len(ho)])
    return table(out("T1-the-lab"), "T1 · The lab: families, rules and task counts",
                 ["family", "what it is", "the house rule", "the usual mistake",
                  "what checks it", "the form the design predicts", "train", "holdout"], body,
                 note="The expected form is the design's prediction, written before any run. "
                      "Whether it is right is H3 and H11, not an assumption.")


def t2_scenarios(d):
    import types
    from pathlib import Path
    src = (Path(__file__).resolve().parents[3] / "lab" / "bin" / "scenarios.py").read_text()
    m = types.ModuleType("sc")
    exec(compile(src, "scenarios.py", "exec"), m.__dict__)
    excl = d.excluded()
    rounds = {sid: r for r, ids in m.ROUNDS.items() for sid in ids}
    body = []
    for s in m.SCENARIOS:
        where = [run for run, e in excl.items() if s["id"] in (e.get("excluded") or [])]
        body.append([s["id"], s["family"], s["split"], s["title"],
                     rounds.get(s["id"], "—"), s["test"],
                     "yes" if s.get("naive") is not None or s["family"] in "ABCE" else "—",
                     ", ".join(where) or "—"])
    return table(out("T2-scenarios"), "T2 · Scenario inventory",
                 ["id", "family", "split", "title", "round", "test",
                  "rule-breaking fix", "excluded from"], body,
                 note="A scenario is excluded from a run when, on that run's final code, its "
                      "test does not fail or its reference fix does not apply and pass "
                      "(PREREGISTRATION.md §5.1). Exclusion is identical in every arm.")


# ---------------------------------------------------------------------- T3 --
def t3_scorecard(d, verdicts):
    body = [[h["id"], h["hypothesis"], h.get("test", "—"), h.get("estimate", "—"),
             h.get("interval", "—"), h.get("margin", "—"), h.get("verdict", "INCONCLUSIVE"),
             h.get("evidence", "—")] for h in verdicts]
    return table(out("T3-scorecard"), "T3 · Hypothesis scorecard",
                 ["#", "hypothesis", "test", "estimate", "95% interval",
                  "margin", "verdict", "evidence"], body,
                 note="The hypotheses are PREREGISTRATION.md §1's. The margins of H2, H6, H7, H8, "
                      "H11 and H12 are its §11.1; the others were written into the analysis code "
                      "before the first evaluation run (commit a23bb26, 2026-09-20), the "
                      "pre-registration setting no number for them. DEVIATIONS.md records every "
                      "later change (D-22 for this version of the report).")


# ---------------------------------------------------------------------- T4 --
def t4_main(d):
    runs = d.evaluation or d.development
    if not runs:
        return missing("T4-main", "T4 · Main results", "no runs exported yet")
    rows_all = d.bench(runs=runs, arms=("none", "evolved"))
    # the complete-case set (every run's valid scenarios) is the primary, as in H1
    keep = {split: set(d.complete_case_tasks(runs, arms=("none", "evolved"), split=split))
            for split in ("holdout", "train")}
    rows = [r for r in rows_all if r["task"] in keep.get(r["split"], set())]
    body, ps, names = [], [], []
    for split in ("holdout", "train"):
        for f in list("ABCDE") + [None]:
            fams = [f] if f else list(RULE_FAMILIES)
            cs = S.cells(rows, "none", "evolved", families=fams, split=split)
            if not cs:
                continue
            sel = rows if f else [r for r in rows if r.get("family") in RULE_FAMILIES]
            k0, n0, p0 = S.rate(sel, split=split, arm="none", **({"family": f} if f else {}))
            k1, n1, p1 = S.rate(sel, split=split, arm="evolved", **({"family": f} if f else {}))
            w0, w1 = S.wilson(k0, n0), S.wilson(k1, n1)
            diff = S.paired_mean(cs)
            lo, hi, _ = S.two_way_bootstrap(cs)
            _, pval, ntask = S.permutation_p(rows, "none", "evolved", families=fams, split=split)
            label = f"{f} {FAMILIES[f]}" if f else "A+B+C+E pooled"
            body.append([split, label, ntask, n0 + n1,
                         f"{pct(p0)} {ci(*w0)}", f"{pct(p1)} {ci(*w1)}",
                         signed(diff), ci(lo, hi), f"{pval:.4f}", None])
            if split == "holdout" and f in RULE_FAMILIES:
                ps.append(pval)
                names.append(len(body) - 1)
    if ps:
        adj = S.holm(ps)
        for i, a in zip(names, adj):
            body[i][-1] = f"{a:.4f}"
    fams = list(RULE_FAMILIES)
    ca = S.cells(rows_all, "none", "evolved", families=fams, split="holdout")
    if ca:
        sel = [r for r in rows_all if r.get("family") in RULE_FAMILIES]
        k0, n0, p0 = S.rate(sel, split="holdout", arm="none")
        k1, n1, p1 = S.rate(sel, split="holdout", arm="evolved")
        lo, hi, _ = S.two_way_bootstrap(ca)
        _, pval, ntask = S.permutation_p(rows_all, "none", "evolved", families=fams, split="holdout")
        body.append(["holdout", "A+B+C+E pooled, every valid scenario (secondary)", ntask, n0 + n1,
                     f"{pct(p0)} {ci(*S.wilson(k0, n0))}", f"{pct(p1)} {ci(*S.wilson(k1, n1))}",
                     signed(S.paired_mean(ca)), ci(lo, hi), f"{pval:.4f}", None])
    return table(out("T4-main"), "T4 · Main results: family x arm x split",
                 ["split", "family", "tasks", "rollouts", "none", "evolved",
                  "paired diff", "bootstrap 95% CI", "permutation p", "Holm p"], body,
                 note="Rows are over the complete-case set, the scenarios valid in every run "
                      "(the primary, as in H1), except the last, which pools every valid "
                      "scenario. Rates are over rollouts with Wilson intervals (description only: they "
                      "ignore that repeats of one task are correlated). The paired difference "
                      "and its interval are over TASKS and RUNS, which is the inference. "
                      "Holm is applied across the four rule families on the holdout.")


# ---------------------------------------------------------------------- T5 --
def t5_trace(d):
    body = []
    for r in d.runs:
        for c in [c for c in d.cycles if c["run"] == r["run"]]:
            sw = [s for s in d.sweeps if s["run"] == r["run"] and s.get("candidate") == c.get("name")]
            rv = d.scored().get((r["run"], c.get("name")))
            body.append([r["run"], c.get("journal_index"), "yes" if c.get("is_cycle") else "no",
                         c.get("date"), c.get("name"), c.get("kind"), c.get("paths") or "—",
                         c.get("theme") or "—", c.get("verdict"),
                         rv["verdict"] if rv else "—",
                         ", ".join(sorted({s["phase"] for s in sw})) or "—",
                         sum(s["rollouts"] for s in sw) or "—",
                         f"${sum(s['cost_usd'] or 0 for s in sw):.2f}" if sw else "—",
                         ", ".join(c.get("gates_failed") or []) or "—"])
    # a candidate the /evolve agent swept and buried without writing a journal entry has no
    # cycle row; it gets one here, from its sweeps alone
    named = {(c["run"], c.get("name")) for c in d.cycles}
    for (run, name), c in sorted(d.scored().items()):
        if (run, name) not in named:
            sw = [s for s in d.sweeps if s["run"] == run and s.get("candidate") == name]
            body.append([run, "—", "no", (sw[0].get("started") or "")[:10] if sw else "—", name,
                         c.get("kind"), "—", "(no journal entry)", "—", c["verdict"],
                         ", ".join(sorted({s["phase"] for s in sw})) or "—",
                         sum(s["rollouts"] for s in sw) or "—",
                         f"${sum(s['cost_usd'] or 0 for s in sw):.2f}" if sw else "—", "—"])
    if not body:
        return missing("T5-trace", "T5 · Evolution trace", "no cycles exported yet")
    return table(out("T5-trace"), "T5 · Evolution trace, per run",
                 ["run", "#", "counted as a cycle", "date", "candidate", "kind", "paths",
                  "theme", "verdict (journal)", "verdict (score.sh)", "phases", "rollouts",
                  "cost", "gates failed (journal)"], body,
                 note="`counted as a cycle` is what `cortex cycle` counted: the journal also "
                      "carries the experimenter's notes and re-tests, which are not cycles. "
                      "The journal is written by the model that runs /evolve; `verdict "
                      "(score.sh)` is score.sh's rules applied again to the cycle's recorded "
                      "rollouts (analysis/rescore.py). Where the /evolve agent buried a "
                      "candidate that score.sh left undecided, the scorer's column reads RERUN.")


# ---------------------------------------------------------------------- T6 --
def t6_items(d):
    body = []
    for it in d.items:
        fire = d.firing(it["run"]).get(it["name"], {})
        byf = fire.get("by_family", {})
        own = _own_family(it["name"], d, it["run"])
        here = byf.get(own, {}) if own else {}
        other = {k: v for k, v in byf.items() if k != own}
        body.append([it["run"], it["name"], it["kind"], own or "—",
                     ", ".join(it.get("paths") or []) or "(none)",
                     it.get("chars"), it["fate"],
                     d.rule_fate(it["run"], it["name"]) or "—",
                     f"{fire.get('visible', 0)}/{fire.get('rollouts', 0)}",
                     f"{fire.get('fired', 0)}/{fire.get('rollouts', 0)}",
                     f"{here.get('fired', 0)}/{here.get('visible', 0)}" if here else "—",
                     f"{sum(v['fired'] for v in other.values())}/"
                     f"{sum(v['visible'] for v in other.values())}" if other else "—",
                     (it.get("why") or "").strip().replace("\n", " ")[:140] or "—"])
    if not body:
        return missing("T6-items", "T6 · Kept and buried items", "no items exported yet")
    return table(out("T6-items"), "T6 · Kept and buried items, across runs",
                 ["run", "name", "kind", "family", "paths", "chars", "fate",
                  "by score.sh", "in context", "invoked", "fired on its own family",
                  "fired elsewhere", "why buried (journal)"], body,
                 note="`in context` and `invoked` are over that run's benchmark rollouts in the "
                      "`evolved` arm. A rule is never 'invoked' by choice: it is loaded when the "
                      "agent reads a matching file, which is why its two columns are equal.")


def _own_family(name, d, run):
    """Which family an item is about.

    Order matters, and getting it wrong is silent. The first version read a
    keyword list over the journal theme, so `exporter-checklist` — whose theme
    mentioned the CHANGELOG in passing — classified as family A, and family C came
    out empty for a run that had plainly learned it.

    So the evidence is taken most-reliable first:
      1. the item's own `paths`, which are unambiguous for B and C;
      2. its name and its text, which say what it is about;
      3. the journal theme, only as a last resort.
    """
    item = next((i for i in d.items if i["run"] == run and i["name"] == name), None)
    paths = " ".join((item or {}).get("paths") or [])

    def hit(text, words):
        return any(w in text for w in words)

    # The NAME and the item's own words come first, and paths only after. Paths
    # alone mislead whenever a rule is scoped to files in another family's folder:
    # `shop-clock-narrow` lists shop/billing/invoice.py among its paths and is a
    # clock rule, not a billing one. Reading paths first put it in family B and
    # emptied family E for a run that had plainly learned it.
    WORDS = (("C", ("exporter", "plugin", "golden", "registry", "docs/exporters")),
             ("E", ("clock", "datetime", "date.today", "time.time")),
             ("A", ("changelog", "unreleased")),
             ("B", ("billing", "integer cent", "money", "rate", "percent_of")))
    # The NAME alone, first. A rule's body lists the paths it is scoped to, so
    # `shop-clock-narrow` — scoped to shop/billing/invoice.py among others — has
    # "billing" in its text and came out as family B, emptying family E for a run
    # that had obviously learned it. The name is the one place the author said
    # what the thing is about.
    low = name.lower()
    for fam, words in WORDS:
        if hit(low, words):
            return fam
    own = (((item or {}).get("description") or "") + " "
           + ((item or {}).get("text") or "")[:600]).lower()
    for fam, words in WORDS:
        if hit(own, words):
            return fam
    if "shop/plugins" in paths:
        return "C"
    if "shop/billing" in paths:
        return "B"
    c = next((c for c in d.cycles if c["run"] == run and c.get("name") == name), None)
    theme = (((c or {}).get("theme") or "") + " " + ((c or {}).get("layer") or "")).lower()
    for fam, words in (("C", ("exporter", "plugin", "golden")), ("B", ("billing", "money")),
                       ("E", ("clock", "datetime", "time")), ("A", ("changelog",))):
        if hit(theme, words):
            return fam
    return None


# ---------------------------------------------------------------------- T7 --
def t7_ablations(d):
    runs = d.evaluation or d.development
    rows = d.bench(runs=runs)
    arms = [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]
    if len(arms) < 2:
        return missing("T7-ablations", "T7 · Ablations", "only one arm measured so far")
    body = []
    for arm in arms:
        chars = {}
        for run in runs:
            chars = d.arms_of(run).get(arm) or chars
        sel = [r for r in rows if r["arm"] == arm and r["split"] == "holdout"]
        k_r, n_r, p_r = S.rate(sel, arm=arm)
        rulefam = [r for r in sel if r["family"] in RULE_FAMILIES]
        dfam = [r for r in sel if r["family"] == "D"]
        cs = S.cells(rows, "none", arm, families=list(RULE_FAMILIES), split="holdout")
        diff = S.paired_mean(cs) if arm != "none" else 0.0
        lo, hi, _ = S.two_way_bootstrap(cs) if arm != "none" else (0.0, 0.0, [])
        mean = lambda key, rs: (sum(r[key] for r in rs if isinstance(r.get(key), (int, float)))
                                / max(1, len([r for r in rs if isinstance(r.get(key), (int, float))])))
        body.append([arm, chars.get("always_on_chars", "?"), chars.get("claude_md_chars", "?"),
                     len(chars.get("skills", [])) + len(chars.get("rules", [])),
                     pct(sum(r["pass"] for r in rulefam) / len(rulefam)) if rulefam else "—",
                     pct(sum(r["pass"] for r in dfam) / len(dfam)) if dfam else "—",
                     signed(diff), ci(lo, hi),
                     f"{mean('tokens', sel):,.0f}", f"{mean('cost_usd', sel):.3f}",
                     f"{mean('secs', sel):.0f}", f"{mean('turns', sel):.1f}",
                     f"{mean('tool_calls', sel):.1f}"])
    return table(out("T7-ablations"), "T7 · Ablations: what each harness costs and buys",
                 ["arm", "always-on chars", "CLAUDE.md", "items", "A+B+C+E", "D",
                  "paired diff vs none", "95% CI", "tokens", "$", "s", "turns", "tool calls"],
                 body,
                 note="Always-on characters are CLAUDE.md plus what Cortex counts as always on: "
                      "a path-less rule's whole body and an always-on skill's description. "
                      "A gated skill and a path-scoped rule cost nothing until their area is touched.")


# ---------------------------------------------------------------------- T8 --
def t8_gates(d):
    if not d.gates:
        return missing("T8-gates", "T8 · Gate calibration", "the gate testbed has not run")
    by = defaultdict(list)
    for g in d.gates:
        by[g["type"]].append(g)
    body = []
    sv = lambda g: ((g.get("confirm") or {}).get("verdict") or (g.get("screen") or {}).get("verdict")
                    or g["verdict"])
    for typ, gs in sorted(by.items()):
        kept = sum(1 for g in gs if g["verdict"] == "KEEP")
        lo, hi = S.clopper_pearson(kept, len(gs))
        fired = [g for g in gs if g.get("fired_runs")]
        body.append([typ, len(gs), kept, sum(1 for g in gs if sv(g) == "KILL"),
                     sum(1 for g in gs if sv(g) == "RERUN"), len(gs) - kept,
                     f"{kept / len(gs):.0%}", f"[{lo:.0%}, {hi:.0%}]",
                     f"{len(fired)}/{len(gs)}",
                     f"{S.one_sided_upper(kept, len(gs)):.0%}"])
    pos = by.get("positive", [])
    plac = by.get("placebo-topic", []) + by.get("placebo-moment", [])
    note = ("KEEP, KILL and RERUN are score.sh's verdicts, after the confirm for a candidate "
            "that reached one. `stopped (procedure)` counts the candidates the pre-registered "
            "procedure stopped, which it does at any screen whose gain is not positive or whose "
            "candidate never fired, whatever score.sh said; a RERUN means no task in the screen "
            "could show a gain, so no gate judged the candidate. Clopper-Pearson intervals; the "
            "last column is the one-sided 95 % upper bound, which is the number to quote when "
            "nothing was kept.")
    if pos and plac:
        a = sum(1 for g in pos if g["verdict"] == "KEEP")
        c = sum(1 for g in plac if g["verdict"] == "KEEP")
        odds, p = S.fisher(a, len(pos) - a, c, len(plac) - c)
        note += f" Fisher's exact, positives against placebos: p = {p:.4g}."
    return table(out("T8-gates"), "T8 · Gate calibration against known answers",
                 ["candidate type", "n", "KEEP", "KILL", "RERUN", "stopped (procedure)",
                  "KEEP rate", "95% CI", "ever fired", "one-sided upper"], body, note=note)


# --------------------------------------------------------------------- T9 --
def t9_corrections(d):
    ev, ct = d.evaluation, d.control
    if not ev:
        return missing("T9-corrections", "T9 · Corrections", "no evaluation runs yet")
    body = []
    for fam in "ABCDE":
        cells = []
        for label, runs in (("evaluation", ev), ("control", ct), ("development", d.development)):
            ss = [s for s in d.sessions if s["run"] in runs and s.get("family") == fam]
            cells.append(f"{sum(s['corrections'] for s in ss)}/{len(ss)}" if ss else "—")
        ss_e = [s for s in d.sessions if s["run"] in ev and s.get("family") == fam]
        ss_c = [s for s in d.sessions if s["run"] in ct and s.get("family") == fam]
        rate_e = sum(s["corrections"] for s in ss_e) / len(ss_e) if ss_e else float("nan")
        rate_c = sum(s["corrections"] for s in ss_c) / len(ss_c) if ss_c else float("nan")
        body.append([fam, FAMILIES[fam], *cells,
                     f"{rate_e:.2f}" if rate_e == rate_e else "—",
                     f"{rate_c:.2f}" if rate_c == rate_c else "—",
                     f"{rate_e - rate_c:+.2f}" if rate_e == rate_e and rate_c == rate_c else "—"])
    return table(out("T9-corrections"), "T9 · Corrections per session, evaluation against control",
                 ["family", "what it is", "evaluation (corrections/sessions)", "control",
                  "development (D0)", "evaluation rate", "control rate", "difference"], body,
                 note="The control runs the SAME sessions with no /evolve at all, so its fall is "
                      "what the agent learns from the code it has already written. Only the "
                      "difference is evidence for H4.")


# -------------------------------------------------------------------- T10 --
def t10_prune(d):
    if not d.prune:
        return missing("T10-prune", "T10 · The prune experiment", "the prune testbed has not run")
    def fired(item):
        rs = [r for r in d.prune_sweeps if r["run"] == "PRUNE" and r["removed"] == item
              and r["arm"] == "base" and r.get("valid", 1)]
        return f"{sum(1 for r in rs if item in (r.get('fired') or []))}/{len(rs)}" if rs else "not swept"
    body = [[p.get("run"), p["item"], p.get("role", "—"), p.get("expected"), p.get("verdict"),
             "yes" if p.get("verdict") == p.get("expected") else "NO",
             fired(p["item"]), p.get("chosen_by", "—"),
             sum(1 for r in d.prune_sweeps if r["run"] == "PRUNE" and r["removed"] == p["item"]) or "—",
             (p.get("note") or "")[:120]] for p in d.prune]
    matched = sum(1 for p in d.prune if p.get("verdict") == p.get("expected"))
    return table(out("T10-prune"), "T10 · The prune experiment: planted items and their verdicts",
                 ["run", "item", "planted role", "expected", "verdict", "matches",
                  "fired in its sweep", "chosen by", "rollouts", "what the planted role expected"], body,
                 note=f"{matched} of {len(d.prune)} matched the expectation fixed in "
                      "PREREGISTRATION.md §8 before the testbed was built. `fired in its "
                      "sweep` is measured: the base rollouts of the item's own removal sweep "
                      "in which it fired (data/prune-sweeps.jsonl).")


# -------------------------------------------------------------------- T11 --
def t11_harvest(d):
    body = []
    for r in d.runs:
        ss = [s for s in d.sessions if s["run"] == r["run"]]
        if not ss:
            continue
        body.append([r["run"], r["kind"], len(ss),
                     sum(1 for s in ss if s.get("harvested")),
                     len(ss) - sum(1 for s in ss if s.get("harvested")),
                     sum(1 for s in ss if s.get("right_first_time")),
                     sum(1 for s in ss if not s.get("ended_ok")),
                     sum(1 for s in ss if s.get("hit_turn_cap")),
                     f"{sum(s['corrections'] for s in ss) / len(ss):.2f}"])
    if not body:
        return missing("T11-harvest", "T11 · Harvest quality", "no sessions exported yet")
    return table(out("T11-harvest"), "T11 · Harvest quality, per run",
                 ["run", "kind", "sessions", "harvested a task", "harvested nothing",
                  "right first time", "never reached ok", "hit the turn cap",
                  "corrections per session"], body)


# -------------------------------------------------------------------- T12 --
def t12_findings(d):
    """What the lab's own checks flagged after each session, counted from the shipped
    session rows. (An earlier version read the autopilot logs beside each run's
    repository; those do not ship, and it then reported that nothing had been flagged.)"""
    body = []
    for r in d.runs:
        ss = [s for s in d.sessions if s["run"] == r["run"]]
        if not ss:
            continue
        checks = (("a harvest recorded the previous session's commit as the task's base "
                   "(WRONG START)", sum(1 for s in ss if s.get("wrong_base"))),
                  ("a correction with no lesson written", sum(max(0, s["corrections"]
                   - (s.get("lessons_added") or 0)) for s in ss)),
                  ("a session that harvested no task", sum(1 for s in ss if not s.get("tasks"))),
                  ("a session turn stopped at the turn cap", sum(1 for s in ss if s.get("hit_turn_cap"))))
        for what, n in checks:
            if n:
                body.append([r["run"], what, n])
    if not body:
        body = [["(none)", "no check flagged anything in any run", 0]]
    return table(out("T12-findings"), "T12 · What the lab's checks flagged, by run",
                 ["run", "finding", "count"], body,
                 note="Counted from sessions.jsonl. The autopilot never repairs anything by "
                      "hand: when a step does not do what the protocol says, it records the "
                      "finding and goes on, or stops. A harvest that produced no task can be "
                      "right: a check that needs the fix's own test is deleted by design.")


# -------------------------------------------------------------------- T13 --
def t13_invalid(d):
    inval = [r for r in d.rollouts if not r.get("valid")]
    if not inval:
        return table(out("T13-invalid"), "T13 · Invalid rollouts",
                     ["run", "source", "arm", "reason", "count"],
                     [["(none)", "—", "—", "no rollout was invalidated", 0]])
    c = Counter((r["run"], r["source"], r.get("arm"), r.get("verdict") or "?") for r in inval)
    body = [[run, src, arm, why, n] for (run, src, arm, why), n in c.most_common()]
    return table(out("T13-invalid"), "T13 · Invalid rollouts, excluded and counted",
                 ["run", "source", "arm", "reason", "count"], body,
                 note="An invalid rollout is infrastructure, not capability: it is excluded from "
                      "every rate and listed here so the exclusion is checkable.")


# -------------------------------------------------------------------- T14 --
def t14_cost(d):
    body = []
    for r in d.runs:
        sw = [s for s in d.sweeps if s["run"] == r["run"]]
        be = [x for x in d.rollouts if x["run"] == r["run"] and x["source"] == "bench"]
        body.append([r["run"], r["kind"],
                     f"${r.get('agent_cost_usd', 0):.2f}",
                     f"{sum(s['rollouts'] for s in sw)}",
                     f"${sum(s.get('cost_usd') or 0 for s in sw):.2f}",
                     f"{len(be)}",
                     f"${sum(x.get('cost_usd') or 0 for x in be):.2f}",
                     f"${r.get('cost_usd', 0):.2f}"])
    if not body:
        return missing("T14-cost", "T14 · Cost", "no runs exported yet")
    total = sum(r.get("cost_usd", 0) for r in d.runs)
    body.append(["runs above (the development run's included)", "", "", "", "", "", "",
                 f"${total:,.2f}"])
    sp = d.spend or {}
    if sp.get("per_run"):
        # everything else the programme spent, measured the same way (usage-guard)
        exported = {r["run"] for r in d.runs}
        cost_of = {r["run"]: r.get("cost_usd", 0) for r in d.runs}
        for run, v in sp["per_run"].items():
            extra = sum(v.values()) - cost_of.get(run, 0)
            if run in exported and extra > 0.5:        # e.g. M1: its /prune sweeps
                body.append([f"{run} (beyond its export)", "measured", "", "",
                             f"${v.get('sweeps', 0):.2f}", "", "", f"${extra:.2f}"])
            if run not in exported:
                body.append([run, "testbed / other", f"${v.get('sessions', 0):.2f}", "",
                             f"${v.get('sweeps', 0) + v.get('sweeps_deleted', 0):.2f}"
                             + (f" (of which ${v['sweeps_deleted']:.2f} a sweep whose record the "
                                f"agent deleted)" if v.get("sweeps_deleted") else ""),
                             "", f"${v.get('bench', 0):.2f}", f"${sum(v.values()):.2f}"])
        body.append(["**programme, measured**", "", "", "", "", "", "",
                     f"**${sp['total']:,.2f}** of ${sp.get('cap', 1500):,.0f} (the development "
                     f"run not included)"])
    return table(out("T14-cost"), "T14 · Cost by phase and run",
                 ["run", "kind", "sessions and /evolve", "sweep rollouts", "sweep $",
                  "benchmark rollouts", "benchmark $", "total"], body,
                 note="Every figure is the sum of `total_cost_usd` the CLI reported for each "
                      "call, never an estimate. One sweep of the prune test is on no disk: the "
                      "/prune agent deleted its record and ran it again; its cost is the sum "
                      "Claude Code recorded for its rollouts (data/transcripts-coverage.json).")


# -------------------------------------------------------------------- T15 --
def t15_model_change(d):
    runs = [r["run"] for r in d.of_kind("model-change")]
    if not runs:
        return missing("T15-model-change", "T15 · A stronger model",
                       "the model-change study has not run")
    rows = d.bench(runs=runs)
    body = []
    for f in list("ABCDE") + [None]:
        fams = [f] if f else list(RULE_FAMILIES)
        cs = S.cells(rows, "none", "evolved", families=fams, split="holdout")
        if not cs:
            continue
        _, _, p0 = S.rate(rows, split="holdout", arm="none", **({"family": f} if f else {}))
        _, _, p1 = S.rate(rows, split="holdout", arm="evolved", **({"family": f} if f else {}))
        lo, hi, _ = S.two_way_bootstrap(cs)
        body.append([f or "A+B+C+E", pct(p0), pct(p1), signed(S.paired_mean(cs)), ci(lo, hi)])
    return table(out("T15-model-change"), "T15 · The same harness under a stronger model",
                 ["family", "none", "evolved", "paired diff", "95% CI"], body,
                 note="Analysed separately from Haiku and never pooled with it. "
                      + ("/prune under " + str(d.prune_mc[0].get("model")) + " ("
                         + str(d.prune_mc[0].get("mode")) + "), every item of "
                         + str(d.prune_mc[0].get("from_run")) + ": "
                         + "; ".join(f"`{p['item']}` {p['verdict']}" for p in d.prune_mc)
                         + ". ACCEPT means removing it cost nothing under this model."
                         if d.prune_mc else "The /prune pass under the stronger model has not run."))


# -------------------------------------------------------------------- T16 --
def t16_defects(d):
    p = DATA / "defects.json"
    if not p.exists():
        return missing("T16-defects", "T16 · Defect catalogue", "defects.json has not been written")
    rows = json.loads(p.read_text())
    body = [[i + 1, r.get("class"), r.get("symptom"), r.get("detected"), r.get("why_serious"),
             r.get("fix"), r.get("test"), ", ".join(r.get("runs_affected") or []) or "—"]
            for i, r in enumerate(rows)]
    return table(out("T16-defects"), "T16 · Every defect the lab found in Cortex",
                 ["#", "class", "symptom", "how it was detected", "why it would corrupt a "
                  "measurement", "the fix", "the regression test", "runs affected"], body,
                 note="Written for a reader who has never seen Cortex. A measurement instrument "
                      "that has never been wrong has never been checked; this is the list of "
                      "times it was, and what stops each one coming back.")


# -------------------------------------------------------------------- T17 --
def t17_external(d):
    if not d.external:
        return missing("T17-external", "T17 · A repository we did not build",
                       "the second repository has not been run")
    body = [[e.get("repo"), e.get("task"), e.get("split"), e.get("arm"),
             e.get("passed"), e.get("n"), pct(e.get("rate", float("nan")))]
            for e in d.external]
    xr = d.bench(runs=sorted({e["run"] for e in d.external}), arms=("none", "evolved"),
                 split="holdout")
    cs = S.cells(xr, "none", "evolved", split="holdout")
    paired = ""
    if cs:
        lo, hi, _ = S.two_way_bootstrap(cs)
        paired = (f" Paired over its {len(cs)} holdout tasks: `evolved` − `none` = "
                  f"{signed(S.paired_mean(cs))} points, 95 % bootstrap interval {ci(lo, hi)} — "
                  "wide, as four tasks must be: corroboration, not a second primary.")
    return table(out("T17-external"), "T17 · The second repository",
                 ["repository", "task", "split", "arm", "passed", "n", "rate"], body,
                 note="Reported on its own and never pooled with the lab." + paired)


# -------------------------------------------------------------------- T18 --
def t18_claims(d, claims):
    body = [[i + 1, c["claim"], c["evidence"], c.get("number", "—")]
            for i, c in enumerate(claims)]
    return table(out("T18-claims"), "T18 · Every claim, and what supports it",
                 ["#", "the sentence the report asserts", "figure or table", "the number"], body,
                 note="A sentence with no evidence is deleted, not softened. This table is the "
                      "check that it was.")


# -------------------------------------------------------------------- T19 --
def t19_scope(d):
    if not d.scope:
        return missing("T19-scope", "T19 · Scope replay", "scope-replay has not been run")
    fate = lambda s: (d.rule_fate(s["run"], s["candidate"])
                      or (f"{d.journal_fate(s['run'], s['candidate'])} (journal)"
                          if d.journal_fate(s["run"], s["candidate"]) else "unresolved"))
    body = [[s.get("run"), s.get("candidate"), s.get("kind"), s.get("injected"), s.get("suite"),
             s.get("relevance"), s.get("breadth"), fate(s), s.get("rollouts"),
             f"${s.get('cost_usd') or 0:.2f}"] for s in d.scope]
    for label, runs in (("evaluation runs", d.evaluation), ("development run", d.development)):
        flagged = [s for s in d.scope if s.get("run") in runs
                   and isinstance(s.get("relevance"), (int, float)) and s["relevance"] < 0.35]
        kept = [s for s in flagged if fate(s).startswith("kept")]
        saved = sum(s.get("cost_usd") or 0 for s in flagged if s not in kept)
        body.append([f"**counterfactual, {label}**", "later buried, that the floor would have "
                     "flagged", len(flagged) - len(kept), "", "", "", "", "", "",
                     f"**${saved:.2f}** saved"])
        body.append([f"**false alarms, {label}**", "KEPT candidates it would also have flagged",
                     len(kept), "", "", "", "", "", "", ""])
    return table(out("T19-scope"), "T19 · Predicting the verdict before paying for it",
                 ["run", "candidate", "kind", "injected", "suite", "relevance", "breadth",
                  "fate", "rollouts", "cost"], body,
                 note="Predictions are computed from each candidate's own text and its run's task "
                      "suite, never from the verdict — which is what makes them predictions. "
                      "`fate` is score.sh's verdict for the evaluation runs' candidates "
                      "(kept, killed-regression, killed on another gate, or unscored: buried by "
                      "the /evolve agent after a RERUN), and the journal's for the development "
                      "run. The saving is never reported without the false-alarm count beside it.")


# -------------------------------------------------------------------- T20 --
def t20_judge(d):
    body = []
    for r in d.runs:
        j = r.get("jev") or {}
        body.append([r["run"], r["kind"], "ON" if j.get("enabled") else "off",
                     j.get("model") or "—", j.get("base_url") or "—",
                     j.get("requests", "—"), j.get("answered", "—"),
                     "yes" if r["run"] in (d.evaluation + d.control) else "no"])
    if not body:
        return missing("T20-judge", "T20 · Judge provenance", "no runs exported yet")
    return table(out("T20-judge"), "T20 · Judge provenance: which runs saw one",
                 ["run", "kind", "jev", "exact model id", "endpoint", "requests", "answered",
                  "may feed a primary"], body,
                 note="Every run appears, including the ones that were off: \"off\" is the claim "
                      "that has to be checkable. A run with a judge may never feed H1, H2 or H13.")
