# Cortex concept audit: what is borrowed, what is new

*Status as of 2026-09-19. This field changes weekly: re-check before submission.*

## 1. Bottom line

- **The theory was borrowed.** The original THEORY.md (since replaced; see §4)
  and the README theory section were an adaptation of **DarwinX** (arXiv
  2608.07545, Aug 2026): the frozen model,
  preserve-and-extend, avg@k, "permissive to try, strict to trust", the three
  learning signals, the four limitations, and even "collect online, evolve
  offline" and "dead weight after the model internalizes it" (DarwinX App. E).
  Several sentences are near-verbatim.
- **Most of the mechanisms have 2026 prior art**, often from the last few weeks:
  - measured deletion (ASSAY);
  - paired net-gain gates (SkillGen, PACE);
  - no-regression gates (HarnessX, Self-Harness);
  - rejected-edit journals (six papers);
  - context cost as an objective (Meta-Harness);
  - invocation detection in Claude Code (SkillReducer);
  - repo-mined, fail-to-pass-validated skill evaluation in real Claude Code (**Skill Issue**, 11 Sep 2026).
- **What is genuinely new is narrower, but real:**
  1. an **exposure-aware measurement semantics**: an item is credited or blamed only where it entered context;
  2. **measured tier placement** of native Claude Code knowledge;
  3. the **full lifecycle for one developer**, run in the real tool against a live concurrent control.

  None of these is a new *algorithm*. The strongest paper built on them is a
  careful *measurement* paper, not a "new self-evolving agent" paper.
- **Statistical warning.** Skill Issue and PACE together imply that Cortex's
  current k=2/3 gates on 3–10 tasks cannot resolve ~5-point effects. A
  simulation (§6) puts power at +5pp barely above the false-KEEP rate. This is
  fixable, and fixing it could itself be part of the contribution.

---

## 2. How this audit was done

1. I read the whole project: README (3,228 lines), the original THEORY.md, the three command
   prompts, the headers of `score.sh` and `sweep.sh`, and the layout of `harness.py`.
   This produced an inventory of ~60 concepts.
2. Background agents searched and read the literature. I set up each of them
   and cross-checked what they returned.
   - **Read in full (23):** DarwinX, SkillHone, Bayesian-Agent, WikiSkill, Evo-Harness, JIT-Agent,
     AHE, Harness Updating ≠ Harness Benefit, DemoEvolve, HarnessX, Lilian Weng's
     survey, SkillOpt, EvoSkill, Trace2Skill, SICA, Self-Harness, Meta-Harness,
     ASSAY, SkillReducer, SkillGen, Skill Issue, PACE, HarnessDev.
   - **Abstract or partial reading only (~30):** everything else cited in §9.
     These are marked [abs].
3. Each concept is labeled:

| Label | Meaning |
|---|---|
| **BORROWED** | taken from a specific source, which must be cited |
| **PRIOR ART** | exists elsewhere, found independently or not; cite it and do not claim it |
| **ADAPTED** | a known idea changed in a way that matters |
| **NEW (narrow)** | not found in anything we read, but small or specific to the setting |
| **NEW** | not found, and substantive |

---

## 3. Concept-by-concept

### 3.1 Theory and framing

| Cortex concept | Label | Source / closest work | What Cortex actually adds |
|---|---|---|---|
| Model frozen, only the harness evolves | BORROWED | DarwinX §2; field-wide (AHE, Self-Harness, Meta-Harness) | Text files only (DarwinX also edits code) |
| Fitness = verifier exit code, no LLM judge | ADAPTED | DarwinX uses benchmark verifiers, but its promote/revert is decided by an LLM "reasoned verifier agent", and WebArena-Infinity uses an LLM judge | Fully deterministic verdict |
| avg@k | BORROWED | DarwinX | — |
| Preserve and extend: `gain > 0 ∧ regression ≤ δ` | BORROWED | DarwinX §2.1, same formula | DarwinX never states δ; Cortex fixes δ = 1/k and couples it to k |
| "Permissive to try, strict to trust"; screen → confirm | BORROWED / ADAPTED | DarwinX: avg@3 screen on rotating subsets → avg@5 confirm | Screen only on the *currently failing* tasks, k=2 → k=3 |
| Three learning signals (failure / teacher / self) | BORROWED, **only partly implemented** | DarwinX §2.4 | See §4: the self signal does not exist in the code |
| Human corrections (`lessons.md`) as the teacher | ADAPTED → NEW (narrow) | DarwinX's teacher is a reference solver; DemoEvolve uses human *demonstrations* | Not found in any paper read |
| "Surviving skills are procedural" | BORROWED **finding** | DarwinX (verification / artifact-contract family) | For Cortex this is an untested hypothesis |
| "Capability and compliance rise together" | BORROWED **finding** | DarwinX (293 → 17 invalid trajectories) | Was stated as fact in the original THEORY.md; unmeasured in Cortex |
| The proxy saturates; the best proxy fit is not the best generaliser | BORROWED, near-verbatim | DarwinX (TerminalWorld 0.505 → 1.000 train vs 68.3% held-out) | — |
| No component independently validated; transfer is weaker | BORROWED | DarwinX limitations | — |
| Noise ≈ the size of one edit | BORROWED | Bjarnason et al. 2602.07150, via DarwinX | — |
| Collect online, evolve offline | BORROWED | DarwinX App. E (verifier and avg@k-cost arguments) | The "impossible to debug" argument is Cortex's own |
| Skills become dead weight after the model internalizes them | BORROWED **idea** | DarwinX App. E (untested); Anthropic, "new rules of context engineering for Claude 5" (Jul 2026); SkillReducer; Patel et al. 2609.03141 [abs] | The **mechanism** (re-test every item after a model change, biggest first) is NEW (narrow) |
| One lineage, no merge, "safe at this scale" | ADAPTED (a simplification) | DarwinX rejects single lineage; its merged harness beat every specialist on TerminalWorld (28 vs 24–27 of 41); on WebArena-Infinity every merge was reverted | The "safe" claim must be softened, with this evidence cited |

### 3.2 Measurement protocol

| Cortex concept | Label | Closest work | Difference |
|---|---|---|---|
| Paired with/without on the same tasks | PRIOR ART | SkillGen, PACE, Skill Issue | — |
| **Base re-measured live in the same sweep, interleaved base/cand** | NEW (as practice) | DarwinX, Meta-Harness, Skill Issue and SkillGen all use cached parent/seed scores; Self-Harness measures base once per round; PACE pairs but does not discuss interleaving | Standard experimental design (a concurrent control), but absent from this literature. Claim it as rigor, not as a concept |
| **Marginal value on top of the full live library** (leave-one-in / leave-one-out) | NEW (narrow) | ASSAY uses random masking (marginalised over co-occurring skills); SkillGen and Skill Issue compare against an *empty* baseline | Measures exactly the decision the user faces |
| Harness snapshot, isolated clones, cache purge | PRIOR ART in principle | ABC checklist T.4 (2507.02825); Anthropic "Demystifying evals" | Specific instances belong in the pitfalls catalog |
| **Verified reset:** `check.sh` must fail before every rollout | NEW (narrow) | Not found per rollout (Terminal-Bench checks with a no-op agent at task-validation time) | — |
| **Task store hidden from the sandbox** (committed `.evolve/` would leak earlier tasks' fixes) | NEW (narrow) | Not found | A real leakage vector, specific to tasks stored in the same repo |
| Infrastructure-invalid rollouts excluded | PRIOR ART | ABC T.3; SWE-rebench reruns; HarnessDev excludes invalid runs | Many others count them as failures (AHE, HarnessX, JIT, SICA, Self-Harness) |
| **Refuse to decide (RERUN)** on truncation, missing runs, CLI drift or unknown firing | NEW (narrow) | ABC T.3 is closest; no paper returns "no verdict" | — |
| Agent timeout = valid fail; check timeout = invalid | NEW (narrow) | DarwinX, SICA and SkillOpt treat timeouts as failures | Detail |
| Run-to-run noise | PRIOR ART | Bjarnason 2602.07150; Atil 2408.04667; HarnessDev (±4.75 on the same commit); Anthropic infrastructure-noise post | — |

### 3.3 Acceptance gates

| Gate | Label | Closest work |
|---|---|---|
| 1. gain > 0 | BORROWED | DarwinX |
| 2. worst single-task drop ≤ δ | NEW (narrow) | DarwinX bounds only the summed regression |
| 3. protected set: tasks at 1.00 stay at 1.00 | PRIOR ART | HarnessX "seesaw"; Self-Harness no-regression; ASSAY splits |
| 4. net·k ≥ 2 runs | PRIOR ART | SkillGen `G ≥ max{2, ⌈0.05m⌉, 1}` |
| 5. candidate must have loaded | ADAPTED → NEW (narrow) | SkillMAS "only execution-supported skills receive positive credit"; DemoEvolve's "inert edit" (a real false accept, found only by audit); Updating≠Benefit skill-load rate. Cortex makes it an **automatic acceptance gate** |
| **Gates 1–4 read only *exposed* tasks** | **NEW** | Not found. Tasks where the item never entered context are excluded as noise by construction |
| RECHECK: replicate regression-only kills | NEW (narrow) | Not found. **Caveat:** asymmetric; it biases toward KEEP |
| 0. scorable | NEW (narrow) | see §3.2 |
| Verdict in deterministic code, not an LLM | PRIOR ART | HarnessX, SkillOpt, SkillGen. DarwinX is the opposite (LLM verifier) |
| Statistical calibration of the rule | **MISSING** | PACE (2606.08106): fixed-n / greedy rules have uncontrolled false-commit rates; anytime-valid e-process gates. See §6 |

### 3.4 Deletion (`/prune`)

| Cortex concept | Label | Closest work | Difference |
|---|---|---|---|
| Delete a skill by measured ablation | PRIOR ART | **ASSAY** (2606.15390): per-skill causal effect by random masking; retire if \|effect\| < 0.10. Trace2Skill: patch leave-one-out. SkillReducer: clause delta-debugging. konomi-ablate (GitHub) [abs] | — |
| Delete by usage or LLM judgment | PRIOR ART (the contrast) | Bayesian-Agent (posterior retire < 0.45); SkillOps [abs]; AHE, HarnessX, Meta-Harness (LLM-proposed removal) | Cortex forbids both |
| **UNMEASURED: never delete what never fired** | **NEW** | **The opposite** of ASSAY (small effect → retire) and SkillReducer ("never triggered → obsolescence") | The central principled difference |
| Usage logs choose *what to test*, never decide | NEW (narrow) | SkillOps retires on usage | — |
| Measure each item only on tasks where it can load | NEW (narrow) | Not found | Cost efficiency |
| Human approves a cost-estimated plan | NEW (narrow) | Not found | UX / governance |
| Merge colliding skills, measured | ADAPTED | ASSAY merges by keeping the higher-scoring skill (unmeasured); Evo-Harness merges by LLM | The merge itself is measured |
| Re-test everything after a model change, biggest first | NEW (narrow) | ASSAY computes "once per base model" with no ordering; the idea is public (DarwinX App. E, Anthropic Jul 2026) | Mechanism, not idea |

### 3.5 Context cost and tiers

| Cortex concept | Label | Closest work | Difference |
|---|---|---|---|
| Context cost in the objective | PRIOR ART | Meta-Harness: accuracy × context Pareto; CROP `Acc − λ·L` (output tokens) [abs]; SkillReducer (constrained) | Cortex's λ targets *always-on* context specifically: narrow |
| Always-on budget | PRIOR ART | Anthropic docs (CLAUDE.md < 200 lines; SKILL.md < 500); Evo-Harness caps skill count | — |
| Progressive / lazy loading | PRIOR ART | Anthropic Agent Skills; Cursor rules; SkillReducer; EvoSkill | — |
| **Narrowing: move an item between CLAUDE.md, path-scoped rule, path-gated skill and always-on skill, measured as a replacement** | **NEW** | SkillReducer and SkillZip Pro move content *within one skill*; ASSAY splits into embedding-routed variants; Anthropic docs *advise* moving to path rules but don't measure it | The best single novelty candidate |
| Tier chosen from the files the fix touched (`fix.patch`) | NEW (narrow) | Not found | Evidence-derived globs |
| DEAD-glob detection and repair from git rename history | NEW (tooling) | Not found | Engineering, not research |

### 3.6 Attribution

| Cortex concept | Label | Closest work |
|---|---|---|
| Detect skill invocation from the Claude Code stream | PRIOR ART | SkillReducer (same mechanism) |
| Visible vs invoked | PRIOR ART as a distinction | Updating≠Benefit ("listed in catalog" vs loaded); Su et al. 2604.24594 [abs] |
| **Rule firing inferred from a Read of a matching file, plus the diagnosis map** (never visible → fix `paths`; visible but not invoked → fix description; rule never read → harvest a task) | NEW (narrow) | Not found. Note: Claude Code documents an `InstructionsLoaded` hook that could give direct evidence |
| Firing *unknown* ≠ did not fire | NEW (narrow) | Not found |

### 3.7 Tasks

| Cortex concept | Label | Closest work |
|---|---|---|
| Fails on broken, passes on fixed | PRIOR ART | SWE-bench, SWE-rebench, SWE-smith, Terminal-Bench, **Skill Issue** |
| Passes when the fix's own test edits are removed | NEW (narrow) | Skill Issue uses a different, static stranded-fix check |
| Tasks from repo history | PRIOR ART | Skill Issue, SWE-smith, gskill |
| Tasks from real developer sessions | PRIOR ART | REAP/Harvest (Meta, 2604.01527) [abs]; SWE-Together (2606.29957) [abs] |
| **Tasks from *one* developer's own sessions at session end, verbatim prompt, corrections encoded in the check** | NEW (narrow, setting) | Not found in this form |
| Re-validate every cycle; quarantine rotten tasks | NEW (narrow) | Validation is done once elsewhere |
| Private, post-cutoff tasks avoid contamination | PRIOR ART | SWE-rebench, SWE-bench-Live |

### 3.8 Proposal and loop control

| Cortex concept | Label | Closest work |
|---|---|---|
| Journal / graveyard of rejected edits read by the proposer | PRIOR ART | SkillHone, WikiSkill, SkillOpt, EvoSkill, AHE, HarnessX, Self-Harness, Meta-Harness |
| One additive change per cycle | PRIOR ART | DarwinX, Self-Harness, SkillGen |
| Theme must recur ≥ 3 times before proposing; barren-streak stop | NEW (narrow) | Not found; design heuristics |
| Explicit layer choice (skill / CLAUDE.md / hook / settings / MCP) | NEW (narrow) | Not found as an explicit step |
| Loop driven by markdown slash commands inside the tool itself | NEW (tooling) | — |

### 3.9 Setting

| Cortex concept | Label | Closest work |
|---|---|---|
| **Single developer, low budget, own repo, the real Claude Code harness** | **NEW (positioning)** | Every paper read is benchmark-scale. Skill Issue is the closest: real Claude Code, but open-source repos, $2k, 69 h |

---

## 4. Where the original theory did not match the code

These problems were found in the original THEORY.md. On 2026-09-19 THEORY.md
was rewritten from scratch, from the code and the README. Each item's status:

1. **The self-derived signal is not implemented.** The original Mechanism 4 said
   it "falls out naturally". But `bin/sweep.sh:458` deletes every rollout's
   output ("never keep it"), and `/evolve` A3 reads lessons, graveyard, journal,
   failing tasks and *interactive* transcripts, never rollout traces. Cortex has
   **two** signals, failure and human correction.
   *Fixed in the new THEORY.md §9.* Implementing a pass-vs-fail diff remains an
   option.
2. **"Sized for one person … safe"** left out DarwinX's own counter-evidence on
   merging. *Fixed in THEORY.md §10 and the README "Sized for one person" table.*
3. **Two DarwinX findings were stated as facts:** "skills that survive are
   procedure" and "capability and compliance rise together".
   *Now listed as untested hypotheses in THEORY.md §11.*
4. **Near-verbatim sentences.** For example, "the variant that best fits the
   proxy is not the best generaliser". *Removed from THEORY.md. Rewritten in the
   README, which now credits DarwinX at the top of its theory section.* The
   README theory section still follows DarwinX's structure closely. That is
   fine now that it is cited, but re-check its wording before publication.

---

## 5. What Cortex can claim, ranked

Phrase every claim as "to our knowledge", with the citations from §3.

1. **Exposure-aware measurement semantics for harness items (NEW).** One
   principle, applied consistently: *an item can only be credited or blamed
   where it entered the agent's context.* It becomes four rules:
   - gates read only exposed tasks;
   - a candidate that never loaded is never kept;
   - a removal that never fired is UNMEASURED and never deleted;
   - unknown firing blocks the verdict.

   This directly contradicts the deletion rules of ASSAY and SkillReducer, and
   it explains DemoEvolve's inert-edit failure. It is the most defensible
   *conceptual* contribution.
2. **Measured tier placement for native coding-agent knowledge (NEW).**
   Narrowing, meaning a move between always-on CLAUDE.md or skill, path-gated
   skill and path-scoped rule, as an operator judged by a replacement sweep
   under an always-on context budget. It comes with rule-firing attribution and
   a trigger diagnosis.
3. **A complete, single-developer lifecycle in the real tool (NEW positioning).**
   It covers:
   - harvest from your own sessions;
   - add against a live, interleaved, full-library base;
   - measured delete, narrow and merge;
   - re-test after a model change;
   - human-approved budgets.

   This is an integration contribution: no individual step is unprecedented,
   but the whole is.
4. **A catalog of measurement-integrity threats for agent-harness experiments
   (PARTIALLY NEW).** It includes:
   - the verified reset;
   - answer leakage from a committed task store;
   - the Python `(mtime, size)` bytecode bug;
   - snap Docker `/tmp`;
   - CLI drift;
   - check-timeout vs agent-timeout;
   - shared services running the main branch's code.

   It complements the ABC checklist and Anthropic's eval posts.
5. **Placebo-calibrated acceptance (NEW, if you do it).** Prior work uses
   placebo skills as an extra *comparison arm* (Signal or Noise? 2608.23067;
   Huang 2607.07504). Nobody runs known-null edits *through the acceptance rule*
   to measure its false-accept rate on real coding-agent harnesses. PACE does
   something similar only on toy math/QA prompts. This is the POOL experiment
   already in the plan.

## 6. Drop these claims

- a paired with/without net-gain gate (SkillGen, PACE);
- measured skill deletion, merging or splitting (ASSAY, Trace2Skill);
- "skills can hurt", "less context helps" (ASSAY, SkillReducer, Gloaguen 2602.11988, Hajimiri 2606.15017);
- context cost as an objective (Meta-Harness, CROP);
- progressive / conditional loading (Anthropic, SkillReducer);
- detecting skill invocation in Claude Code (SkillReducer);
- visible vs loaded as a distinction (Updating≠Benefit, Su et al.);
- no-regression / protected set (HarnessX, Self-Harness);
- rejected-edit memory (eight papers);
- fail-to-pass task validation, and repo-mined skill evaluation in Claude Code (SWE-bench family, Skill Issue);
- model-specific harnesses and "scaffolding goes stale" (Self-Harness, Anthropic, DarwinX App. E);
- a deterministic gate as opposed to an LLM judge (HarnessX, SkillOpt).

---

## 7. The statistical problem, and why it helps the paper

**What the literature says:**
- **Skill Issue:** a whole SKILL.md against an empty seed moves scores ~5pp
  (GEPA +4.9, SkillOpt +0.1). At 20–26 tasks a sign test needs ~80% of
  disagreements to go one way; the best p was 0.29.
- **HarnessDev:** the same harness commit varies ±4.75 points on ~190 tasks.
  Only 2 of 64 harness switches were clearly beyond noise, and the feedback and
  held-out scores moved the same way only 53% of the time.
- **PACE:** greedy acceptance commits 30–42% false edits when a real
  improvement exists, and 72–100% under pure noise. Paired / e-process gates:
  fewer than 1 per run.

**Simulation of Cortex's current gates** (screen k=2 → confirm k=3, all gates,
RECHECK; one agent's model with its own assumptions, not verified by me;
script in the session scratchpad):

| Tasks | False KEEP (null candidate) | Power at +5pp | Power at +20pp |
|---|---|---|---|
| 3 | 2–8% | — | 16–38% |
| 5 | 3–9% | ~15% | 32–51% |
| 10 | 5–8% | 14–21% | 59–72% |

So Cortex is **far better than greedy**, but at realistic ~5pp effects its
power is only about twice its false-KEEP rate. If fewer than about a quarter of
proposals are real improvements, most KEEPs are noise. Large, repo-specific
effects (+20pp on exposed tasks) are detectable.

**Why this helps:** it gives the paper a sharp, honest core. Fixes that could
become contributions:
1. **Placebo A/A calibration:** measure the pipeline's real false-KEEP rate.
2. **A stated paired test** on discordant pairs, clustered by task (an exact
   sign test, or a PACE-style e-process), with an **INCONCLUSIVE** verdict.
3. **Evidence that accumulates across weeks.** An e-process can keep adding
   newly harvested tasks, which fits the weekly cadence.
4. **A per-cycle minimum detectable effect**, printed by `cortex score`.
5. **A temporal hold-out:** re-score each KEEP on tasks harvested *after* the decision.
6. **Symmetric RECHECK:** replicate marginal KEEPs too, not only
   regression-based KILLs.
7. **Exposure filtering is itself a power booster.** Dropping unexposed tasks
   removes pure-noise pairs. Quantify this: it links contribution 1 to the
   statistics.

---

## 8. What this means for the paper

- **Recommended framing:** *a measurement paper.* Roughly: "What can one
  developer reliably learn about their coding-agent harness? Exposure-aware,
  placebo-calibrated maintenance of Claude Code skills and rules."
  - **Contributions:** (1) exposure-aware semantics, (2) measured tier placement,
    (3) the integrity catalog, (4) placebo-calibrated gates with honest power,
    (5) the open tool.
  - **Results:** noise, false-KEEP on placebos, power, what survives, and
    context saved.
- **Avoid:** "a new self-evolving agent". DarwinX, Self-Harness, Meta-Harness,
  AHE and HarnessX own that space, with benchmark results Cortex cannot match.
- **Update the plan:**
  - Gate G1 is answered: there is a gap, but a narrower one than expected.
  - Change the gates (§7) **before** the code freeze (plan step 3.2).
  - The POOL experiment with placebos is now the centre of the paper, not a side check.
- **THEORY.md: done (2026-09-19).** Rewritten from scratch, from the code and
  the README. Each principle names the file that implements it, and the limits
  and hypotheses are stated. It ends with a credits table that follows this
  audit.

---

## 9. Must-cite references, by paper section

**Introduction / motivation**
- DarwinX 2608.07545 (the parent)
- Skill Issue 2609.12742 (closest; skill gains hidden in noise)
- ASSAY 2606.15390 (skills can hurt)
- Gloaguen et al., "Evaluating AGENTS.md", 2602.11988 [abs]
- Hajimiri et al. 2606.15017 [abs]
- Anthropic, "The new rules of context engineering for Claude 5" (Jul 2026)

**Background**
- Anthropic Agent Skills docs and engineering post
- Claude Code memory / rules docs (paths, `InstructionsLoaded`)
- SWE-bench 2310.06770
- Bjarnason et al. 2602.07150

**Design:** cite at each mechanism
- DarwinX (preserve-and-extend, two speeds, signals)
- SkillGen 2605.10999 (net-gain gate)
- HarnessX 2606.14249 and Self-Harness 2606.09498 (no-regression)
- SkillMAS 2605.09341 and DemoEvolve 2605.24539 (credit only what fired)
- SkillReducer 2603.29919 (invocation detection, progressive disclosure)
- ASSAY (deletion: the direct counterpoint to UNMEASURED)
- Meta-Harness 2603.28052 (context-cost objective)
- SWE-rebench 2505.20411 and Skill Issue (task validation)

**Statistics / evaluation**
- PACE 2606.08106
- Miller, "Adding error bars to evals", 2411.00640
- HarnessDev 2609.01437
- Sida Wang 2512.21326 [abs]
- Madaan et al. 2406.10229 [abs]
- Atil et al. 2408.04667 [abs]
- Anthropic infrastructure-noise post (2026)
- ABC checklist 2507.02825

**Placebo controls**
- Signal or Noise? 2608.23067 [abs]
- Huang 2607.07504 [abs]
- Sclar et al. 2310.11324 [abs]

**Related work: harness / skill evolution**
- AHE 2604.25850
- Harness Updating ≠ Harness Benefit 2605.30621
- SkillHone 2606.08671
- Bayesian-Agent 2606.08348
- WikiSkill 2608.27454
- Evo-Harness 2608.15071
- JIT-Agent 2608.25593
- SkillOpt 2605.23904
- EvoSkill 2603.02766
- Trace2Skill 2603.25158
- SICA 2504.15228
- Darwin Gödel Machine 2505.22954
- ADAS 2408.08435
- GEPA 2507.19457
- ACE [arXiv ID to verify]
- Lilian Weng, "Harness Engineering for Self-Improvement" (Jul 2026)

**Related work: tasks and contamination**
- SWE-smith 2504.21798
- SWE-Gym 2412.21139
- Terminal-Bench 2601.11868
- SWE-Bench+ 2410.06992
- SWE-bench-Live 2505.23419 [abs]
- REAP 2604.01527 [abs]
- SWE-Together 2606.29957 [abs]

**Still to read before submission:**
- Self-Harness and DarwinX yourself, in full
- SkillMAS in full
- "What Happens When the Model Eats the Stack?" 2609.03141
- SkillOps 2605.13716
- konomi-ablate (GitHub)
- a fresh search in the final week

## 10. Caveats

- Papers marked [abs] were checked only from their abstract or through a
  summarising tool. Verify them before citing.
- A few titles and IDs were corrected along the way (Bayesian-Agent "Across";
  JIT-Agent). Check every bibliography entry against arXiv.
- SkillGen's net-gain threshold is 2 in the paper and 3 in its repository config.
- The simulation in §7 is a model, not a measurement. The POOL experiment replaces it.
- In 2026 this area gets new preprints almost weekly. Skill Issue appeared
  8 days before this audit.
