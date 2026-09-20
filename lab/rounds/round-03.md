# Round 3 — C01, C02, C03

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

### C01 — XML export (family C: new exporter)

> Our accountant's software imports XML. Please add an XML export format: `shop export orders.json --format xml`. The tests are already in tests/test_export_xml.py — they fail for now.

### C02 — Markdown export (family C: new exporter)

> We paste order summaries into our wiki. Can you add a `markdown` export format (a table, one row per order line)? The tests are in tests/test_export_markdown.py.

### C03 — TSV export (family C: new exporter)

> Excel users keep breaking our CSV on commas in customer names. Please add a `tsv` export format (tab separated). Tests are in tests/test_export_tsv.py.

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

**What should happen this round:** the exporter theme reaches three → a **path-gated skill** (or a rule) on `shop/plugins/**`.

If `/evolve` asks you a question, or something looks wrong, don't fix it by hand: tell me.

**Then tell me "round 3 done".** Don't start round 4 before I have checked.
