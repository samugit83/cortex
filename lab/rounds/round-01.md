# Round 1 — B01, B02, B03

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

### B01 — fractional tax rates (family B: money)

> CI has been red since QA added tests/test_tax_rates.py: tax_for() gives the wrong tax for fractional rates like 8.25%, and it doesn't round the way the tests expect. Can you fix it?

### B02 — fractional discounts (family B: money)

> The 12.5% spring promo is charging customers the wrong amount — apply_discount() ignores the decimals. QA added tests/test_discount_rates.py and it fails. Please fix it.

### B03 — four-decimal exchange rates (family B: money)

> Our USD and GBP price lists are wrong: convert() ignores the decimals of the exchange rate, so 1.0842 is used as 1. Finance publishes 4 decimals. QA added tests/test_fx_rates.py — can you fix convert()?

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

**What should happen this round:** the money theme has only 1–2 lessons (B02 learned the rule from B01's fix in the code) → most likely **BARREN**, which is correct: nothing recurs yet.

If `/evolve` asks you a question, or something looks wrong, don't fix it by hand: tell me.

**Then tell me "round 1 done".** Don't start round 2 before I have checked.
