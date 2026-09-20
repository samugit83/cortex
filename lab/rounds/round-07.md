# Round 7 — A05, B05, E04

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

### A05 — list --limit (family A: user-visible change)

> Support wants `shop list --limit N` to show only the first N products. QA added tests/test_list_limit.py. Can you add the option?

### B05 — exact prorated refunds (family B: money)

> A customer who cancelled after 10 of 30 days paid €9.99 and got €6.69 back instead of €6.66: prorated_refund() rounds the daily rate first. QA added tests/test_refund_proration.py. Can you fix it?

### E04 — new arrivals (family E: time)

> The homepage needs a 'new arrivals' strip. Please add new_arrivals(products, days=30, today=None) to shop/catalog.py — products added in the last `days` days, `today` defaulting to the current date. Tests: tests/test_new_arrivals.py.

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

**What should happen this round:** same → BARREN (after three quiet rounds in a row Cortex says STOP: the loop has converged).

If `/evolve` asks you a question, or something looks wrong, don't fix it by hand: tell me.

**Then tell me "round 7 done".** Don't start round 8 before I have checked.
