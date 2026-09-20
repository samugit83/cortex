# Round 5 — D01, D02, D03

3 sessions, then `/evolve`. Do them in order; `lab next` always picks the right one.

## Each session

1. In a terminal: `lab next`. A teammate's commit lands in cortex-lab, and the prompt is printed.
2. Open a **new** Claude Code chat in cortex-lab and check the model is **Haiku 4.5**.
   Paste the prompt exactly as printed. Let Claude work, and approve what it asks.
3. When Claude says it is done: `lab verify`.
   - `✘ …` + a reply → paste the reply into the **same** chat, let Claude fix, run `lab verify` again.
   - `✔ …` → go on.
4. Type `/harvest` in the **same** chat. Wait for its one-line report.
5. `lab done`: it records the session and commits everything.

Claude asks nothing: your global default is bypassPermissions. If it stalls or loops, stop it and tell me.

## This round's sessions

Here for reference: `lab next` prints the same text.

### D01 — slugify with accents (family D: control)

> Product URLs are broken for names with accents: slugify('Café chair') gives 'caf-chair'. QA added tests/test_slugify_accents.py. Can you fix it?

### D02 — truncate respects the width (family D: control)

> truncate() returns one character more than the width it's given, so labels overflow. QA added tests/test_truncate_width.py. Please fix it.

### D03 — pluralize zero (family D: control)

> An empty cart says '0 item'. pluralize() should use the plural for zero. QA added tests/test_pluralize_zero.py — please fix it.

## Then `/evolve`

1. Open a **new** chat (Haiku 4.5) and type `/evolve`.
2. It runs preflight, reads the lessons and either stops (**BARREN**: nothing recurs yet) or
   writes one candidate and launches a **screen** sweep in the background, then says it will be back.
3. Wait for the sweep. In a terminal inside cortex-lab, `cortex score | jq -c '{phase,rollouts,finished}'` shows progress.
   A screen is ~8–16 rollouts (10–20 min); a confirm is tasks × 6 rollouts.
4. When `finished` is `true`, type `/evolve` again (same chat or a new one). It reads the result and
   either stops (KILL) or launches the next sweep: the **confirm**, or a small **recheck**.
5. Repeat 3–4 until it reports **KEEP**, **KILL** or **BARREN** and writes the journal.
6. In a terminal: `lab commit` (commits the new skill or rule, the journal and the baseline).

**What should happen this round:** control tasks (plain bugs): no corrections, no lessons → **BARREN**; they join the suite as tasks every future change must not break.

If `/evolve` asks you a question, or something looks wrong, don't fix it by hand: tell me.

**Then tell me "round 5 done".** Don't start round 6 before I have checked.
