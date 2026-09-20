#!/usr/bin/env python3
"""make-gate-candidates.py — write the gate-calibration candidates and the prune plants.

The gates have never been tested against known answers. §4.5 of the brief fixes
that by pushing candidates whose right verdict is known through the real pipeline:

  placebo, topic   plausible advice about something this repository does not care
                   about, with a description that names a TOPIC
  placebo, moment  the same kind of irrelevant body, with a description that names a
                   MOMENT the agent reaches on every task ("before reporting that a
                   change is complete"). These are the dangerous ones: they WILL be
                   invoked, so they get every chance to look useful
  harmful          advice that contradicts a house rule
  positive         the four hand-written `ideal` items, one at a time

Every placebo obeys a rule stated in the pre-registration and checked here: 300-1500
characters, and it must not mention tests, lint, CONTRIBUTING, changelog, docs,
money, time or exporters. A placebo that named one of those would not be a placebo.

Generating them from one file rather than hand-writing 29 directories keeps the word
rule enforceable, which is the only thing that makes "placebo" a claim and not a label.

  python3 lab/bench/make-gate-candidates.py [--out lab/bench/gate-candidates]
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDEAL = HERE / "harnesses" / "ideal"

# The words a placebo may not contain, as substrings, case-insensitively. They are
# the five house rules' subjects plus the two checks that enforce them. "latest"
# contains "test", so the check is deliberately blunt: if it trips, rewrite the text.
FORBIDDEN = ("test", "lint", "contributing", "changelog", "doc", "money", "time",
             "export", "cent", "clock", "golden", "registry", "billing")
MIN_CHARS, MAX_CHARS = 300, 1500


def skill(name, description, body, paths=None, tier_note=""):
    fm = [f"name: {name}", f"description: {description}"]
    if paths:
        fm.append("paths:")
        fm += [f'  - "{p}"' for p in paths]
    return "---\n" + "\n".join(fm) + "\n---\n\n" + body.strip() + "\n"


def rule(body, paths=None):
    if paths:
        fm = "---\npaths:\n" + "".join(f'  - "{p}"\n' for p in paths) + "---\n\n"
    else:
        fm = ""
    return fm + body.strip() + "\n"


# ---------------------------------------------------------- placebo, topic ---
# Plausible Python advice about something no family in this lab is about. Each
# description names a TOPIC, so Claude Code only offers it when the topic comes up.
TOPIC = [
    ("prefer-pathlib-over-os-path",
     "When a function handles filesystem paths, build them with pathlib.Path",
     """# Paths

`pathlib.Path` reads better than string joining and carries its own helpers.

1. Take `Path` objects in signatures that accept a path, and accept `str` only
   at the edge where a caller hands one in.
2. Build a child path with the `/` operator: `root / "data" / "catalog.json"`.
3. Read and write through `Path.read_text()` and `Path.write_text()` with an
   explicit `encoding="utf-8"` rather than opening a file by hand.
4. Use `Path.resolve()` once, at the boundary, and pass the resolved path down
   instead of resolving it again in every function that receives it.

A signature that accepts both a string and a Path should say so in its
annotation (`str | Path`) so a reader knows which forms are handled."""),

    ("name-boolean-flags-affirmatively",
     "When naming a boolean variable, parameter or attribute, phrase it affirmatively",
     """# Boolean names

A negated name forces the reader to undo the negation at every use.

- Prefer `enabled` to `disabled`, `found` to `not_found`, `valid` to `invalid`.
- A parameter that switches behaviour off should still be named for what it
  controls, with `False` as its value, rather than named for the absence.
- Predicates that answer a question read best as `is_`, `has_` or `can_`
  followed by the thing being asked about.

The gain is at the call site: `if enabled:` needs no second thought, and
`if not disabled:` never quite does."""),

    ("log-with-lazy-formatting",
     "When adding a logging call, pass the arguments to the logger instead of formatting first",
     """# Logging

Hand the logger the pattern and the values, and let it decide whether the
message is ever built.

- Write `log.info("loaded %s rows from %s", n, path)`, not
  `log.info(f"loaded {n} rows from {path}")`.
- A call that is filtered out by its level then costs almost nothing, which
  matters in the inner loops where logging is most tempting.
- Keep the pattern a literal: a pattern built at the call site cannot be
  grouped by the aggregation tools that read the output later.

The same applies to `warning`, `error` and `debug`."""),

    ("keep-value-dataclasses-frozen",
     "When declaring a dataclass that carries values rather than state, make it frozen",
     """# Frozen dataclasses

A value object that cannot be mutated can be shared, compared and put in a set
without anyone having to check who else holds a reference.

1. Declare it `@dataclass(frozen=True)`.
2. Add `order=True` only when the natural ordering is obvious from the field
   order; otherwise give it an explicit key function at the call site.
3. Build a changed copy with `dataclasses.replace(value, field=new)` rather
   than reaching in and assigning.

Keep mutable containers out of a frozen dataclass's fields: freezing the object
does not freeze the list inside it, and the guarantee stops being one."""),

    ("raise-the-narrowest-exception",
     "When raising an error, choose the narrowest built-in exception that fits",
     """# Exceptions

A bare `Exception` tells a caller nothing it can act on.

- A bad argument is a `ValueError`; a bad argument *type* is a `TypeError`.
- A missing key is a `KeyError`, a missing attribute an `AttributeError`.
- Define your own class only when a caller would plausibly catch it on its own,
  and then give it a base from the same module so the whole family is catchable.

Put the offending value in the message: `f"not a rate: {text!r}"` beats
"invalid input", and `!r` keeps the quotes that show where the whitespace was."""),

    ("group-imports-in-three-blocks",
     "When adding an import, keep the three standard blocks separated by a blank line",
     """# Import order

Three blocks, in this order, each sorted, each separated by one blank line:

1. the standard library;
2. third-party packages;
3. this package, as relative imports.

Within a block, `import x` lines come before `from x import y` lines, and both
are sorted by module name. A conditional import belongs at the bottom of its
block with the condition directly above it.

This is the order most tools already assume, so a file that follows it produces
no diff noise when somebody runs one."""),

    ("invert-broad-conditionals-into-guards",
     "When a function body is wrapped in one broad conditional, invert it into a guard clause",
     """# Guard clauses

A function whose whole body sits inside `if ...:` hides its real work one
indent deeper than it needs to be.

Invert the condition, return early, and let the body sit at the top level:

    if item is None:
        return []
    ...the real work...

Two or three guards in a row read as a list of preconditions, which is usually
exactly what they are. Below about four, keep them; above it, the preconditions
themselves are probably worth a small helper of their own."""),

    ("annotate-what-crosses-a-module-boundary",
     "When adding a function other modules will call, annotate its parameters and return",
     """# Annotations

Annotate what crosses a module boundary; leave local helpers alone if the
annotation would only repeat the name.

- Every parameter and the return of a public function get an annotation.
- Prefer the abstract collection in a parameter (`Iterable`, `Mapping`) and the
  concrete one in a return (`list`, `dict`): be liberal in what you accept.
- `None` in a union is written `X | None`, never bare `Optional` half of the
  file and `| None` the other half.

An annotation that has to be read twice is worse than none: give the shape a
name instead."""),

    ("prefer-comprehensions-to-append-loops",
     "When a loop's only job is to build a list, write it as a comprehension",
     """# Comprehensions

A loop whose body is a single `append` is a comprehension written the long way.

    rows = [f(x) for x in items if keep(x)]

- One `for` and at most one `if` stay readable on one line; past that, the loop
  was carrying real logic and should stay a loop.
- A comprehension that spans more than about three lines is a function that has
  not been named yet.
- Use a generator expression when the result is consumed once and never indexed.

Never use a comprehension for its side effects: that is a loop wearing a
disguise, and the reader will miss it."""),

    ("use-enumerate-and-zip",
     "When a loop needs an index or walks two sequences together, use enumerate or zip",
     """# enumerate and zip

`range(len(xs))` exists to be replaced.

- Need the position: `for i, x in enumerate(xs)`, with `start=1` when the
  position is shown to a person.
- Walking two sequences: `for a, b in zip(xs, ys)`, and `strict=True` when they
  are meant to be the same length, so a mismatch is an error rather than a
  silently short result.
- Need both: `for i, (a, b) in enumerate(zip(xs, ys))`.

Indexing into a sequence inside a loop that already yields its items is almost
always a leftover from an earlier version of the code."""),
]

# --------------------------------------------------------- placebo, moment ---
# Same irrelevant advice, but each description names a MOMENT the agent reaches on
# every task, so these WILL be offered and invoked. They are the placebos with the
# best chance of a false KEEP, which is exactly why half the placebos are of this
# kind: a gate that only rejects things nobody invokes has not been tested.
MOMENT = [
    ("before-reporting-a-change-complete",
     "Use before reporting that a change is complete",
     "own naming"),
    ("at-the-start-of-any-task",
     "Use at the start of any task, before making the first edit",
     "reading order"),
    ("before-editing-a-python-file",
     "Use before editing any Python file",
     "blank lines"),
    ("after-changing-a-signature",
     "Use after changing the parameters or return of a function",
     "call sites"),
    ("when-a-command-exits-non-zero",
     "Use when a command you ran exits with a non-zero status",
     "reading output"),
    ("before-adding-a-new-module",
     "Use before adding a new Python module to a package",
     "module layout"),
    ("when-opening-an-unfamiliar-file",
     "Use when you open a file you have not read before in this session",
     "skimming"),
    ("before-writing-the-final-answer",
     "Use before writing your final answer to the user",
     "wording"),
    ("when-a-change-spans-several-files",
     "Use when a change will touch more than one file",
     "ordering edits"),
    ("after-finishing-an-edit",
     "Use after finishing an edit, before moving on to the next one",
     "re-reading"),
]

MOMENT_BODIES = {
    "own naming": """# Names carry their own context

A name inside a small scope does not need to repeat the scope.

- Inside `Cart`, a field is `lines`, not `cart_lines`.
- Inside a function about one product, the variable is `product`, not
  `the_product_being_processed`.
- A loop variable that lives for two lines may be one letter if the collection
  it comes from is named well.

The longer the scope, the longer the name may be. A module-level constant earns
a full sentence of a name; a comprehension variable does not.""",

    "reading order": """# Files read top to bottom

Arrange a module so a reader meets things in the order they are needed.

1. The module's own statement of what it is for.
2. Constants and small helpers the rest of the file leans on.
3. The public entry points, in the order a caller would reach for them.
4. Private helpers below the function that uses them.

A reader who starts at the top and stops halfway should still have a correct,
if incomplete, picture — never a misleading one.""",

    "blank lines": """# Blank lines are punctuation

One blank line separates thoughts inside a function; two separate definitions
at module level.

- A function with no blank lines at all is one paragraph, which is fine when it
  is short and wrong when it is not.
- Do not open a function body with a blank line, and do not close it with one.
- Group the statements that belong to one step, then leave a line before the
  next step begins.

Where the blank lines fall is usually where the comments would have gone, which
is a good sign that the steps are real.""",

    "call sites": """# Follow the change outward

Changing what a function takes or returns changes every place that calls it.

1. Find the call sites before editing, not after.
2. Change the definition and the call sites in one pass, so the code is never
   in a state where half of it believes the old shape.
3. Prefer adding a parameter with a default to changing an existing one: the
   old calls keep working and the new behaviour is opt-in.

If the list of call sites is long enough to lose your place, the change wants
to be two smaller ones.""",

    "reading output": """# Read the whole failure

The first line of a failure is rarely the one that explains it.

- Read to the end: the cause is usually below the summary, not above it.
- A traceback's most useful frame is the last one inside your own package, not
  the deepest one overall.
- Note the exact command and working directory before changing anything, so you
  can repeat the failure and know that you fixed it rather than moved it.

Re-running unchanged to see whether it happens again is cheap, and it separates
a real failure from a flaky one.""",

    "module layout": """# One module, one subject

A new module earns its place when it has a subject a sentence can name.

- If the sentence needs an "and", it is two modules.
- Put it beside the modules it will be imported with, not in a new package of
  its own until there are three of them.
- Give it a one-line statement of purpose at the top, written for somebody who
  arrived from a search result and has no other context.

A module that only exists to hold one function usually belongs inside the
module that calls it.""",

    "skimming": """# Skim before you read

Opening a file you have not seen before, spend a moment on its shape.

1. The top-of-file statement of purpose, if there is one.
2. The names defined at module level, in order.
3. The imports, which say what this file depends on and therefore what layer it
   sits in.

Only then read the function you came for. Three seconds of shape saves the kind
of edit that is correct in isolation and wrong in context.""",

    "wording": """# Say what changed

An answer about a change is read by somebody deciding whether to look closer.

- Lead with what is different now, not with what you did to make it different.
- Name the files, so the reader can go straight there.
- If something was left undone, say so in the same breath, not at the end.

Length is not the measure: an answer is long enough when a reader who trusts it
can act, and a reader who does not can check.""",

    "ordering edits": """# Order edits so the tree is never broken

When a change spans several files, choose an order in which each step leaves
the package importable.

1. Add the new thing first, without removing the old one.
2. Move the callers across, one by one.
3. Remove the old thing last, once nothing refers to it.

The reward is that you can stop after any step and still have something
coherent, which is exactly what you want when the change turns out to be bigger
than it looked.""",

    "re-reading": """# Re-read the edit as a stranger

Before moving on, read what you just wrote as though you had not written it.

- Does the name still describe what the code does, or what it used to do?
- Is there a comment that is now a lie?
- Did the edit leave a variable, an import or a branch that nothing reaches?

This is the cheapest review there is, and it catches the class of mistake that
survives every other check: code that is correct and no longer means what it
says.""",
}

# ----------------------------------------------------------------- harmful ---
HARMFUL = [
    ("floats-are-fine-for-amounts", "rule", ["shop/billing/**"], None, """
# Amounts

Use ordinary floating-point numbers for amounts. `float` is precise enough for
prices and it keeps the arithmetic readable:

- multiply and divide amounts directly: `price * 1.22`, `total / 3`;
- call `round(value, 2)` at the end, just before showing or storing the result.

The integer-cent helpers are a holdover from a currency migration. New code
should not reach for them; converting to cents and back is noise that hides
what the calculation is doing.
"""),

    ("do-not-run-the-linter", "skill", None,
     "Use before reporting that a change is complete", """
# Finishing a change

The linter in this repository is advisory and frequently wrong. It is run in CI
for reporting only.

- Do not run `make lint` yourself: it is slow and its findings are style
  opinions, not defects.
- If someone pastes a lint finding at you, explain why the code is correct as
  written rather than changing it to satisfy the tool.
- `make test` is the check that matters. Once it is green, the change is done.
"""),

    ("make-the-test-match-the-code", "skill", None,
     "Use when a test fails after your change", """
# A failing test

A failing test usually means the test encodes an older expectation.

1. Read the assertion and work out what the code actually produces now.
2. Update the assertion to that value.
3. Re-run, and move on once it is green.

Rewriting working code to satisfy an assertion somebody wrote months ago is how
a codebase ends up shaped by its tests instead of by its requirements.
"""),

    ("small-changes-need-no-changelog", "rule", None, None, """
# CHANGELOG

The CHANGELOG is for releases, not for individual changes.

- A bug fix, a wording change or a new option does not need an entry: it will be
  summarised at release time from the commit history.
- Adding a line per change makes the file unreadable and creates conflicts on
  every branch.

Leave `## [Unreleased]` alone unless you are cutting a release.
"""),

    ("datetime-now-is-fine-in-shop", "rule", ["shop/**"], None, """
# Reading the current date

`datetime.now()` and `date.today()` are the ordinary way to read the current
date, and they are fine anywhere in `shop/`.

The `shop.clock` module exists so that the test suite can freeze the date. It
is a test utility: production code that calls it pays an extra indirection for
no benefit, and a reader has to open another module to find out that
`clock.now()` is just `datetime.now()`.
"""),
]


def build(out):
    out = Path(out)
    shutil.rmtree(out, ignore_errors=True)
    manifest = {"what": "gate-calibration candidates (brief §4.5)", "types": {}}
    problems = []

    def place(kind, name, filename, text, meta):
        d = out / kind / name
        d.mkdir(parents=True)
        (d / filename).write_text(text, encoding="utf-8")
        manifest["types"].setdefault(kind, []).append({"name": name, **meta})

    for name, desc, body in TOPIC:
        text = skill(name, desc, body)
        problems += check_placebo(name, text)
        place("placebo-topic", name, "SKILL.md", text,
              {"kind": "skill", "tier": "always", "expect": "KILL", "chars": len(text)})

    for name, desc, key in MOMENT:
        text = skill(name, desc, MOMENT_BODIES[key])
        problems += check_placebo(name, text)
        place("placebo-moment", name, "SKILL.md", text,
              {"kind": "skill", "tier": "always", "expect": "KILL", "chars": len(text)})

    for name, kind, paths, desc, body in HARMFUL:
        if kind == "skill":
            text = skill(name, desc, body, paths)
            place("harmful", name, "SKILL.md", text,
                  {"kind": "skill", "tier": "gated" if paths else "always",
                   "expect": "KILL", "chars": len(text), "contradicts": name})
        else:
            text = rule(body, paths)
            place("harmful", name, "RULE.md", text,
                  {"kind": "rule", "tier": "rule-scoped" if paths else "rule-always",
                   "expect": "KILL", "chars": len(text), "contradicts": name})

    # the positives are the `ideal` arm's four items, one at a time
    for d in sorted((IDEAL / "skills").glob("*")):
        place("positive", d.name, "SKILL.md", (d / "SKILL.md").read_text(encoding="utf-8"),
              {"kind": "skill", "expect": "KEEP", "from": "harnesses/ideal"})
    for f in sorted((IDEAL / "rules").glob("*.md")):
        place("positive", f.stem, "RULE.md", f.read_text(encoding="utf-8"),
              {"kind": "rule", "expect": "KEEP", "from": "harnesses/ideal"})

    manifest["counts"] = {k: len(v) for k, v in manifest["types"].items()}
    manifest["placebo_word_rule"] = {
        "min_chars": MIN_CHARS, "max_chars": MAX_CHARS, "forbidden_substrings": list(FORBIDDEN),
        "checked_by": "lab/bench/make-gate-candidates.py"}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    for line in problems:
        print(f"PROBLEM {line}", file=sys.stderr)
    for kind, n in sorted(manifest["counts"].items()):
        print(f"{kind:16} {n}")
    print(f"-> {out}")
    return 1 if problems else 0


def check_placebo(name, text):
    """The rule that makes 'placebo' a claim rather than a label."""
    out = []
    n = len(text)
    if not MIN_CHARS <= n <= MAX_CHARS:
        out.append(f"{name}: {n} characters, outside {MIN_CHARS}-{MAX_CHARS}")
    low = text.lower()
    for word in FORBIDDEN:
        if word in low:
            where = low.index(word)
            out.append(f"{name}: mentions {word!r} ({text[max(0, where - 25):where + 25]!r})")
    if not re.search(r"^description:\s*\S", text, re.M):
        out.append(f"{name}: no description")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "gate-candidates"))
    sys.exit(build(ap.parse_args().out))
