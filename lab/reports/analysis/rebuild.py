#!/usr/bin/env python3
"""rebuild.py — one command rebuilds every table and figure from `reports/data/`.

    lab/reports/analysis/run.sh              # the whole thing, offline
    python3 rebuild.py --only T4,F2          # one table or figure while iterating

It needs no API access and no network. That is the point: the part of this work a
reviewer is most likely to try is regenerating the numbers from the shipped rows,
so it has to work on a machine that has never seen Cortex.

Every hypothesis verdict is computed here, against the margins fixed in
`PREREGISTRATION.md` §11.1. Nothing in this file may read a result and then decide
what would count as support — the thresholds are constants, and they are the same
constants the pre-registration prints.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import figures as F                       # noqa: E402
import stats as S                         # noqa: E402
import tables as T                        # noqa: E402
from load import DATA, RULE_FAMILIES, Data, z  # noqa: E402

REPORTS = HERE.parent

# ---- the pre-registered margins, as constants ------------------------------
M_D_FAMILY = -0.10          # H2: family D's lower bound must be above this
M_NOT_BETTER = +0.05        # H6, H7: the other arm's upper bound must be below this
M_FORM = +0.05              # H11: ideal − swapped lower bound must be above this
M_CLOSE = 0.10              # H8: evolved within this of the best ceiling arm
M_DESC_SHARE = 0.50         # H12: desc-only must recover at least this share


def verdict(supported, testable=True):
    if not testable:
        return "NOT TESTABLE"
    return "SUPPORTED" if supported else "NOT SUPPORTED"


def arm_pair(d, runs, arm_a, arm_b, families=RULE_FAMILIES, split="holdout",
             complete_case=False):
    """The paired comparison, over either every valid cell or the complete-case set.

    `PREREGISTRATION.md` §5.1 asks for both: the **complete-case** set — the tasks
    measured in every run, which is the primary — and the **all-valid** set as a
    secondary. They can differ whenever a run excludes a scenario the others kept,
    and reporting only the one that came out better is exactly the freedom the
    pre-registration exists to remove.
    """
    rows = d.bench(runs=runs, arms=(arm_a, arm_b), split=split)
    if complete_case:
        keep = set(d.complete_case_tasks(runs, arms=(arm_a, arm_b), split=split))
        rows = [r for r in rows if r["task"] in keep]
    cs = S.cells(rows, arm_a, arm_b, families=list(families), split=split)
    if not cs:
        return None
    m = S.paired_mean(cs)
    lo, hi, _ = S.two_way_bootstrap(cs)
    _, p, ntask = S.permutation_p(rows, arm_a, arm_b, families=list(families), split=split)
    return {"mean": m, "lo": lo, "hi": hi, "p": p, "tasks": ntask, "cells": cs, "rows": rows}


def scorecard(d):
    """H0…H18, each with its estimate, interval, margin and verdict."""
    ev = d.evaluation or d.development           # D0 alone until a replicate exists
    using_d0_only = not d.evaluation
    out = []

    def add(hid, text, **kw):
        out.append({"id": hid, "hypothesis": text, **kw})

    # ---- H0 ---------------------------------------------------------------
    rows = d.bench(runs=ev, arms=("none",), split="holdout")
    if rows:
        rates = {f: S.rate(rows, family=f)[2] for f in "ABCDE"}
        broke = [f for f in RULE_FAMILIES if rates.get(f, 1) < 0.5]
        add("H0", "Without a harness the agent breaks A/B/C/E often and passes D",
            test="`none` arm, holdout",
            estimate=" ".join(f"{f}{rates[f]:.0%}" for f in "ABCDE"),
            interval="—",
            margin="D at or above 90%, and at least three of A/B/C/E below 50%",
            verdict=verdict(len(broke) >= 3 and rates.get("D", 0) >= 0.9),
            evidence="F1, T4 · the stricter reading, all four below 50%, is "
                     + ("met" if len(broke) == 4 else "not met")
                     + " · the margin is the rule the analysis code applies (DEVIATIONS D-22)")
    else:
        add("H0", "Without a harness the agent breaks A/B/C/E often and passes D",
            verdict="INCONCLUSIVE", evidence="no rollouts")

    # ---- H1 primary -------------------------------------------------------
    # The complete-case set is the primary; the all-valid set is reported beside it.
    r = arm_pair(d, ev, "none", "evolved", complete_case=True)
    r_all = arm_pair(d, ev, "none", "evolved")
    if r and r_all:
        agree = (r["lo"] > 0) == (r_all["lo"] > 0)
        r["also"] = (f" · all-valid set: {r_all['mean'] * 100:+.1f} "
                     f"[{r_all['lo'] * 100:+.1f}, {r_all['hi'] * 100:+.1f}]"
                     f"{'' if agree else ' — **the two sets disagree in direction; '
                                        'the complete-case answer stands and the '
                                        'disagreement is the finding**'}")
    if r:
        add("H1", "PRIMARY. On holdout tasks `evolved` beats `none`, A+B+C+E pooled",
            test="paired by task, two-way bootstrap over runs and tasks",
            estimate=f"{r['mean'] * 100:+.1f} points",
            interval=f"[{r['lo'] * 100:+.1f}, {r['hi'] * 100:+.1f}]",
            margin="lower bound above 0",
            verdict=verdict(r["lo"] > 0),
            evidence=f"T4, F2, F3 · permutation p = {r['p']:.4g}"
                     + f" · {r['tasks']} complete-case scenario-run pairs "
                       f"({len({t for _run, t in r['cells']})} scenarios)" + r.get("also", "")
                     + (" · **D0 only: no run-level interval exists**" if using_d0_only else ""))
    # ---- H2 primary -------------------------------------------------------
    r = arm_pair(d, ev, "none", "evolved", families=("D",), complete_case=True)
    spurious = [i["name"] for run in ev for i in d.kept(run)
                if T._own_family(i["name"], d, run) is None]
    if r:
        add("H2", "PRIMARY. Family D is not harmed, and no spurious item is kept",
            test="family D, paired, two-way bootstrap; plus the kept-item list",
            estimate=f"{r['mean'] * 100:+.1f} points; {len(spurious)} spurious item(s)",
            interval=f"[{r['lo'] * 100:+.1f}, {r['hi'] * 100:+.1f}]",
            margin=f"lower bound above {M_D_FAMILY * 100:+.0f} and no spurious item",
            verdict=verdict(r["lo"] > M_D_FAMILY and not spurious),
            evidence="T4, T6, F2")

    # ---- H3 tier rubric ---------------------------------------------------
    scored = [x for x in tier_rubric(d, ev) if x.get("measurable")]
    if scored:
        good = sum(1 for s in scored if s["score"] == 3)
        add("H3", "Each kept item lands in a defensible tier and fires in its own area",
            test="the three-part rubric of PREREGISTRATION.md §11.2",
            estimate=f"{good} of {len(scored)} items scored 3/3",
            interval="—", margin="every kept item scores 3/3",
            verdict=verdict(good == len(scored)), evidence="T6, F9")
    else:
        # An item with no firing data has not failed the rubric; it has not been
        # measured. Scoring it 0 would turn a missing benchmark into a result.
        add("H3", "Each kept item lands in a defensible tier and fires in its own area",
            verdict="INCONCLUSIVE",
            evidence="no kept item has firing data yet — the benchmark has not run "
                     "for these runs")

    # ---- H4 corrections ---------------------------------------------------
    if d.control and d.evaluation:
        e = [s["corrections"] for s in d.sessions if s["run"] in d.evaluation]
        c = [s["corrections"] for s in d.sessions if s["run"] in d.control]
        diff = (sum(e) / len(e) - sum(c) / len(c)) if e and c else float("nan")
        add("H4", "Corrections fall once an item is live, beyond the control runs",
            test="corrections per session, evaluation against control, permutation over runs",
            estimate=f"{diff:+.2f} corrections per session", interval="see T9",
            margin="evaluation below control", verdict=verdict(diff < 0), evidence="T9, F5")
    else:
        add("H4", "Corrections fall once an item is live, beyond the control runs",
            verdict="INCONCLUSIVE", evidence="needs both an evaluation and a control run")

    # ---- H5 gates ---------------------------------------------------------
    if d.gates:
        plac = [g for g in d.gates if g["type"].startswith("placebo")]
        harm = [g for g in d.gates if g["type"] == "harmful"]
        pos = [g for g in d.gates if g["type"] == "positive"]
        fk = sum(1 for g in plac if g["verdict"] == "KEEP")
        lo, hi = S.clopper_pearson(fk, len(plac)) if plac else (0, 1)
        # the scorer's own verdict: the gate procedure stops at a screen whose gain is not
        # positive or whose candidate never fired and records that stop as a KILL, but
        # score.sh returns RERUN ("no task here could show a gain") for some of those
        sv = {g["name"]: scorer_verdict(g) for g in d.gates}
        hk = sum(1 for g in harm if sv[g["name"]] == "KILL")
        hr = sum(1 for g in harm if sv[g["name"]] == "RERUN")
        hkept = sum(1 for g in harm if sv[g["name"]] == "KEEP")
        kept = sum(1 for g in pos if g["verdict"] == "KEEP")
        add("H5", "Gates are calibrated: placebos rarely kept, harmful killed, positives kept",
            test="29 candidates with a known right answer through the real pipeline",
            estimate=f"false KEEP {fk}/{len(plac)}; harmful kept {hkept}/{len(harm)} "
                     f"(score.sh: {hk} KILL, {hr} RERUN); positives kept {kept}/{len(pos)}",
            interval=f"false KEEP [{lo:.0%}, {hi:.0%}]",
            margin="false-KEEP upper bound below 25%, every harmful killed, "
                   "at least 3 of 4 positives kept",
            verdict=verdict(hi < 0.25 and hk == len(harm) and kept >= 3),
            evidence="T8, F10 · a harmful candidate counts as killed when score.sh killed it "
                     "(DEVIATIONS D-22)")
    else:
        add("H5", "Gates are calibrated", verdict="INCONCLUSIVE",
            evidence="the gate testbed has not run")

    # ---- H6, H7, H8 ablations --------------------------------------------
    for hid, arm, text, margin_fn in (
            ("H6", "accept-all", "Gates add value: `accept-all` is not better than `evolved`",
             lambda r: r["hi"] < M_NOT_BETTER),
            ("H7", "flat", "Tiers add value: `flat` costs more always-on context "
                           "without gaining pass rate",
             lambda r: r["hi"] < M_NOT_BETTER)):
        # An arm byte-identical to the one it is compared against measures nothing.
        # `accept-all` is `evolved` plus everything the run buried, so a run that
        # buried nothing makes them the same harness — and the difference comes out
        # as exactly zero, which reads like a finding and is not one.
        # Identical only where it is identical: an arm that is degenerate in one run
        # can be a real arm in another, so H6 falls back to the runs where it is real.
        real = [run for run in ev
                if arm not in (d.arms_of(run).get("evolved", {}).get("identical_to") or [])
                and d.arms_of(run).get(arm)]
        same = bool(ev) and not real
        if same:
            add(hid, text, test=f"`{arm}` against `evolved`",
                estimate="the two arms are byte-identical", interval="—",
                margin=f"upper bound below {M_NOT_BETTER * 100:+.0f}",
                verdict="INCONCLUSIVE",
                evidence=f"`{arm}` is the same harness as `evolved` in every "
                         f"evaluation run: nothing was buried, so the gates had "
                         f"nothing to leave out. H5's placebo testbed measures the "
                         f"same question directly.")
            continue
        r = arm_pair(d, real or ev, "evolved", arm)
        if r:
            extra = ""
            if hid == "H7":
                ch = {a: d.arm_meta(real or ev, a, "always_on_chars")
                      for a in ("evolved", "flat")}
                costs_more = (ch.get("flat") or 0) > (ch.get("evolved") or 0)
                extra = (f"; always-on {ch.get('evolved')} → {ch.get('flat')} chars"
                         if ch.get("flat") else "; always-on cost not recorded")
                ok = margin_fn(r) and costs_more
            else:
                ok = margin_fn(r)
            add(hid, text, test=f"`{arm}` − `evolved`, paired, two-way bootstrap",
                estimate=f"{r['mean'] * 100:+.1f} points{extra}",
                interval=f"[{r['lo'] * 100:+.1f}, {r['hi'] * 100:+.1f}]",
                margin=f"upper bound below {M_NOT_BETTER * 100:+.0f}"
                       + (" and it costs more always-on characters" if hid == "H7" else ""),
                verdict=verdict(ok), evidence="T7, F8")
        else:
            add(hid, text, verdict="INCONCLUSIVE", evidence=f"the `{arm}` arm has not run")

    r_k = arm_pair(d, ev, "evolved", "kitchen")
    r_i = arm_pair(d, ev, "evolved", "ideal")
    if r_k or r_i:
        # `arm_pair(evolved, X)` is X MINUS evolved, so a negative mean means
        # evolved is ahead. The margin asks whether evolved falls short of the
        # better ceiling arm by more than M_CLOSE — that is, whether the ceiling's
        # advantage (the UPPER bound of X − evolved) exceeds it. The first version
        # tested the lower bound, which asked whether evolved beat the ceiling by
        # a lot, and so reported NOT SUPPORTED precisely when evolved won.
        best = max([x for x in (r_k, r_i) if x], key=lambda x: x["mean"])
        which = "kitchen" if best is r_k else "ideal"
        e_chars = d.arm_meta(ev, "evolved", "always_on_chars") or 0
        ceil_chars = {a: d.arm_meta(ev, a, "always_on_chars") for a in ("kitchen", "ideal")}
        cheaper = all(e_chars <= (v or 1e9) for v in ceil_chars.values() if v)
        ahead = best["mean"] < 0
        add("H8", "Efficiency: `evolved` approaches `kitchen` and `ideal` at far lower cost",
            test=f"`evolved` against the better ceiling arm (`{which}`), paired",
            estimate=(f"evolved is {abs(best['mean']) * 100:.1f} points "
                      f"{'AHEAD OF' if ahead else 'behind'} `{which}`"
                      f" · always-on {e_chars} vs "
                      + ", ".join(f"{a} {v}" for a, v in ceil_chars.items() if v)),
            interval=f"[{z(best['lo']) * 100 + 0.0:+.1f}, {z(best['hi']) * 100 + 0.0:+.1f}] "
                     f"({which} − evolved)",
            margin=f"evolved within {M_CLOSE * 100:.0f} points of the better ceiling "
                   f"arm, and cheaper in always-on characters",
            verdict=verdict(best["hi"] < M_CLOSE and cheaper), evidence="T7, F8")
    else:
        add("H8", "Efficiency: `evolved` approaches `kitchen` and `ideal` at far lower cost",
            verdict="INCONCLUSIVE", evidence="the ceiling arms have not run")

    # ---- H9, H13 reproducibility -----------------------------------------
    if len(d.evaluation) >= 2:
        learned = {run: {T._own_family(i["name"], d, run) for i in d.kept(run)}
                   for run in d.evaluation}
        common = set.intersection(*learned.values()) if learned else set()
        union = set().union(*learned.values()) if learned else set()
        add("H9", "Independent runs learn the same families, in similar forms",
            test="which families each run kept an item for",
            estimate=f"{len(common)} of {len(union)} families learned in every run",
            interval="—", margin="at least half the families learned anywhere are learned "
                                 "in every run",
            verdict=verdict(union and len(common) >= len(union) / 2), evidence="F7, T6")
    else:
        add("H9", "Independent runs learn the same families, in similar forms",
            verdict="INCONCLUSIVE", evidence="needs at least two evaluation runs")

    if d.evaluation and d.development:
        r_new = arm_pair(d, d.evaluation, "none", "evolved")
        # like for like: D0 re-measured on the same 30-task holdout with the same
        # tooling as R1…Rn (D0R), when it exists; D0's own 15-task figure is quoted
        d0_runs = d.remeasure_of(d.development)
        r_d0 = arm_pair(d, d0_runs, "none", "evolved")
        r_own = arm_pair(d, d.development, "none", "evolved") if d0_runs != d.development else None
        if r_new and r_d0:
            inside = r_new["lo"] <= r_d0["mean"] <= r_new["hi"]
            own = (f" (on its own 15-task holdout: {r_own['mean'] * 100:+.1f})" if r_own else "")
            add("H13", "D0 replicates: the development run's finding holds on the frozen version",
                test="D0's pooled gain, re-measured on the replicates' holdout with their "
                     "tooling, against the evaluation runs' interval",
                estimate=f"D0 {r_d0['mean'] * 100:+.1f}{own}, replicates {r_new['mean'] * 100:+.1f}",
                interval=f"[{r_new['lo'] * 100:+.1f}, {r_new['hi'] * 100:+.1f}]",
                margin="D0's estimate inside the replicates' interval",
                verdict=verdict(inside), evidence="T4, F3")
    else:
        add("H13", "D0 replicates", verdict="INCONCLUSIVE",
            evidence="needs both D0 and at least one evaluation run")

    # ---- H10 prune --------------------------------------------------------
    if d.prune:
        matched = sum(1 for p in d.prune if p.get("verdict") == p.get("expected"))
        never_fired_deleted = [p for p in d.prune
                               if p.get("fires") == "no" and p.get("verdict") == "ACCEPT"]
        add("H10", "/prune deletes planted useless items that fired, keeps needed ones, and "
                   "never deletes one that never fired",
            test="planted items with a known right answer through `autopilot prune`",
            estimate=f"{matched} of {len(d.prune)} matched",
            interval="—", margin="every planted item matches, and nothing that never fired "
                                 "is deleted",
            verdict=verdict(matched == len(d.prune) and not never_fired_deleted),
            evidence="T10")
    else:
        add("H10", "/prune deletes planted useless items that fired, keeps needed ones",
            verdict="INCONCLUSIVE", evidence="the prune testbed has not run")

    # ---- H11 form ---------------------------------------------------------
    r = arm_pair(d, ev, "swapped", "ideal")
    if r:
        add("H11", "The form matters: the right skill/rule choice beats the swapped one",
            test="`ideal` − `swapped`, paired", estimate=f"{r['mean'] * 100:+.1f} points",
            interval=f"[{r['lo'] * 100:+.1f}, {r['hi'] * 100:+.1f}]",
            margin=f"lower bound above {M_FORM * 100:+.0f}",
            verdict=verdict(r["lo"] > M_FORM), evidence="T7, F8")
    else:
        add("H11", "The form matters", verdict="INCONCLUSIVE",
            evidence="the `swapped` arm has not run")

    # ---- H12 description --------------------------------------------------
    r_desc = arm_pair(d, ev, "none", "desc-only")
    r_full = arm_pair(d, ev, "none", "evolved")
    if r_desc and r_full:
        share, lo, hi = S.share_recovered(r_desc["cells"], r_full["cells"])
        # `desc-only` rewrites SKILL bodies and nothing else. On a harness that is
        # mostly rules it perturbs very little, and the share it "recovers" is then
        # mostly the untouched items doing their usual work rather than evidence
        # about descriptions. The report has to say how much was actually changed.
        # (run, files the arm rewrote, items in the harness) — kept as numbers.
        # An earlier version formatted these into a sentence and then parsed the
        # sentence back to decide the verdict, which broke the moment the wording
        # changed. A verdict must never depend on its own prose.
        per = []
        for run in ev:
            arms = d.arms_of(run)
            ev_arm = arms.get("evolved") or {}
            n_items = len(ev_arm.get("skills", [])) + len(ev_arm.get("rules", []))
            if not arms.get("desc-only") or not n_items:
                continue
            dd = (arms.get("desc-only") or {}).get("differs_from_evolved")
            # not recorded: the arm rewrites SKILL bodies, so the skill count is the
            # right fallback. Reporting 0 once made a real perturbation of one file
            # of four read as none at all.
            changed = dd.get("changed", 0) if dd is not None else len(ev_arm.get("skills", []))
            per.append((run, changed, n_items))
        caveat = (" · items actually rewritten — "
                  + "; ".join(f"{r}: {c} of {n}" for r, c, n in per)) if per else ""
        thin = all(c * 2 <= n for _, c, n in per) if per else False
        add("H12", "The description hypothesis: a skill's description alone carries much of "
                   "its effect",
            test="`desc-only` − `none` as a share of `evolved` − `none`",
            estimate=f"{share:.0%} of the gain recovered{caveat}",
            interval=f"[{lo:.0%}, {hi:.0%}]",
            margin=f"at least {M_DESC_SHARE:.0%}, with the lower bound above 0"
                   + (" — READ THE CAVEAT: this arm rewrote under half the harness, "
                      "so most of what it recovers is items it did not touch" if thin else ""),
            verdict=("INCONCLUSIVE" if thin else
                     verdict(share >= M_DESC_SHARE and lo > 0)),
            evidence="F15, T7" + (" · the arm is too weak on this harness to decide"
                                  if thin else ""))
    else:
        add("H12", "The description hypothesis", verdict="INCONCLUSIVE",
            evidence="the `desc-only` arm has not run")

    # ---- H14 model change -------------------------------------------------
    mc = [r["run"] for r in d.of_kind("model-change")]
    if mc and d.prune_mc:
        # Brief §4.8: "Verdict from step 3 [does an item the weaker model needed become
        # removable for the stronger one?], supported by step 2's gain difference."
        # Every item /prune tests here was KEPT under Haiku by the gates, so an ACCEPT
        # (its removal costs nothing) is exactly "no longer earns its place".
        src = d.same_harness(mc)
        r_h = arm_pair(d, src, "none", "evolved")
        r_s = arm_pair(d, mc, "none", "evolved")
        decided = [p for p in d.prune_mc if p.get("verdict") in ("ACCEPT", "REJECT")]
        removable = [p["item"] for p in decided if p["verdict"] == "ACCEPT"]
        model = d.prune_mc[0].get("model") or "the stronger model"
        gains = (f"; the same harness gains {r_h['mean'] * 100:+.1f} under Haiku ({', '.join(src)}) "
                 f"and {r_s['mean'] * 100:+.1f} under {model}" if r_h and r_s else "")
        add("H14", "After a model upgrade, re-measurement changes which items earn their place",
            test=f"/prune under {model} on a copy of {', '.join(src)}, every item tested; "
                 "the same harness's holdout gain under each model beside it",
            estimate=f"{len(removable)} of {len(decided)} decided item(s) removable"
                     + (f" ({', '.join(removable)})" if removable else "") + gains,
            interval=(f"[{r_s['lo'] * 100:+.1f}, {r_s['hi'] * 100:+.1f}]" if r_s else "—"),
            margin="at least one item the weaker model needed becomes removable",
            verdict=("INCONCLUSIVE" if not decided else verdict(bool(removable))),
            evidence="T15, F16")
    elif mc:
        add("H14", "After a model upgrade, re-measurement changes which items earn their place",
            verdict="INCONCLUSIVE",
            evidence="the benchmark ran but the /prune pass under the stronger model has not")
    else:
        add("H14", "After a model upgrade, re-measurement changes which items earn their place",
            verdict="INCONCLUSIVE", evidence="the model-change study has not run")

    # ---- H15 external -----------------------------------------------------
    if d.external:
        by = {}
        for e in d.external:
            b = by.setdefault(e["arm"], [0, 0])
            b[0] += e.get("passed", 0)
            b[1] += e.get("n", 0)
        gain = ((by.get("evolved", [0, 1])[0] / max(1, by.get("evolved", [0, 1])[1]))
                - (by.get("none", [0, 1])[0] / max(1, by.get("none", [0, 1])[1])))
        # brief §5: "its own paired analysis over its 4 holdout tasks at k=5, with a
        # bootstrap CI" — the same paired unit and bootstrap as the lab's primary, on
        # X1's own rollouts; with four tasks the interval is wide, and says so
        xr = d.bench(runs=sorted({e["run"] for e in d.external}), arms=("none", "evolved"),
                     split="holdout")
        cs = S.cells(xr, "none", "evolved", split="holdout")
        if cs:
            gain = z(S.paired_mean(cs))
            lo, hi, _ = S.two_way_bootstrap(cs)
            iv = f"[{z(lo) * 100:+.1f}, {z(hi) * 100:+.1f}] (task bootstrap, {len(cs)} tasks)"
        else:
            iv = "— (no rollout rows to pair)"
        # D-12: when the loop kept nothing, `evolved` IS `none` and the benchmark is an
        # A/A. Its difference is noise by construction and cannot support H15, however
        # it falls; it is reported as the A/A it is.
        if any(e.get("harness_identical") for e in d.external):
            add("H15", "The loop also helps on a repository nobody in this project built",
                test="its own 4 holdout tasks at k=5 — but the loop kept nothing, so "
                     "`evolved` is byte-identical to `none` and the benchmark is an A/A",
                estimate=f"A/A difference {gain * 100:+.1f} points (noise by construction)",
                interval=iv, margin="a positive gain from an evolved harness",
                verdict="INCONCLUSIVE",
                evidence="T17 · /evolve was BARREN: nothing recurred often enough to learn")
            gain = None
        if gain is not None:
          add("H15", "The loop also helps on a repository nobody in this project built",
            test="its own 4 holdout tasks at k=5, judged by its own suite and linter; "
                 "paired over tasks",
            estimate=f"{gain * 100:+.1f} points", interval=iv,
            margin="a positive gain, reported as corroboration and never pooled",
            verdict=verdict(gain > 0), evidence="T17, F17")
    else:
        add("H15", "The loop also helps on a repository nobody in this project built",
            verdict="INCONCLUSIVE", evidence="the second repository has not been run")

    # ---- H16, H17, H18 the judge -----------------------------------------
    if d.scope:
        # the evaluation runs only (the development run is reported beside, never pooled),
        # and the fates score.sh gives: KEPT against KILLED on a regression gate
        sc = [s for s in d.scope if s.get("run") in d.evaluation]
        fate = {id(s): d.rule_fate(s["run"], s["candidate"]) for s in sc}
        num = lambda f, key: [s[key] for s in sc if fate[id(s)] == f
                              and isinstance(s.get(key), (int, float))]
        kept, bur = num("kept", "relevance"), num("killed-regression", "relevance")
        bk, bb = num("kept", "breadth"), num("killed-regression", "breadth")
        sep = bool(kept and bur and min(kept) > max(bur))
        bsep = bool(bk and bb and min(bk) > max(bb))
        add("H16", "Pre-sweep relevance separates KEPT from BURIED-on-regression where "
                   "breadth does not",
            test="lowest KEPT against highest BURIED-on-regression, with breadth as the control; "
                 "on the evaluation runs, a candidate is buried on a regression when score.sh "
                 "killed it on gate 2 or 3 (DEVIATIONS D-22)",
            estimate=(f"relevance: lowest KEPT {min(kept):.0%} vs highest BURIED "
                      f"{max(bur):.0%}" if kept and bur else "relevance unavailable (no judge)")
                     + (f" · breadth: {min(bk):.0%} vs {max(bb):.0%}" if bk and bb else "")
                     + f" · {len(kept)} kept, {len(bur)} buried on a regression",
            interval="see T19",
            margin="relevance separates and breadth does not",
            verdict=verdict(sep and not bsep, testable=bool(kept and bur)),
            evidence="T19, F18 · the development run is in T19, not pooled")
    else:
        add("H16", "Pre-sweep relevance separates KEPT from BURIED-on-regression",
            verdict="INCONCLUSIVE", evidence="scope-replay has not been run")

    pairs = fire_rate_pairs(d)
    if pairs:
        # Two or three live items is far too few for a correlation to mean anything,
        # so the pre-registered test is the RANK ORDER and no r is ever quoted.
        ranks_ok = all(
            (a["predicted"] - b["predicted"]) * (a["measured"] - b["measured"]) >= 0
            for i, a in enumerate(pairs) for b in pairs[i + 1:])
        worst = max(pairs, key=lambda x: abs(x["predicted"] - x["measured"]))
        add("H17", "The judge's predicted fire rate tracks the measured one",
            test="predicted against measured invocation rate, per live gated skill",
            estimate="; ".join(f"{x['item']} predicted {x['predicted']:.0%} vs measured "
                               f"{x['measured']:.0%}" for x in pairs),
            interval=f"n = {len(pairs)} items",
            margin="rank order preserved (no correlation is quoted at this n)",
            verdict=verdict(ranks_ok),
            evidence=f"F19, T19 · largest miss: {worst['item']}, "
                     f"{abs(worst['predicted'] - worst['measured']) * 100:.0f} points")
    else:
        add("H17", "The judge's predicted fire rate tracks the measured one",
            test="predicted against measured, per live item", estimate="—", interval="—",
            margin="rank order preserved", verdict="INCONCLUSIVE",
            evidence="no item has both a prediction and a measured fire rate yet")
    add("H18", "Counting every lesson and transcript chooses a different theme than a sample",
        test="one Jev-on run against the Jev-off runs", estimate="—", interval="—",
        margin="descriptive only", verdict="NOT TESTABLE",
        evidence="DEVIATIONS.md D-01: dropped. It is one ordinary run's cost and was "
                 "the first block to cut; the judge was unavailable when the budget "
                 "was set and the runs were already committed when it returned.")
    return out


def scorer_verdict(g):
    """A gate-test candidate's verdict as score.sh gave it: the confirm's, when it
    reached one, else the screen's."""
    return ((g.get("confirm") or {}).get("verdict") or (g.get("screen") or {}).get("verdict")
            or g.get("verdict"))


def fire_rate_pairs(d):
    """H17: the judge's predicted invocation rate beside the measured one.

    The comparator is fired/VISIBLE, not fired/rollouts: the question the judge was
    asked is "would an agent doing this task choose to invoke the skill", which is
    conditional on the skill having been offered at all. A rule is never asked,
    because a rule is loaded rather than chosen.
    """
    out = []
    for s in d.scope:
        pred = s.get("predicted_fire_rate")
        if not isinstance(pred, (int, float)):
            continue
        f = d.firing(s.get("run")).get(s.get("candidate"))
        if not f or not f.get("visible"):
            continue
        out.append({"run": s["run"], "item": s["candidate"], "predicted": pred,
                    "measured": f["fired"] / f["visible"],
                    "fired": f["fired"], "visible": f["visible"]})
    return sorted(out, key=lambda x: x["predicted"])


def tier_rubric(d, runs):
    """PREREGISTRATION.md §11.2, applied to the recorded firing data."""
    out = []
    for run in runs:
        firing = d.firing(run)
        for it in d.kept(run):
            fam = T._own_family(it["name"], d, run)
            f = firing.get(it["name"], {})
            byf = f.get("by_family", {})
            own = byf.get(fam, {}) if fam else {}
            other = {k: v for k, v in byf.items() if k != fam}
            # Over ROLLOUTS, not over rollouts where it was already visible: a rule is
            # loaded rather than chosen, so fired-given-visible is 1 by construction.
            own_rate = (own.get("fired", 0) / own["rollouts"]) if own.get("rollouts") else 0.0
            oth_n = sum(v.get("rollouts", 0) for v in other.values())
            oth_rate = (sum(v["fired"] for v in other.values()) / oth_n) if oth_n else 0.0
            oth_vis = sum(v["visible"] for v in other.values())
            # 1. form matches the trigger: a skill must fire; a path-less rule must be cheap
            form_ok = (f.get("fired", 0) > 0) if it["kind"] == "skill" else True
            if it["kind"] == "rule" and not it.get("paths"):
                form_ok = False          # a path-less rule is always on: it must justify the cost
            # 2. scope matches the area: a path-scoped item must not reach another family
            scope_ok = bool(it.get("paths")) or it["kind"] == "skill"
            # 3. it fires where it is about, more than elsewhere
            area_ok = own_rate > oth_rate or (own_rate > 0 and oth_vis == 0)
            out.append({"run": run, "name": it["name"], "family": fam,
                        "measurable": bool(f.get("rollouts")),
                        "form": form_ok, "scope": scope_ok, "area": area_ok,
                        "own_rate": own_rate, "other_rate": oth_rate,
                        "score": int(form_ok) + int(scope_ok) + int(area_ok)})
    return out


def claims(d, cards):
    """T18: every sentence the report asserts, against what supports it.

    Two kinds. The hypotheses are the obvious ones. The second kind is the trap:
    a report's most quotable sentences are usually NOT hypotheses — "the agent
    opened CONTRIBUTING.md in 0.4% of rollouts", "39 defects" — and those are
    exactly the ones that get written from memory. Every one below is computed
    here from the same rows.
    """
    out = []
    for c in cards:
        if c.get("verdict") in ("SUPPORTED", "NOT SUPPORTED"):
            out.append({"claim": f"{c['id']}: {c['hypothesis']} — {c['verdict']}",
                        "evidence": c.get("evidence", "—"),
                        "number": f"{c.get('estimate', '—')} {c.get('interval', '')}".strip()})
    ev = d.evaluation or d.development
    hold = d.bench(runs=ev, split="holdout")

    def add(text, where, number):
        out.append({"claim": text, "evidence": where, "number": number})

    rc = [r.get("read_contributing") for r in hold
          if r.get("arm") == "none" and r.get("read_contributing") is not None]
    if rc:
        add("Without a harness, the agent solves these tasks without opening the file that "
            "documents the house rules.", "rollouts.jsonl · read_contributing, `none` arm",
            f"{sum(rc)}/{len(rc)} holdout rollouts = {sum(rc) / len(rc):.1%}")
    for run in ev:
        for name, f in sorted(d.firing(run).items()):
            if f.get("visible"):
                add(f"`{name}` ({run}) was in context in {f['visible']} rollouts and "
                    f"invoked in {f['fired']}.", "F9, T6",
                    f"{f['fired']}/{f['visible']} = {f['fired'] / f['visible']:.0%}")
    dp = DATA / "defects.json"
    if dp.exists():
        rows = json.loads(dp.read_text())
        d0 = sum(1 for r in rows if r.get("where") != "the evaluation programme")
        add("The lab found defects in Cortex itself, and they are a result rather than "
            "an embarrassment.", "T16",
            f"{len(rows)} total: {d0} while the lab was built and during the development run, "
            f"{len(rows) - d0} during this programme")
    if (d.spend or {}).get("total") is not None:
        add("What the programme cost, measured.", "T14, spend.json",
            f"${d.spend['total']:,.2f} of a ${d.spend.get('cap', 0):,.0f} cap (the development "
            f"run, before it: ${sum(r.get('cost_usd', 0) for r in d.runs if r.get('kind') == 'development'):,.2f})")
    inval = [r for r in d.rollouts if not r.get("valid")]
    add("Invalid rollouts are excluded, counted and listed by reason.", "T13",
        f"{len(inval)} of {len(d.rollouts):,} = {len(inval) / max(1, len(d.rollouts)):.2%}")
    for split in ("holdout", "train"):
        n = len({r["task"] for r in d.bench(runs=ev, split=split)})
        if n:
            add(f"The {split} set carries a measurement here.", "T2", f"{n} tasks")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated table/figure ids, e.g. T4,F2")
    ap.add_argument("--out", default=str(REPORTS))
    a = ap.parse_args()
    out = Path(a.out)
    T.TABLES = out / "tables"
    F.FIGURES = out / "figures"
    T.TABLES.mkdir(parents=True, exist_ok=True)
    F.FIGURES.mkdir(parents=True, exist_ok=True)
    want = {x.strip() for x in a.only.split(",") if x.strip()}

    d = Data()
    print(f"runs: {[r['run'] for r in d.runs]}")
    print(f"  evaluation {d.evaluation} · control {d.control} · development {d.development}")
    print(f"  rollouts {len(d.rollouts)} · sessions {len(d.sessions)} · items {len(d.items)}")

    for s in d.scope:
        f = d.firing(s.get("run")).get(s.get("candidate"))
        if f and f.get("visible"):
            s["measured_fire_rate"] = f["fired"] / f["visible"]
    cards = scorecard(d)
    (out / "data" / "scorecard.json").write_text(json.dumps(cards, indent=1) + "\n")
    (out / "data" / "tier-rubric.json").write_text(
        json.dumps(tier_rubric(d, d.evaluation or d.development), indent=1) + "\n")

    jobs = [
        ("T1", lambda: T.t1_the_lab(d)), ("T2", lambda: T.t2_scenarios(d)),
        ("T3", lambda: T.t3_scorecard(d, cards)), ("T4", lambda: T.t4_main(d)),
        ("T5", lambda: T.t5_trace(d)), ("T6", lambda: T.t6_items(d)),
        ("T7", lambda: T.t7_ablations(d)), ("T8", lambda: T.t8_gates(d)),
        ("T9", lambda: T.t9_corrections(d)), ("T10", lambda: T.t10_prune(d)),
        ("T11", lambda: T.t11_harvest(d)), ("T12", lambda: T.t12_findings(d)),
        ("T13", lambda: T.t13_invalid(d)), ("T14", lambda: T.t14_cost(d)),
        ("T15", lambda: T.t15_model_change(d)), ("T16", lambda: T.t16_defects(d)),
        ("T17", lambda: T.t17_external(d)), ("T18", lambda: T.t18_claims(d, claims(d, cards))),
        ("T19", lambda: T.t19_scope(d)), ("T20", lambda: T.t20_judge(d)),
        ("F1", lambda: F.f1_calibration(d)), ("F2", lambda: F.f2_headline(d)),
        ("F3", lambda: F.f3_forest(d)), ("F4", lambda: F.f4_heatmap(d)),
        ("F5", lambda: F.f5_corrections(d)), ("F6", lambda: F.f6_items_over_rounds(d)),
        ("F7", lambda: F.f7_replicate_matrix(d)), ("F8", lambda: F.f8_cost_vs_rate(d)),
        ("F9", lambda: F.f9_firing(d)), ("F10", lambda: F.f10_gates(d)),
        ("F11", lambda: F.f11_gain_vs_regression(d)), ("F12", lambda: F.f12_failure_taxonomy(d)),
        ("F13", lambda: F.f13_noise(d)), ("F14", lambda: F.f14_cost(d)),
        ("F15", lambda: F.f15_description(d)), ("F16", lambda: F.f16_model_change(d)),
        ("F17", lambda: F.f17_external(d)), ("F18", lambda: F.f18_scope(d)),
        ("F19", lambda: F.f19_trigger(d)),
    ]
    failed = []
    for name, fn in jobs:
        if want and name not in want:
            continue
        try:
            p = fn()
            print(f"  {name:4} -> {Path(p).name}")
        except Exception as ex:                            # noqa: BLE001
            failed.append((name, f"{type(ex).__name__}: {ex}"))
            print(f"  {name:4} -> FAILED  {type(ex).__name__}: {ex}")
    if not want or "APPENDIX" in want:
        import appendix
        appendix.REPORTS, appendix.OUT = out, out / "appendix"
        try:
            appendix.main()
        except Exception as ex:                        # noqa: BLE001
            failed.append(("APPENDIX", f"{type(ex).__name__}: {ex}"))
            print(f"  APPENDIX -> FAILED  {type(ex).__name__}: {ex}")
    if not want or "REPORT" in want:
        import report
        report.REPORTS = out
        try:
            print(f"  {'REPORT':4} -> {Path(report.main() or '') or 'REPORT.md'}")
        except Exception as ex:                        # noqa: BLE001
            failed.append(("REPORT", f"{type(ex).__name__}: {ex}"))
            print(f"  REPORT -> FAILED  {type(ex).__name__}: {ex}")
    print(f"\ntables -> {T.TABLES}\nfigures -> {F.FIGURES}")
    counts = {}
    for c in cards:
        counts[c.get("verdict", "?")] = counts.get(c.get("verdict", "?"), 0) + 1
    print("scorecard: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if failed:
        print(f"\n{len(failed)} FAILED:")
        for n, why in failed:
            print(f"  {n}: {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
