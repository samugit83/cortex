# Round 4 — E01, E02, E03

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

### E01 — invoice due date (family E: time)

> Invoices need a due date. Please add due_date(issued=None, days=30) to shop/billing/invoice.py: 30 days after the issue date, and when no issue date is given, 30 days from today. The tests are in tests/test_due_date.py.

### E02 — cart reservation expiry (family E: time)

> Checkout should hold items for 15 minutes. Please add Cart.reserve(minutes=15), which sets cart.expires_at (UTC), and Cart.is_expired(at=None), which defaults to now. The tests are in tests/test_cart_reservation.py.

### E03 — archive old orders (family E: time)

> Ops wants to archive old orders. Please add archive_old_orders(orders, days=90, today=None) to shop/orders.py, returning (recent, archived); `today` defaults to the current date. Tests: tests/test_order_archive.py.

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

**What should happen this round:** the time theme: three lessons if the sessions need correcting → an always-on skill or a `CLAUDE.md` line; fewer if Haiku copies `clock` from E01's fix → BARREN.

If `/evolve` asks you a question, or something looks wrong, don't fix it by hand: tell me.

**Then tell me "round 4 done".** Don't start round 5 before I have checked.
