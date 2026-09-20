# Round 2 — A01, A02, A03

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

### A01 — list cheapest first by default (family A: user-visible change)

> Product decided that `shop list` should show the cheapest products first by default (`--sort name` keeps the old order). QA already added tests/test_list_default_sort.py, which fails for now. Can you make the change?

### A02 — thousands separator in prices (family A: user-visible change)

> Prices over a thousand are hard to read: the standing desk shows as €1249.00. Product wants a thousands separator (€1,249.00) everywhere. QA added tests/test_money_display.py. Please implement it.

### A03 — report total row (family A: user-visible change)

> Finance wants a TOTAL row at the bottom of `shop report`: total items and total amount. QA added tests/test_report_total.py. Can you add it?

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

**What should happen this round:** the changelog theme reaches three lessons in one round → the first skill: probably an **always-on** skill ("before reporting done, add a CHANGELOG line"), screened on this round's three tasks, then confirmed on all.

If `/evolve` asks you a question, or something looks wrong, don't fix it by hand: tell me.

**Then tell me "round 2 done".** Don't start round 3 before I have checked.
