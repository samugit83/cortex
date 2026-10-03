#!/usr/bin/env python3
"""appendix.py — write everything a reader might want to check by hand.

    lab/reports/analysis/run.sh --appendix

The report quotes numbers; the appendix carries the material those numbers were
computed from, so that a disagreement can be settled by reading rather than by
re-running:

  A1  every scenario: the teammate's commit, the user's words, the reference fix,
      and the rule-breaking fix that passes its own test
  A2  every correction the lab's scripted user can send, verbatim
  A3  every item every run produced, kept or buried, in full, with why
  A4  every evolution journal, verbatim
  A5  the hand-written harnesses (`ideal`, `swapped`)
  A6  the 29 gate-calibration candidates
  A7  the four prune plants
  A8  the second repository's mined tasks

Written as files rather than one document because A1 and A3 are long, and a reader
usually wants one of them.
"""
from __future__ import annotations

import json
import shutil
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from load import FAMILIES, Data                      # noqa: E402

REPORTS = HERE.parent
CORTEX = REPORTS.parent.parent
OUT = REPORTS / "appendix"


def scenarios():
    m = types.ModuleType("sc")
    src = (CORTEX / "lab" / "bin" / "scenarios.py").read_text()
    exec(compile(src, "scenarios.py", "exec"), m.__dict__)
    return m


def fence(text, lang=""):
    text = text if isinstance(text, str) else json.dumps(text, indent=1)
    return f"```{lang}\n{text.rstrip()}\n```"


def a1_scenarios(m):
    rounds = {sid: r for r, ids in m.ROUNDS.items() for sid in ids}
    L = ["# A1 · Every scenario", "",
         "56 scenarios: 26 training and 30 holdout, six per family. A scenario is a "
         "teammate's commit (a test, which is the specification), the user's words, a "
         "reference fix that satisfies the house rule, and — for the four families "
         "that have one — a **rule-breaking fix that passes the scenario's own test**. "
         "That last one is what makes the family's check the only thing that can tell "
         "them apart.", ""]
    for fam in "ABCDE":
        L += [f"## Family {fam} — {FAMILIES[fam]}", ""]
        for s in [x for x in m.SCENARIOS if x["family"] == fam]:
            L += [f"### {s['id']} · {s['title']}  ({s['split']}"
                  + (f", round {rounds[s['id']]}" if s["id"] in rounds else "") + ")", "",
                  f"**The teammate's commit** — `{s['message']}` by {s['author']}", "",
                  f"Files: {', '.join(f'`{k}`' for k in s['files'])}", "",
                  "**What the user asks**", "", f"> {s['prompt']}", "",
                  f"**The check**: `python3 -m unittest {s['test']}`", "",
                  "<details><summary>the teammate's test, verbatim</summary>", ""]
            for rel, content in s["files"].items():
                L += [f"`{rel}`", "", fence(content, "python"), ""]
            L += ["</details>", "",
                  "<details><summary>the reference fix</summary>", "",
                  fence(s["solve"], "json"), "", "</details>", ""]
            naive = m.naive_edits(s) if hasattr(m, "naive_edits") else s.get("naive")
            if naive:
                L += ["<details><summary>the rule-breaking fix — passes this test, "
                      "fails the house rule</summary>", "", fence(naive, "json"), "",
                      "</details>", ""]
    return "\n".join(L) + "\n"


def a2_corrections(m):
    L = ["# A2 · Every correction", "",
         "The lab's user is scripted: when `lab verify` returns a verdict, exactly one "
         "of these is sent, with the scenario's own test and files interpolated. It "
         "plays a user faithfully and never gets confused, never changes its mind and "
         "always corrects in the same voice — which is a limitation, stated in the "
         "report's threats section and answered in part by the second repository, "
         "where the corrections are the project's own CI output pasted back verbatim.",
         ""]
    for verdict, text in m.CORRECTIONS.items():
        what = {"tampered": "the rollout changed the test QA committed",
                "test": "the task's own test still fails",
                "suite": "the change broke other tests",
                "A": "the house rule for family A was broken",
                "B": "the house rule for family B was broken",
                "C": "the house rule for family C was broken",
                "E": "the house rule for family E was broken"}.get(verdict, "")
        L += [f"## `{verdict}` — {what}", "", fence(text), ""]
    return "\n".join(L) + "\n"


def a3_items(d):
    L = ["# A3 · Every item, kept and buried", "",
         "In full, with the measurement that decided it. A buried item is as much a "
         "result as a kept one: it is the loop declining to spend your context on "
         "something it could not show a gain for.", ""]
    for run in sorted({i["run"] for i in d.items}):
        L += [f"## {run}", ""]
        for fate in ("kept", "buried"):
            items = [i for i in d.items if i["run"] == run and i["fate"] == fate]
            if not items:
                continue
            L += [f"### {fate} ({len(items)})", ""]
            for it in items:
                paths = ", ".join(f"`{p}`" for p in (it.get("paths") or [])) or "none (always on)"
                L += [f"#### `{it['name']}` — {it['kind']}, paths: {paths}", "",
                      fence(it.get("text", ""), "markdown"), ""]
                if it.get("why"):
                    L += ["**Why it was buried**", "", fence(it["why"]), ""]
    return "\n".join(L) + "\n"


def a4_journals(d):
    L = ["# A4 · The evolution journals", "",
         "One entry per `/evolve` cycle, written by the agent as it went. This is the "
         "permanent record of why each run's `.claude/` looks the way it does.", ""]
    for run in sorted({c["run"] for c in d.cycles}):
        L += [f"## {run}", ""]
        for c in sorted([c for c in d.cycles if c["run"] == run],
                        key=lambda c: c.get("journal_index", 0)):
            tag = "" if c.get("is_cycle") else "  _(not counted as a cycle: an "
            if not c.get("is_cycle"):
                tag += "experimenter's note or a re-test)_"
            L += [fence(c.get("raw", ""), "markdown") + tag, ""]
    return "\n".join(L) + "\n"


def copy_tree(src, dest, title, blurb):
    if not src.is_dir():
        return None
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    files = sorted(p for p in dest.rglob("*") if p.is_file())
    L = [f"# {title}", "", blurb, "", f"{len(files)} file(s), copied verbatim:", ""]
    for f in files:
        L.append(f"- `{f.relative_to(dest)}`")
    (dest / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return len(files)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m, d = scenarios(), Data()
    wrote = []
    for name, text in (("A1-scenarios.md", a1_scenarios(m)),
                       ("A2-corrections.md", a2_corrections(m)),
                       ("A3-items.md", a3_items(d)),
                       ("A4-journals.md", a4_journals(d))):
        (OUT / name).write_text(text, encoding="utf-8")
        wrote.append((name, len(text.splitlines())))
    b = CORTEX / "lab" / "bench"
    copy_tree(b / "harnesses", OUT / "A5-harnesses", "A5 · The hand-written harnesses",
              "`ideal` is what someone who already knew all four house rules AND "
              "Cortex's tier model would have installed on day one. `swapped` is the "
              "same four items with their words unchanged and their form inverted. "
              "Both were committed before the first run.")
    copy_tree(b / "gate-candidates", OUT / "A6-gate-candidates",
              "A6 · The gate-calibration candidates",
              "29 candidates whose right verdict was written down before any of them "
              "ran. The placebo word rule — 300-1500 characters and no mention of "
              "tests, lint, CONTRIBUTING, changelog, docs, money, time or exporters — "
              "is enforced by the generator, which is what makes 'placebo' a claim "
              "rather than a label.")
    copy_tree(b / "prune-plants", OUT / "A7-prune-plants", "A7 · The prune plants",
              "Four items planted in a copy of a finished run, each with its expected "
              "fate fixed in advance. The two that matter are the ones that must NOT "
              "be deleted: a gated skill no task can reach, and an always-on skill "
              "that never fires.")
    ext = CORTEX.parent / "cortex-eval" / "external" / "structlog-tasks.json"
    if ext.is_file():
        doc = json.loads(ext.read_text())
        L = ["# A8 · The second repository's tasks", "",
             f"Mined from `{doc['repo'].split('/')[-1]}`'s own history at base "
             f"`{doc['base'][:10]}`: {doc['mined']} validated, {doc['rejected']} "
             f"rejected. For each, the implementation is reverted at its own commit "
             f"and the tests are kept as the specification.", ""]
        for t in doc["tasks"]:
            L += [f"## {t['id']} · {t['title']}", "",
                  f"- commit `{t['sha'][:10]}`, parent `{t['parent'][:10]}`",
                  f"- implementation reverted: {', '.join(f'`{x}`' for x in t['src'])}",
                  f"- the check: `{t['check']}`",
                  f"- broken state: `{(t.get('broken_tail') or [''])[0]}`",
                  f"- rest of the suite on the broken state: "
                  f"`{(t.get('rest_tail') or [''])[0]}`", "",
                  "**What the user asks**", "", f"> {t['prompt']}", ""]
        (OUT / "A8-external-tasks.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        wrote.append(("A8-external-tasks.md", len(L)))
    for name, n in wrote:
        print(f"  {name:24} {n:5} lines")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
