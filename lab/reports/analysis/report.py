#!/usr/bin/env python3
"""report.py — assemble REPORT.md from the tables, the figures and the scorecard.

    lab/reports/analysis/run.sh --report

The report contains **no hand-typed numbers**. The prose is written here; every
figure it quotes is read back out of `reports/data/` or the generated tables, so
the report and the tables cannot disagree, and re-running this after more data
arrives updates the sentences as well as the numbers.

Where a block of the programme has not run, the section says so in its own words
rather than being omitted — a reader should be able to see the shape of what is
missing, not just its absence.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stats as S                                    # noqa: E402
from load import FAMILIES, RULE_FAMILIES, Data       # noqa: E402

REPORTS = HERE.parent
CORTEX = REPORTS.parent.parent


def half_up(x):
    """A share as a whole percentage, rounded half up (as the paper's tables round)."""
    return f"{int(100 * x + 0.5 + 1e-9)}%"


def pctv(x, nan="—"):
    return nan if x != x else f"{x * 100:.0f}%"


def pp(x, nan="—"):
    return nan if x != x else f"{x * 100:+.1f}"


class Report:
    def __init__(self):
        self.d = Data()
        self.cards = {c["id"]: c for c in json.loads(
            (REPORTS / "data" / "scorecard.json").read_text())} \
            if (REPORTS / "data" / "scorecard.json").exists() else {}
        self.L = []

    # ---- helpers ---------------------------------------------------------
    def w(self, *lines):
        self.L.extend(lines)

    def card(self, hid):
        return self.cards.get(hid, {})

    def verdict(self, hid):
        return self.card(hid).get("verdict", "INCONCLUSIVE")

    def line(self, hid):
        """`**H1** SUPPORTED — +42.0 points [+18.0, +61.0]`"""
        c = self.card(hid)
        bits = [f"**{hid}** {c.get('verdict', 'INCONCLUSIVE')}"]
        if c.get("estimate") and c["estimate"] != "—":
            bits.append(c["estimate"])
        if c.get("interval") and c["interval"] != "—":
            bits.append(c["interval"])
        return " — ".join(bits)

    def missing(self, what):
        self.w(f"> **Not measured.** {what}", "")

    def reads(self, run, source, arms=None, split=None, flags=("text",), rule_only=False):
        """(rollouts that read something through git, rollouts) from the session records."""
        runs = run if isinstance(run, (list, tuple)) else [run]
        rs = [r for r in self.d.transcripts if r["run"] in runs and r["source"] == source
              and (arms is None or r.get("arm") in arms) and (split is None or r.get("split") == split)
              and (not rule_only or r.get("family") in RULE_FAMILIES)]
        return sum(1 for r in rs if set(flags) & set(r["reads"])), len(rs)

    # ---- the report ------------------------------------------------------
    def build(self):
        d = self.d
        ev, ct, dev = d.evaluation, d.control, d.development
        self.head(ev, ct, dev)
        self.summary()
        self.setup(ev, ct, dev)
        self.calibration()
        self.what_cortex_did()
        self.main_result()
        self.corrections()
        self.tiers()
        self.ablations()
        self.gates()
        self.pruning()
        self.reproducibility()
        self.stronger_model()
        self.second_repository()
        self.predicting()
        self.failures_noise_cost()
        self.threats()
        self.reproduce()
        return "\n".join(self.L) + "\n"

    # 0 -------------------------------------------------------------------
    def head(self, ev, ct, dev):
        d = self.d
        runs = d.runs
        tag = next((r.get("cortex_tag") for r in runs if r.get("cortex_tag")), "v1.0-eval")
        nroll = len(d.rollouts)
        dev_cost = sum(r.get("cost_usd", 0) for r in runs if r.get("kind") == "development")
        prog = (d.spend or {}).get("total")
        cost_line = (f"${prog:,.0f} measured, of a ${d.spend.get('cap', 1500):,.0f} cap "
                     f"(+ ${dev_cost:,.0f} for the development run, before the programme)"
                     if prog is not None else f"${sum(r.get('cost_usd', 0) for r in runs):,.0f}")
        self.w(
            "# Does a measured context loop earn its place?",
            "",
            "_The Cortex evaluation programme: what the loop does, what it costs, and "
            "where it fails._",
            "",
            f"_Generated {datetime.now().isoformat(timespec='minutes')} from "
            f"`reports/data/` by `analysis/report.py`. Every result below is computed from "
            f"those rows. The few figures that describe the design (the fifteen scenarios "
            f"written for this programme, the relevance floor) and the judge's own validation "
            f"(J0, from `jev/RESULTS.md`) are quoted._",
            "",
            "| | |",
            "|---|---|",
            f"| System under test | Cortex, frozen at `{tag}` |",
            f"| Evaluation runs | {', '.join(ev) or '—'} |",
            f"| Control runs | {', '.join(ct) or '—'} |",
            f"| Development run | {', '.join(dev) or '—'} — reported beside, **never pooled** |",
            f"| Rollouts | {nroll:,} in `rollouts.jsonl` (the development run's included; the "
            f"gate and prune tests' sweeps are in `gates.jsonl` and `prune-sweeps.jsonl`) |",
            f"| Spend | {cost_line} |",
            "",
            "---", "")

    # 1 -------------------------------------------------------------------
    def summary(self):
        self.w("## 1. Summary", "")
        h1, h2 = self.card("H1"), self.card("H2")
        self.w(
            "**The thesis.** An agent's context should be treated as something you "
            "measure rather than something you curate. Cortex proposes a skill or a "
            "rule from what went wrong in real sessions, runs the agent with and "
            "without it on tasks harvested from those sessions, and keeps it only if "
            "the pass rate moves and nothing else breaks. This programme asks whether "
            "that loop works, whether its gates are calibrated, and what it costs.",
            "")
        if h1.get("estimate"):
            self.w(
                f"**The headline.** On holdout tasks the agent never saw during "
                f"evolution, the harness Cortex evolved beats no harness at all by "
                f"**{h1['estimate']}** ({h1.get('interval', '')}), pooled over the four "
                f"families that have a house rule. The control family, which has none, "
                f"moves by {h2.get('estimate', '—')}.",
                "")
        self.w("![headline](figures/F2-headline.png)", "",
               "### The scorecard", "",
               "| # | Hypothesis | Verdict | Estimate | Interval |",
               "|---|---|---|---|---|")
        for hid in [f"H{i}" for i in range(17)]:
            c = self.card(hid)
            if not c:
                continue
            self.w(f"| {hid} | {c['hypothesis']} | **{c.get('verdict', '—')}** | "
                   f"{c.get('estimate', '—')} | {c.get('interval', '—')} |")
        self.w("", "Full detail, with the margin for each, in "
                   "[`tables/T3-scorecard.md`](tables/T3-scorecard.md).", "", "---", "")

    # 2 -------------------------------------------------------------------
    def setup(self, ev, ct, dev):
        d = self.d
        self.w("## 2. Setup", "",
               "**The lab.** A synthetic Python repository, `shopkit`, with a real "
               "history and four house rules a model breaks by default, plus one "
               "control family that has no rule at all:", "")
        self.w("| Family | The house rule | What checks it |", "|---|---|---|")
        rules = {"A": ("every user-visible change gets a CHANGELOG line", "the diff"),
                 "B": ("amounts are integer cents, scaled with the rates helpers", "`tools/lint.py`"),
                 "C": ("a new exporter needs module, registry, docs row and golden file", "`tools/lint.py`"),
                 "D": ("— none, by design", "its own test and the suite"),
                 "E": ("read the clock through `shop.clock`", "`tools/lint.py`")}
        for f in "ABCDE":
            self.w(f"| **{f}** {FAMILIES[f]} | {rules[f][0]} | {rules[f][1]} |")
        lab_runs = ev + ct + dev + d.remeasure_of(dev)       # the lab's own tasks only
        ho = len({r["task"] for r in d.bench(runs=lab_runs, split="holdout")})
        tr = len({r["task"] for r in d.bench(runs=lab_runs, split="train")})
        self.w("", f"**The tasks.** {ho + tr} scenarios: {tr} training and {ho} holdout, "
                   f"{ho // len(FAMILIES)} holdout per family, every one of them carrying a "
                   f"measurement here. The holdout is never seen by `/harvest` or `/evolve`, and "
                   f"the fifteen scenarios written for this programme were derived only "
                   f"from `CONTRIBUTING.md` and the family definition — never from the "
                   f"text of anything D0 had already evolved. See "
                   f"[`T1`](tables/T1-the-lab.md), [`T2`](tables/T2-scenarios.md).", "")
        self.w("**The arms.** An arm is a harness and nothing else — the same tasks, "
               "the same oracle, the same model:", "",
               "| Arm | What it is |", "|---|---|",
               "| `none` | the minimal `CLAUDE.md` `cortex init` writes, nothing else |",
               "| `none2` | built by the same code as `none`: the A/A check |",
               "| `evolved` | what that run kept |",
               "| `kitchen` | `none` + the whole of `CONTRIBUTING.md`, always on |",
               "| `ideal` | hand-written, in the forms the design predicted |",
               "| `accept-all` | `evolved` + everything that run buried |",
               "| `flat` | `evolved`'s words with the scope removed |",
               "| `desc-only` | `evolved`'s skills keep description and paths; the body becomes filler |", "")
        jev_on = [r["run"] for r in d.runs if (r.get("jev") or {}).get("enabled")]
        self.w(f"**The judge.** Cortex ships an optional judge in its *proposal* layer. "
               f"Every number in this report that feeds a hypothesis was produced with "
               f"it **off**; {'runs ' + ', '.join(jev_on) + ' had it on and are never pooled' if jev_on else 'no run in this programme had it on'}. "
               f"The gates contain no model of any kind, and Cortex's own suite asserts "
               f"the string `jev` appears nowhere in `score.sh`, `preflight.sh` or "
               f"`sweep.sh`. [`T19`](tables/T19-judge.md) prints one row per run, "
               f"including the off ones — \"off\" is the claim that has to be checkable.",
               "", "---", "")

    # 3 -------------------------------------------------------------------
    def calibration(self):
        d = self.d
        self.w("## 3. Calibration: what the agent does with no harness (H0)", "")
        rows = d.bench(runs=d.evaluation or d.development, arms=("none",), split="holdout")
        if not rows:
            self.missing("No `none` rollouts yet.")
            self.w("---", "")
            return
        self.w("| Family | pass rate | n |", "|---|---|---|")
        for f in "ABCDE":
            k, n, p = S.rate(rows, family=f)
            lo, hi = S.wilson(k, n)
            self.w(f"| {f} {FAMILIES[f]} | {pctv(p)} [{pctv(lo)}–{pctv(hi)}] | {n} |")
        self.w("", self.line("H0"), "",
               "The control family is the one to read first: the agent passes D "
               "without help, so whatever the harness does later is not simply "
               "\"the agent got better at everything\". The other four are the room "
               "there is to move.", "",
               "![calibration](figures/F1-calibration.png)", "", "---", "")

    # 4 -------------------------------------------------------------------
    def what_cortex_did(self):
        d = self.d
        self.w("## 4. What Cortex did", "")
        if not d.items:
            self.missing("No run has produced an item yet.")
            self.w("---", "")
            return
        self.w("| Run | cycles | kept | buried |", "|---|---|---|---|")
        for r in d.runs:
            kept = [i["name"] for i in d.kept(r["run"])]
            bur = [i["name"] for i in d.buried(r["run"])]
            self.w(f"| {r['run']} ({r['kind']}) | {r.get('cycles', '—')} | "
                   f"{', '.join(f'`{k}`' for k in kept) or '—'} | {len(bur)} |")
        self.w("", "Every cycle, its theme, its verdict and what it cost is in "
                   "[`T5`](tables/T5-trace.md); every item's text, scope and firing "
                   "data in [`T6`](tables/T6-items.md).", "",
               "![items](figures/F6-items.png)", "", "---", "")

    # 5 -------------------------------------------------------------------
    def main_result(self):
        d = self.d
        self.w("## 5. The main result (H1, H2)", "")
        ev = d.evaluation or d.development
        rows = d.bench(runs=ev, arms=("none", "evolved"), split="holdout")
        if not rows:
            self.missing("No benchmark has run yet.")
            self.w("---", "")
            return
        # the complete-case set, the scenarios valid in every run, is the primary;
        # the all-valid pooled row is the secondary, beside it
        keep = set(d.complete_case_tasks(ev, arms=("none", "evolved"), split="holdout"))
        cc = [r for r in rows if r["task"] in keep]
        self.w(f"Over the {len({r['task'] for r in cc if r.get('family') in RULE_FAMILIES})} "
               f"rule-family scenarios valid in every run (the complete-case set):", "",
               "| Family | none | evolved | paired difference | 95% CI |",
               "|---|---|---|---|---|")
        for f in list("ABCDE") + [None]:
            fams = [f] if f else list(RULE_FAMILIES)
            cs = S.cells(cc, "none", "evolved", families=fams, split="holdout")
            if not cs:
                continue
            sel = cc if f else [r for r in cc if r.get("family") in RULE_FAMILIES]
            _, _, p0 = S.rate(sel, arm="none", **({"family": f} if f else {}))
            _, _, p1 = S.rate(sel, arm="evolved", **({"family": f} if f else {}))
            lo, hi, _ = S.two_way_bootstrap(cs)
            label = f"{f} {FAMILIES[f]}" if f else "**A+B+C+E pooled**"
            self.w(f"| {label} | {pctv(p0)} | {pctv(p1)} | {pp(S.paired_mean(cs))} | "
                   f"[{pp(lo)}, {pp(hi)}] |")
        ca = S.cells(rows, "none", "evolved", families=list(RULE_FAMILIES), split="holdout")
        if ca:
            lo, hi, _ = S.two_way_bootstrap(ca)
            sel = [r for r in rows if r.get("family") in RULE_FAMILIES]
            self.w(f"| A+B+C+E pooled, every valid scenario (secondary) | "
                   f"{pctv(S.rate(sel, arm='none')[2])} | {pctv(S.rate(sel, arm='evolved')[2])} | "
                   f"{pp(S.paired_mean(ca))} | [{pp(lo)}, {pp(hi)}] |")
        self.w("", self.line("H1"), "", self.line("H2"), "",
               "The interval is a two-way bootstrap over **runs and tasks**, not over "
               "rollouts: five rollouts of one task are five draws of the same coin, "
               "and a task is a draw from the population of tasks we could have "
               "written. Wilson intervals appear in "
               "[`T4`](tables/T4-main.md) as description only, labelled as such.", "",
               "![forest](figures/F3-forest.png)", "")
        # `rows` holds only none/evolved: the A/A needs `none2`'s own rows, or it could
        # never be found and the report said the arm "has not run" when it had
        aa = S.cells(d.bench(runs=ev, arms=("none", "none2"), split="holdout"),
                     "none", "none2", families=list("ABCDE"), split="holdout")
        self.w("### The A/A check", "")
        if aa:
            lo, hi, _ = S.two_way_bootstrap(aa)
            m = S.paired_mean(aa)
            excl = lo > 0 or hi < 0
            self.w(f"`none2` is the `none` harness built by the same function, measured "
                   f"as if it were a treatment. Its difference from `none` is "
                   f"**{pp(m)} [{pp(lo)}, {pp(hi)}]**.", "",
                   ("**That interval excludes zero.** Every other result in this report "
                    "should be treated as suspect until this is explained."
                    if excl else
                    "The interval includes zero, which is what it must do. It is the "
                    "floor under every other difference here: a gain smaller than this "
                    "arm's spread is not a gain."), "")
        else:
            self.missing("The A/A arm has not run.")
        self.w("![heatmap](figures/F4-heatmap.png)", "", "---", "")

    # 6 -------------------------------------------------------------------
    def corrections(self):
        self.w("## 6. Corrections (H4)", "")
        if not (self.d.control and self.d.evaluation):
            self.missing("H4 needs both an evaluation run and a control run. The "
                         "control runs the same sessions with `/evolve` switched off, "
                         "so its fall is what the agent learns from the code it has "
                         "already written — and only the difference is evidence.")
        else:
            import math
            ev_, ct_ = self.d.evaluation, self.d.control
            self.w(self.line("H4"), "",
                   f"This is a description, not a tested effect. The estimate is over all "
                   f"sessions, including those before any item went live, and with "
                   f"{len(ct_)} control run(s) no permutation of the run "
                   f"labels can give p below {1 / math.comb(len(ev_) + len(ct_), len(ct_)):.1f}.", "",
                   "See [`T9`](tables/T9-corrections.md).", "")
        self.w("![corrections](figures/F5-corrections.png)", "", "---", "")

    # 7 -------------------------------------------------------------------
    def tiers(self):
        d = self.d
        self.w("## 7. Tiers and firing (H3, H11)", "")
        rub = REPORTS / "data" / "tier-rubric.json"
        if rub.exists():
            rows = json.loads(rub.read_text())
            if rows:
                self.w("| Item | family | form | scope | fires where it is about | score |",
                       "|---|---|---|---|---|---|")
                for r in rows:
                    tick = lambda b: "yes" if b else "**no**"
                    self.w(f"| `{r['name']}` | {r['family'] or '—'} | {tick(r['form'])} | "
                           f"{tick(r['scope'])} | {tick(r['area'])} "
                           f"({half_up(r['own_rate'])} vs {half_up(r['other_rate'])}) | "
                           f"{r['score']}/3 |")
                self.w("", self.line("H3"), "")
                paths = {(i["run"], i["name"]): i.get("paths") for i in self.d.items}
                kind = {(i["run"], i["name"]): i.get("kind") for i in self.d.items}
                wide = [r for r in rows if paths.get((r["run"], r["name"])) == ["shop/**"]]
                crule = [r for r in rows if r["family"] == "C" and kind.get((r["run"], r["name"])) == "rule"]
                self.w(f"The rubric is lenient on two points. It passes every path-scoped "
                       f"item on scope, although a rule on `shop/**` also covers families it is "
                       f"not about; and every path-scoped rule on form, although a duty the task "
                       f"itself names, such as adding an exporter, would sit better in a skill, "
                       f"which the {len(crule)} exporter rules are not. Under the stricter reading, "
                       f"at most {len(rows) - len(wide) - len(crule)} of the {len(rows)} items "
                       f"would score 3/3.", "")
        # Rules against skills, counted. It decides what H11 can even be asked of.
        d = self.d
        kept = [i for i in d.items if i["fate"] == "kept"]
        by_run = {}
        for i in kept:
            b = by_run.setdefault(i["run"], [0, 0])
            b[0 if i["kind"] == "rule" else 1] += 1
        if by_run:
            self.w("### What the loop keeps: rules, almost always", "",
                   "| run | items kept | rules | skills |", "|---|---|---|---|")
            for run, (r, k) in by_run.items():
                self.w(f"| {run} | {r + k} | {r} | {k} |")
            rep = [v for run, v in by_run.items() if run not in d.development]
            rr, kk = sum(v[0] for v in rep), sum(v[1] for v in rep)
            if rr + kk:
                self.w("", f"Across the replicate runs the loop kept **{kk} skill"
                           f"{'' if kk == 1 else 's'} of {rr + kk} items**. The development run is the outlier: it "
                           f"kept skills for two of its three.", "",
                       "**There is a mechanism for this, and it is the asymmetry below.** "
                       "A rule enters the context whenever the agent reads a matching "
                       "file, so it fires every time it is present and a sweep can "
                       "always measure it. A skill has to be *chosen*, and gate 5 kills "
                       "a candidate that never loaded — so a skill whose description "
                       "names a side duty rather than the task at hand tends to be "
                       "killed for never firing, while the same advice written as a "
                       "rule survives. The loop is not expressing a preference about "
                       "form; it is measuring, and one form is far easier to measure.",
                       "",
                       "**This limits what can be asked of H11.** `desc-only` rewrites "
                       "skill bodies, so on a harness of nothing but rules it changes "
                       "nothing at all. The description hypothesis can only be put to "
                       "runs that kept skills, and the arm ran on R1, which kept one of "
                       "four: a weak footing for the arm.", "")
        self.w("**A rule is loaded; a skill must be chosen.** That asymmetry is the "
               "most useful thing the firing data says. A rule enters the context "
               "whenever the agent reads a file its glob matches, so its fire rate "
               "given visibility is 1 by construction. A skill is offered and the "
               "agent decides — which means a skill whose description names a *side "
               "duty* rather than the task at hand can sit in context all day and "
               "never be invoked.", "",
               "![firing](figures/F9-firing.png)", "",
               "### The description hypothesis (H11)", "")
        # on the DATA: H11 is also INCONCLUSIVE when the arm ran but could perturb too
        # little of the harness to decide, and "has not run" would then be false
        if not self.d.bench(arms=("desc-only",)):
            self.missing("The `desc-only` arm has not run. It keeps each skill's name, "
                         "description and paths and replaces the body with neutral "
                         "filler of about the same length; whatever it recovers of "
                         "`evolved`'s gain was never coming from the body.")
        else:
            self.w(self.line("H11"), "")
            from rebuild import arm_pair
            runs_ = [r for r in (self.d.evaluation or []) if self.d.arms_of(r).get("desc-only")]
            rd = arm_pair(self.d, runs_, "none", "desc-only", families=("C",))
            rf = arm_pair(self.d, runs_, "none", "evolved", families=("C",))
            if rd and rf:
                sh, lo, hi = S.share_recovered(rd["cells"], rf["cells"])
                dc = [r for r in self.d.transcripts if r["run"] in runs_ and r.get("arm") == "desc-only"
                      and r.get("family") == "C"]
                read = [r for r in dc if "text" in r["reads"]]
                self.w(f"The margin is stated per family. Only C's skill was rewritten, and there "
                       f"the arm recovered {sh:.0%} [{lo:.0%}, {hi:.0%}] of the gain, below the "
                       f"margin's half"
                       + (f"; and of its {len(dc)} rollouts on C, the {sum(r['pass'] for r in dc)} "
                          f"that passed were all among the {len(read)} that printed the skill's "
                          f"real body through git (§15), so even that share overstates what the "
                          f"description alone did" if dc and sum(r['pass'] for r in read) == sum(r['pass'] for r in dc) else "")
                       + ".", "")
            self.w("![description](figures/F15-description.png)", "")
        self.w("---", "")

    # 8 -------------------------------------------------------------------
    def ablations(self):
        self.w("## 8. Ablations: which part is doing the work (H6, H7, H8)", "")
        d = self.d
        acc = [r for r in (d.evaluation or []) if d.bench(runs=[r], arms=("accept-all",))]
        bur = [(r, i["name"]) for r in acc for i in d.buried(r)]
        fates = {d.rule_fate(r, n) for r, n in bur}
        h6 = ("**Does the burial matter?** `accept-all` is `evolved` plus every candidate that "
              "run buried.")
        if acc and bur and fates == {"unscored"}:
            h6 += (f" It ran on {', '.join(acc)}, whose {'only burial' if len(bur) == 1 else 'burials'} "
                   f"({', '.join(f'`{n}`' for _r, n in bur)}) the /evolve agent made after score.sh "
                   f"returned RERUN, not a gate: the arm tests that burial, not the gates.")
        for hid, text in (("H6", h6),
                          ("H7", "**Do the tiers earn their cost?** `flat` is "
                                 "`evolved`'s words with the scope removed: gated "
                                 "skills lose their `paths`, path-scoped rules become "
                                 "path-less rules that load on every turn."),
                          ("H8", "**Is the loop efficient?** `kitchen` puts the whole "
                                 "of `CONTRIBUTING.md` in context on every turn; "
                                 "`ideal` is what someone who already knew all four "
                                 "house rules would have written.")):
            self.w(text, "")
            self.w(self.line(hid) if self.card(hid).get("estimate")
                   else "> **Not measured** — that arm has not run.", "")
        self.w("![cost vs rate](figures/F8-cost-vs-rate.png)", "",
               "Up and to the left is the whole claim: the same pass rate for fewer "
               "characters in every single turn's context. See "
               "[`T7`](tables/T7-ablations.md).", "", "---", "")

    # 9 -------------------------------------------------------------------
    def gates(self):
        d = self.d
        self.w("## 9. Are the gates calibrated? (H5)", "")
        if not d.gates:
            self.missing("The gate testbed has not run. It pushes 29 candidates whose "
                         "right verdict was written down in advance — 20 placebos, 5 "
                         "harmful, 4 known-good — through the real pipeline.")
            self.w("---", "")
            return
        self.w(self.line("H5"), "", "See [`T8`](tables/T8-gates.md).", "")
        sv = lambda g: ((g.get("confirm") or {}).get("verdict")
                        or (g.get("screen") or {}).get("verdict") or g["verdict"])
        plac = [g for g in d.gates if g["type"].startswith("placebo")]
        opened = sum(1 for g in plac if (g.get("screen") or {}).get("candidate_fired_runs"))
        harm = [g for g in d.gates if g["type"] == "harmful"]
        h_rerun = [g for g in harm if sv(g) == "RERUN"]
        broken = [(g, t) for g in h_rerun for t in ((g.get("screen") or {}).get("protected_broken") or [])]
        broke_n = len({g["name"] for g, _t in broken})
        pt = {(g["name"], x["task"]): x for g in h_rerun for x in (g.get("screen") or {}).get("per_task", [])}
        broke_t = ", ".join(f"task {t}, {pt[(g['name'], t)]['base']:.0%} to {pt[(g['name'], t)]['cand']:.0%} "
                            f"of its runs" for g, t in broken if (g["name"], t) in pt)
        lost = [g for g in d.gates if g["type"] == "positive" and g.get("verdict") != "KEEP"]
        self.w(f"**What the test shows, and what it does not.** No placebo was kept. But the "
               f"agent opened {opened} of the {len(plac)} placebos on their screens, so every "
               f"one of them was stopped by gate 5 (a candidate that never loaded is never "
               f"kept) or left unscored, before the gain, net and worst-drop gates had anything "
               f"to judge. The test shows that the pipeline refuses what never loads; it does "
               f"not show how the other gates treat a candidate that loads and does nothing. "
               f"Harm was not judged either: {len(h_rerun)} of the {len(harm)} harmful "
               f"candidates were rules that loaded, but their screens ran, as screens do, on "
               f"failing tasks, where no gain could show"
               + (f"; {'one' if broke_n == 1 else broke_n} screen{'' if broke_n == 1 else 's'} also met a task that passed without its rule, and the "
                  f"rule broke it ({broke_t}), but score.sh returns RERUN whenever no task can "
                  f"show a gain, before any regression gate" if broke_n else "")
               + f"; the other {len(harm) - len(h_rerun)} were skills the agent never opened.", "")
        if lost:
            self.w(f"The {len(lost)} known-good item(s) the gates did not keep, "
                   + ", ".join(f"`{g['name']}`" for g in lost) + ", are the always-on skills: "
                   "the agent must choose to invoke them with nothing in the task pointing to "
                   "them, and on their screens it never did. The positives kept are a "
                   "path-scoped rule and a gated skill, both tied to the files a task touches, "
                   "the asymmetry of §7 again.", "")
        self.w("The gates contain no Jev code at all, so whatever this test measures is a "
               "property of the gates alone.", "",
               "![gates](figures/F10-gates.png)", "", "---", "")

    # 10 ------------------------------------------------------------------
    def pruning(self):
        d = self.d
        self.w("## 10. Pruning (H10)", "")
        if not d.prune:
            self.missing("The prune testbed has not run.")
            self.w("---", "")
            return
        self.w(self.line("H10"), "", "See [`T10`](tables/T10-prune.md).", "")
        miss = [q for q in d.prune if not q.get("matches")]

        def sweep(item):
            return [r for r in d.prune_sweeps if r["run"] == "PRUNE" and r["removed"] == item
                    and r.get("valid", 1)]
        deleted_unfired = []
        for q in d.prune:
            rs = sweep(q["item"])
            if q.get("verdict") == "ACCEPT" and rs and not any(
                    q["item"] in (r.get("fired") or []) for r in rs if r["arm"] == "base"):
                deleted_unfired.append(q["item"])
        if miss:
            parts = []
            for q in miss:
                rs = sweep(q["item"])
                base = [r for r in rs if r["arm"] == "base"]
                fired = sum(1 for r in base if q["item"] in (r.get("fired") or []))
                if rs:
                    rate = lambda arm, t: (sum(r["pass"] for r in rs if r["arm"] == arm and r["task"] == t)
                                           / max(1, sum(1 for r in rs if r["arm"] == arm and r["task"] == t)))
                    lost = sorted(t for t in {r["task"] for r in rs} if rate("cand", t) < rate("base", t))
                    parts.append(f"`{q['item']}`, expected {q['expected']}, got {q['verdict']}: it "
                                 f"fired in {fired} of the {len(base)} base rollouts of its sweep, "
                                 f"so it could not have been deleted, and its verdict came from "
                                 f"runs lost on {len(lost)} task(s) when it was removed")
                else:
                    parts.append(f"`{q['item']}`, expected {q['expected']}, got {q['verdict']}: "
                                 f"the plan never swept it, since it leaves out an item that no "
                                 f"sweep could delete, so the item stayed without a verdict")
            self.w("Where the verdict differed from the expected one: "
                   + "; ".join(parts) + f". Items that never fired and were deleted: "
                   f"**{len(deleted_unfired)}**.", "")
        self.w("", "The question worth asking of a pruner is not whether it deletes "
                   "rubbish. It is whether it **refuses to delete what it never saw "
                   "fire** — a skill for something that happens twice a year looks "
                   "exactly like a useless one in between, and is precisely the one "
                   "you want when it happens.", "", "---", "")

    # 11 ------------------------------------------------------------------
    def reproducibility(self):
        from tables import _own_family
        d = self.d
        self.w("## 11. Does it replicate? (H9, H12)", "")
        runs = [r["run"] for r in d.runs if r["kind"] in ("development", "evaluation")]
        if runs:
            # What each run learned, by family: the form AND the scope, because they
            # replicate differently and that difference is the result.
            cell = {}
            for run in runs:
                for it in d.kept(run):
                    fam = _own_family(it["name"], d, run)
                    if fam:
                        form = ("rule" if it["kind"] == "rule" else
                                ("gated skill" if it.get("paths") else "always-on skill"))
                        paths = ", ".join(f"`{x}`" for x in (it.get("paths") or [])) or "—"
                        cell.setdefault((run, fam), []).append((form, paths))
            self.w("| family | " + " | ".join(runs) + " |", "|---" * (len(runs) + 1) + "|")
            for fam in RULE_FAMILIES:
                row = []
                for run in runs:
                    fs = cell.get((run, fam)) or []
                    row.append("<br>".join(f"{a} {b}" for a, b in fs) if fs else "—")
                self.w(f"| **{fam}** {FAMILIES[fam].split(' (')[0]} | " + " | ".join(row) + " |")
            scopes, forms = {}, {}
            for (run, fam), fs in cell.items():
                scopes.setdefault(fam, set()).add(" + ".join(sorted(b for _, b in fs)))
                forms.setdefault(fam, set()).add(" + ".join(sorted(a for a, _ in fs)))
            agree_scope = [f for f, v in scopes.items() if len(v) == 1]
            agree_form = [f for f, v in forms.items() if len(v) == 1]
            pairs, agree = [], []
            for i, a in enumerate(runs):
                for b in runs[i + 1:]:
                    fams = [f for f in RULE_FAMILIES if (a, f) in cell and (b, f) in cell]
                    if not fams:
                        continue
                    n = sum(1 for f in fams
                            if sorted(x[1] for x in cell[(a, f)])
                            == sorted(x[1] for x in cell[(b, f)]))
                    pairs.append(f"{a}/{b} {n}/{len(fams)}")
                    agree.append((n, len(fams)))
            tot_n = sum(n for n, _ in agree)
            tot_d = sum(dd for _, dd in agree) or 1
            self.w("", f"**Scope agrees on {len(agree_scope)} of {len(scopes)} families "
                       f"across all runs; form on {len(agree_form)}.** Pairwise, runs "
                       f"agree on scope in {tot_n} of {tot_d} comparable families "
                       f"({', '.join(pairs)}).", "")
            self.narrow_run(_own_family)
        self.w(self.line("H9"), "", self.line("H12"), "",
               "![replicate](figures/F7-replicate.png)", "", "---", "")

    def narrow_run(self, own):
        """The evaluation run that named files instead of globs, and how it got there, from
        score.sh's verdicts rather than the journal the /evolve agent wrote."""
        d = self.d
        narrow = next((run for run in d.evaluation
                       if (bs := [it for it in d.kept(run) if own(it["name"], d, run) == "B"])
                       and all("*" not in p for it in bs for p in (it.get("paths") or []))), None)
        if not narrow:
            return
        fam = lambda n: own(n, d, narrow)
        cands = [name for (run, name) in d.scored() if run == narrow]
        unsc = [n for n in cands if fam(n) == "B" and d.rule_fate(narrow, n) == "unscored"]
        kreg = [n for n in cands if fam(n) == "E" and d.rule_fate(narrow, n) == "killed-regression"]
        money = [it["name"] for it in d.kept(narrow) if fam(it["name"]) == "B"]

        def loaded(run, names):
            rs = [r for r in d.bench(runs=[run], arms=("evolved",), split="holdout")
                  if r.get("family") == "B"]
            return sum(1 for r in rs if set(names) & set(r.get("fired") or [])), len(rs)
        k, n = loaded(narrow, money)
        others = [loaded(run, [it["name"] for it in d.kept(run) if own(it["name"], d, run) == "B"])[0]
                  for run in d.evaluation if run != narrow]
        text = [f"**The runs differ in how wide a scope they chose.** The other runs chose "
                f"broad globs; {narrow} named individual files for its money and clock rules."]
        if kreg:
            c = d.scored()[(narrow, kreg[0])]
            conf = [s for s in c["sweeps"] if s["phase"] == "confirm"][-1]
            gate = "3" if "gate3" in conf["failed"] else "2"
            text.append(f"Its broad clock rule, `{kreg[0]}`, was killed by the gates: a task "
                        f"lost runs in the confirm (gate {gate})"
                        + (" and again in the recheck" if c.get("rechecked") else "") + ".")
        if unsc:
            unk = sum(1 for r in d.rollouts if r.get("source") == "sweep" and r["run"] == narrow
                      and r.get("candidate") == unsc[0] and r.get("fired") is None)
            text.append(f"Its broad money rule, `{unsc[0]}`, was not: score.sh returned RERUN, "
                        f"because the event streams of {unk} of its rollouts could not be read, "
                        f"and the /evolve agent buried it anyway, writing into its journal a "
                        f"regression the sweep does not contain.")
        text.append(f"The narrow money rules that followed loaded in {k} of the run's {n} "
                    f"held-out money rollouts, against at least {min(others) if others else '—'} "
                    f"in each other run. The gates judge a scope only on the tasks the loop has "
                    f"harvested; nothing in them can see that a scope is too narrow for tasks "
                    f"it has not met. Which scope to propose is the proposal layer's choice.")
        self.w(" ".join(text), "")

    # 12 ------------------------------------------------------------------
    def stronger_model(self):
        d = self.d
        self.w("## 12. A stronger model (H13)", "")
        mc = [r["run"] for r in d.of_kind("model-change")]
        if not mc:
            self.missing("The model-change study has not run.")
        else:
            self.w(self.line("H13"), "", "See [`T15`](tables/T15-model-change.md).", "")
            from rebuild import arm_pair
            c = arm_pair(d, mc, "none", "evolved", families=("C",))
            k = next((r["k"] for r in d.prune_sweeps if r["run"] == "M1"), None)
            if c:
                self.w(f"Read the removals with care. `/prune` made one pass under the stronger "
                       f"model, at k={k} runs per task and arm, and one pass at that k cannot tell "
                       f"a small effect from none: the exporter checklist it found removable still "
                       f"showed the largest held-out gain under that model, {pp(c['mean'])} "
                       f"[{pp(c['lo'])}, {pp(c['hi'])}] on family C.", "")
        self.w("A smaller gain under a stronger model is the **expected** result: "
               "a model that already follows some house rules has less to gain from "
               "being told them. That is a finding about where this loop is worth "
               "running, not a failure of it.", "",
               "![model change](figures/F16-model-change.png)", "", "---", "")

    # 13 ------------------------------------------------------------------
    def second_repository(self):
        d = self.d
        self.w("## 13. A repository we did not build (H14)", "")
        self.w("This section exists to answer the hardest attack on everything above: "
               "*you built the repository, the house rules and the tasks, so of course "
               "it works.*", "")
        if not d.external:
            self.missing("The second repository has not been measured yet.")
        else:
            self.w(self.line("H14"), "", "See [`T16`](tables/T16-external.md).", "")
            if any(e.get("harness_identical") for e in d.external):
                self.w("**The loop kept nothing here**, so the two arms are the same harness "
                       "and the benchmark is an A/A. The agent passed the "
                       "project's own tests and pinned linter on the first attempt in most "
                       "training sessions; with no correction recurring, `/evolve` declined "
                       "every cycle. That is evidence about *when* the loop has anything to "
                       "do — and none about whether what it learns transfers.", "")
        self.w("", "**Nothing here was written by us.** The repository is `hynek/"
                   "structlog`, chosen by a rule fixed before any candidate was "
                   "inspected. The tasks are its own commits, with the implementation "
                   "reverted and its own tests kept as the specification. The house "
                   "rule is its own `ruff` configuration (`select = [\"ALL\"]`). The "
                   "corrections are its own CI output, pasted back verbatim. The judge "
                   "is its own test suite plus its own linter.", "")
        bi, bn = self.reads("X1", "bench", flags=("impl",))
        ti, tn = self.reads("X1", "session", flags=("impl",))
        xb = [r for r in d.transcripts if r["run"] == "X1" and r["source"] == "bench"]
        xp = sum(r["pass"] for r in xb if "impl" in r["reads"])
        xo = [r for r in xb if "impl" not in r["reads"]]
        tr = [r for r in d.transcripts if r["run"] == "X1" and r["source"] == "session" and "impl" in r["reads"]]
        first = all(r.get("right_first_time") for r in tr)
        leak = (f" And the answer was within reach of git: a benchmark rollout started at the "
                f"upstream commit itself, with the implementation reverted only in the index and "
                f"the working tree, and {bi} of the {bn} rollouts printed it; "
                + (f"all of them passed" if xp == bi else f"{xp} of them passed")
                + f", against {sum(r['pass'] for r in xo)} of the other {len(xo)}. In training, "
                f"the upstream commits were ancestors of the session's own, and {ti} of the {tn} "
                f"sessions printed the upstream fix before writing its own"
                + (", which passed at the first attempt" if tr and first else "")
                + f". Both arms had one harness and the same "
                f"access, so the A/A difference stands; its pass rates are not those of an agent "
                f"working unaided." if bn else "")
        self.w("**Its own threats:** four holdout tasks, one run, real-world noise, and "
               "possible contamination — `structlog` is public and the model may have "
               "seen these commits." + leak + " It is reported here as corroboration and "
               "is **never pooled** with the lab.", "",
               "![external](figures/F17-external.png)", "", "---", "")

    # 13b -----------------------------------------------------------------
    def predicting(self):
        d = self.d
        self.w("## 13b. Predicting the verdict before paying for it (H15, H16)", "")
        self.w("**The boundary first, because it is the point.** Cortex's gates contain "
               "no model: `score.sh`, `preflight.sh` and `sweep.sh` are arithmetic over "
               "recorded pass rates, and a test asserts the string `jev` appears in none "
               "of them. The *proposal* layer may consult a judge — which theme recurs, "
               "which tier fits, how much of the task suite a candidate is actually "
               "about. A wrong proposal costs a cycle and the gates kill it; a wrong "
               "fitness value corrupts everything downstream and nothing catches it.", "")
        if not d.scope:
            self.missing("`scope-replay` has not run.")
        else:
            sc = [s for s in d.scope if s.get("run") in d.evaluation]
            fate = lambda s: d.rule_fate(s["run"], s["candidate"])
            val = lambda f, key: [s[key] for s in sc if fate(s) == f
                                  and isinstance(s.get(key), (int, float))]
            self.w("On the evaluation runs, with each candidate's fate as score.sh gives it:", "",
                   "| predictor | KEPT | BURIED on a regression (score.sh: gate 2 or 3) | separates? |",
                   "|---|---|---|---|")
            for label, key in (("relevance (needs a judge)", "relevance"),
                               ("breadth (free, deterministic)", "breadth")):
                a, b = val("kept", key), val("killed-regression", key)
                if a and b:
                    sep = "**yes**" if min(a) > max(b) else "no — they overlap"
                    self.w(f"| {label} | {', '.join(f'{x:.0%}' for x in sorted(a))} | "
                           f"{', '.join(f'{x:.0%}' for x in sorted(b))} | {sep} |")
            self.w("", self.line("H15"), "",
                   "So few regression kills make a thin comparison. The development run's "
                   "candidates, with the journal's fates, are in [`T18`](tables/T18-scope.md) "
                   "and are not pooled here.", "")
            flagged = [s for s in sc if isinstance(s.get("relevance"), (int, float))
                       and s["relevance"] < 0.35]
            alarms = [s for s in flagged if fate(s) == "kept"]
            saved = sum(s.get("cost_usd") or 0 for s in flagged if fate(s) != "kept")
            n_skip = len(flagged) - len(alarms)
            self.w(f"**The counterfactual, stated as a counterfactual.** On the evaluation "
                   f"runs, acting on the 0.35 relevance floor would have skipped **{n_skip}** "
                   f"candidate{'' if n_skip == 1 else 's'} that "
                   f"{'was' if n_skip == 1 else 'were'} later buried, saving "
                   f"**${saved:.2f}** — and would also have flagged **{len(alarms)}** "
                   f"that {'was' if len(alarms) == 1 else 'were'} KEPT. The saving is "
                   f"never quoted without that second number beside it.", "")
        self.w("![scope](figures/F18-scope.png)", "")
        self.w("### On the development run: two measurements of the same claim", "",
               "`jev/RESULTS.md` (J0), the judge's own validation, reported that relevance "
               "separates the development run's kept candidates from those buried on a "
               "regression. The replay of the same run (T18) finds that it does not. The two "
               "measure different things: J0 scored the candidates that reached a confirm "
               "sweep, on the tasks each was swept on, with fates from its own records; the "
               "replay scores every candidate the run proposed, on every task `cortex scope` "
               "says it would load on, with the fates the run's journal records. Only the "
               "replay is used for H15.", "")
        self.w("### Does the judge know when a skill will be invoked? (H16)", "")
        h16 = self.card("H16")
        if h16.get("estimate") and h16["estimate"] != "—":
            self.w(self.line("H16"), "",
                   ("The rank order is preserved, but it rests on the one prediction below "
                    "100 %, a skill of the development run: the evaluation runs' two gated "
                    "skills were both predicted at 100 %, which leaves no order to test, so "
                    "the hypothesis is left undecided. "
                    if h16.get("verdict") == "INCONCLUSIVE" else
                    "The rank order is preserved, which at this n is all that can be "
                    "asked, and it rests on the one prediction below 100 %, a skill of the "
                    "development run: the evaluation runs' two gated skills were both predicted "
                    "at 100 %, which leaves no order to test. ")
                   + "The size of the miss is the "
                   "finding. A judge shown only a skill's description predicts "
                   "it will be reached for far more often than it is. That is the same "
                   "asymmetry §7 measures from the other side: a description that names a "
                   "**side duty** rather than the task at hand sits in context and is not "
                   "chosen.", "",
                   "![trigger](figures/F19-trigger.png)", "")
        else:
            self.missing(h16.get("evidence", "no prediction is available"))
        self.w("**The judge's own gate failed, and then passed.** J0 — the experiment "
               "Cortex's author put in front of the whole Jev integration — measured "
               "89.4 % agreement against a bar of 90 %, with separation preserved and "
               "calibration monotonic: a **FAIL**. The bar was then lowered to 85 % and "
               "the judge shipped. The measurement did not change; `jev/validate.py` keeps "
               "the bar as a constant, `PASS_AGREEMENT`, with a note on its history. No "
               "hypothesis in H0–H14 depends on J0, and every primary number here ran "
               "with the judge off.", "", "---", "")

    # 14 ------------------------------------------------------------------
    def failures_noise_cost(self):
        d = self.d
        self.w("## 14. Why failures remain, and what this costs", "")
        rows = d.bench(runs=d.evaluation or d.development, split="holdout")
        fails = [r for r in rows if not r["pass"]]
        if fails:
            self.w("| Arm | verdict | count |", "|---|---|---|")
            from collections import Counter
            c = Counter((r["arm"], r.get("verdict")) for r in fails)
            for (arm, v), n in c.most_common(12):
                self.w(f"| {arm} | {v} | {n} |")
            self.w("", "`tampered` is the row to watch: it means the rollout changed the "
                       "test QA committed rather than the code. It is the failure mode a "
                       "harness is most likely to move, because an agent that knows the "
                       "house rule has less reason to bend the test.", "")
        self.w("![failures](figures/F12-failures.png)", "",
               "![noise](figures/F13-noise.png)", "",
               "![cost](figures/F14-cost.png)", "")
        rc = [r.get("read_contributing") for r in rows
              if r.get("arm") == "none" and r.get("read_contributing") is not None]
        if rc:
            self.w(f"**One measured premise.** The lab assumes the agent does not go and "
                   f"read the file that documents the house rules. Without a harness, across "
                   f"{len(rc):,} holdout rollouts, it opened `CONTRIBUTING.md` in "
                   f"**{sum(rc) / len(rc):.1%}** of them. The rules are discoverable; "
                   f"they are simply not discovered.", "")
        self.w("Cost per phase and per run: [`T14`](tables/T14-cost.md). Invalid "
               "rollouts, excluded and counted by reason: "
               "[`T13`](tables/T13-invalid.md).", "", "---", "")

    # 15 ------------------------------------------------------------------
    def threats(self):
        d = self.d
        self.w("## 15. Threats to validity", "",
               "| Threat | What it could do | What is done about it |",
               "|---|---|---|")
        ext = "answered in part by §13" if d.external else "**not yet answered**"
        mod = "answered in part by §12" if d.of_kind("model-change") else "**not yet answered**"
        self.w(
            f"| **One synthetic repository**, built by us | the house rules, the tasks "
            f"and the checks all come from the same hand, and the lab was calibrated so that "
            f"the model breaks the rules (scenarios it already passed were redesigned before "
            f"the first session) | a second, real repository with tasks mined from its own "
            f"history ({ext}) |",
            f"| **One model** | every number is conditional on `claude-haiku-4-5` | the "
            f"model-change study ({mod}) |",
            "| **Lintable rules only** | a machine can tell whether these four rules "
            "were followed. Rules needing judgement are not tested at all | stated, not "
            "mitigated. It is the clearest limit on the whole claim |",
            "| **Scripted corrections** | the lab's user plays a part faithfully but "
            "never gets confused or changes their mind | the second repository uses its "
            "own CI output verbatim instead |",
            "| **The holdout was written after D0's items were known** | a scenario "
            "could unconsciously favour what D0 learned | the fifteen new scenarios were "
            "derived only from `CONTRIBUTING.md` and the family definition, and each "
            "touches code no training fix touches. The discipline is the mitigation, not "
            "a proof |",
            "| **Cortex was changed while D0 ran** | the system under test moved while it "
            "was measured | "
            "D0 is reported separately and never pooled; every replicate ran on a frozen "
            "tag, asserted on three resolution paths |",
            self.batch_row(),
            self.git_row(),
            self.records_row(),
            "| **Multiple comparisons** | four families, many arms | Holm across the four "
            "rule families; the primaries are two |",
            "| **A judge in the proposal layer** | a model influences what gets proposed | "
            "every primary ran with it off (`T19` proves which); the gates contain no "
            "model and a test asserts so; H15 and H16 score the judge rather than assume it. "
            "**Its own gate J0 failed at 90 % and passed only after the bar was lowered "
            "to 85 %** |",
            self.foreign_row(),
            "")
        self.w("A reviewer who finds the judge unprompted will discount the whole "
               "paper. One who reads about it here, with its failed gate stated in the "
               "same breath, can weigh it.", "", "---", "")

    def batch_row(self):
        d = self.d
        ev = d.evaluation or d.development
        aa = S.cells(d.bench(runs=ev, arms=("none", "none2"), split="holdout"), "none", "none2",
                     families=list(RULE_FAMILIES), split="holdout")
        if not aa:
            return "| **Batches** | — | the A/A arm has not run |"
        return (f"| **Batches** | the primary arms ran interleaved; every other arm ran later, "
                f"in batches of its own (R1's ablations and `none2` together, `accept-all` on R2 "
                f"apart), and across R1's the A/A pair (the same harness twice) differed by "
                f"{pp(S.paired_mean(aa))} points on the rule families | a comparison with an "
                f"ablation arm may carry that shift; it is reported beside those comparisons, "
                f"and every ablation interval resamples scenarios only |")

    def git_row(self):
        d = self.d
        if not d.transcripts:
            return ("| **What a rollout could read through git** | the fixes and the tracked "
                    "harness are reachable from a sandbox's history and index | not measured |")
        ev = d.evaluation
        lf, ln = self.reads(ev, "sweep", flags=("fix", "store"))
        nt, nn = self.reads(ev, "bench", arms=("none",), split="holdout")
        st, sn = self.reads("M1", "bench", arms=("none",))
        rt, rn = self.reads("M1", "sweep", arms=("cand",))
        xi, xn = self.reads("X1", "bench", flags=("impl",))
        nm, _ = self.reads(ev, "bench", arms=("none",), split="holdout", flags=("names",))
        sm, _ = self.reads("M1", "bench", arms=("none",), flags=("names",))
        dt, dn = self.reads("R1", "bench", arms=("desc-only",))
        ph, pn = self.reads("PRUNE", "sweep", arms=("cand",))
        cov = d.transcript_cover.get("rollouts", {})
        matched = sum(v["matched"] for v in cov.values())
        return (f"| **What a rollout could read through git** | each sandbox is a clone: a "
                f"harvested task's later fix commit and the task store (every `fix.patch`, the "
                f"lessons) are in its history, and a harness item that an arm lacks is still "
                f"tracked, so `git status` lists it and `git diff` prints it; on structlog, "
                f"HEAD was the fix itself | measured, from Claude Code's own record of each of "
                f"{matched:,} rollouts (`data/transcripts.jsonl`): under Haiku, {lf} of {ln:,} loop "
                f"rollouts read a harvested fix (one screen's base arm; the rule was kept); git "
                f"named the run's items to the held-out `none` arm in {nm} of {nn} rollouts and "
                f"printed their text in {nt}; `desc-only` printed the skill body it had replaced "
                f"in {dt} of {dn}; the removal arm of `/prune` printed the removed item in {ph} "
                f"of {pn}. Under Sonnet, git named the items to the `none` arm in {sm} of {sn} "
                f"rollouts and it read their text in {st}, and the removal arm read the removed "
                f"item in {rt} of {rn}; the rollouts that read the text passed as often (`none`) "
                f"or less often (removal) than the others. On structlog, {xi} of {xn} benchmark "
                f"rollouts printed the implementation. A "
                f"sandbox holding one commit, the broken state without the task store, with the "
                f"harness untracked, would close both routes |")

    def records_row(self):
        d = self.d
        uns = [(run, name) for (run, name) in d.scored() if d.rule_fate(run, name) == "unscored"
               and any(i["run"] == run and i["name"] == name and i["fate"] == "buried" for i in d.items)]
        gone = (d.transcript_cover or {}).get("deleted") or []
        g = (f"; the `/prune` agent stopped one of its sweeps before its last rollout was "
             f"recorded, deleted its record and ran it again: Claude Code's records hold all "
             f"{gone[0]['rollouts']} of its rollouts, which count in no result, and their "
             f"${gone[0]['cost_usd']:.2f} is in the spend" if gone else "")
        nj = [name for (run, name) in uns if not any(c["run"] == run and c.get("name") == name
                                                    for c in d.cycles)]
        return (f"| **The loop's own records** | the model that runs `/evolve` and `/prune` writes "
                f"the journal and manages the sweeps: it buried {len(uns)} candidates that "
                f"score.sh had left undecided (RERUN), for one writing into the journal a "
                f"regression its sweep does not contain"
                + (f" and for {'another' if len(nj) == 1 else len(nj)} writing no journal entry at all" if nj else "")
                + f"{g} | every verdict of the evaluation runs' loop in this report is score.sh's "
                f"rules applied again to the recorded rollouts (`analysis/rescore.py`; T5, T6, "
                f"T18), with the journal's record beside it where they differ; the development "
                f"run, whose sweeps ran on a Cortex still being changed, keeps its journal's |")


    def foreign_row(self):
        fs = self.d.foreign_skills()
        (kn, nn), (ke, ne) = fs["by_arm"]["none"], fs["by_arm"]["evolved"]
        if not nn or not ne:
            return ("| **The CLI's own skills** | the agent can reach for skills no harness "
                    "contains | not yet measured: no primary-arm benchmark rows |")
        top = ", ".join(f"`{n}` ({k})" for n, k in list(fs["names"].items())[:4])
        own = "".join(f"; once the agent also invoked Cortex's own `/{n}` command, which "
                      f"`cortex init` installs" for n, k in fs.get("own", {}).items())
        return (f"| **The CLI's own skills** | in {kn}/{nn} `none` rollouts "
                f"({kn / nn:.1%}) and {ke}/{ne} `evolved` ones ({ke / ne:.1%}) the agent "
                f"invoked a skill no harness in the programme contains — {top}{own} | they ship "
                f"inside the pinned Claude Code binary, so they are part of the environment "
                f"under test and available to every arm alike; the rates are computed from "
                f"every valid primary-arm rollout and are close. The programme changed no setting "
                f"or skill in `~/.claude` (Claude Code itself keeps a record of each session "
                f"there) |")

    # 16 ------------------------------------------------------------------
    def reproduce(self):
        self.w("## 16. How to reproduce", "",
               "Everything here rebuilds from the shipped rows with one command and no "
               "network: see [`REPRODUCE.md`](REPRODUCE.md).", "",
               "```bash", "lab/reports/analysis/run.sh", "```", "",
               "The development run is evidence, and the claim that it is untouched is "
               "checkable: `lab/bin/verify-d0`.", "")


def summary(r):
    """SUMMARY.md — one page, for the people who will not read the report.

    The claim, the headline numbers with their intervals, and the three limits.
    Nothing here is written by hand either: if the report's numbers move, this
    moves with them.
    """
    d, L = r.d, []
    h1, h2 = r.card("H1"), r.card("H2")
    counts = {}
    for c in r.cards.values():
        counts[c.get("verdict", "—")] = counts.get(c.get("verdict", "—"), 0) + 1
    L += ["# Cortex, in one page", "",
          "**The claim.** An agent's context should be measured, not curated. Cortex "
          "watches real sessions, proposes a skill or a rule from what went wrong, runs "
          "the agent with and without it on tasks harvested from those sessions, and "
          "keeps it only if the pass rate moves and nothing else breaks.", ""]
    if h1.get("estimate"):
        L += [f"**The headline.** On holdout tasks never seen during evolution, the "
              f"evolved harness beats no harness by **{h1['estimate']}** "
              f"{h1.get('interval', '')} across the four families that have a house "
              f"rule. The control family, which has none, moves "
              f"{h2.get('estimate', '—').split(';')[0]}.", ""]
    L += ["| | |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    L += ["", "**What it cost.** "
          + (f"${d.spend['total']:,.0f} measured for the programme, within a "
             f"${d.spend.get('cap', 1500):,.0f} cap (the development run before it: "
             f"${sum(x.get('cost_usd', 0) for x in d.runs if x.get('kind') == 'development'):,.0f})"
             if (d.spend or {}).get("total") is not None else
             f"${sum(x.get('cost_usd', 0) for x in d.runs):,.0f}")
          + ".", "",
          "## The three limits", "",
          "1. **One synthetic repository and four lintable rules.** A machine can tell "
          "whether these rules were followed. Rules that need judgement are not tested "
          "here at all, and that is the clearest limit on the whole claim."]
    h13 = r.card("H13") if hasattr(r, "card") else {}
    import re as _re
    m = _re.search(r"gains ([+-][0-9.]+) under Haiku \((\w+)\) and ([+-][0-9.]+) under (\S+)",
                   h13.get("estimate") or "")
    rm = _re.search(r"(\d+) of (\d+) decided item\(s\) removable(?: \(([^)]*)\))?",
                    h13.get("estimate") or "")
    if d.of_kind("model-change") and m:
        # the one-page reader must not leave thinking the gain is model-independent
        L += [f"2. **The gain is a property of a weak model.** Every primary number is "
              f"`claude-haiku-4-5`. Under `{m.group(4)}` the same harness gains "
              f"**{m.group(3)}** points where it gained **{m.group(1)}** under Haiku "
              f"({m.group(2)}'s harness), because the stronger model already follows most "
              f"house rules without a harness"
              + (f"; one `/prune` pass after the upgrade, at k=3, found {rm.group(1)} of its "
                 f"{rm.group(2)} items removable ({rm.group(3)})" if rm and rm.group(3) else "")
              + ". The loop is worth most where the model is weakest."]
    else:
        L += ["2. **One model.** Every number is conditional on `claude-haiku-4-5`."
              + ("" if d.of_kind("model-change") else " The model-change study has not run yet.")]
    L += ["3. **A judge in the proposal layer.** Cortex ships one. Every primary number "
          "here was produced with it off, the gates contain no model and a test asserts "
          "so — and its own validation gate failed at 90 % before being lowered to 85 %."]
    if d.external:
        ident = any(e.get("harness_identical") for e in d.external)
        L += ["", "A second, real repository nobody here built is reported separately in §13, "
              "never pooled." + (" **On it the loop learned nothing**: the agent was rarely "
              "corrected, so no problem recurred and Cortex declined to invent a rule. It "
              "shows when the loop has work to do, and does not test whether what it learns "
              "transfers." if ident else "")]
    L += ["", "Full report: [`REPORT.md`](REPORT.md). Rebuild every number offline with "
          "`lab/reports/analysis/run.sh`."]
    return "\n".join(L) + "\n"


def main():
    r = Report()
    text = r.build()
    (REPORTS / "REPORT.md").write_text(text, encoding="utf-8")
    (REPORTS / "SUMMARY.md").write_text(summary(r), encoding="utf-8")
    print(f"{len(text.splitlines())} lines -> {REPORTS / 'REPORT.md'} (+ SUMMARY.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
