#!/usr/bin/env bash
# score.sh — turn a results file into per-task scores and the gate numbers.
#
#   score.sh [path/to/results.jsonl]      (default: newest in .evolve/runs/)
#
# gain       = sum of positive deltas    (what the candidate WON)
# regression = sum of negative deltas    (what the candidate COST)
# worst_drop = the single biggest drop on any one task
#
# base is always the live harness; cand is the harness with the change. The
# verdict depends on what the change was (the sweep's `mode`):
#
#   add      (/evolve)  KEEP | KILL       must WIN something and break nothing
#                       CONFIRM           a SCREEN that passed (gain > 0, the candidate
#                                         loaded): run the confirm. A screen never KEEPs
#   replace  (/prune)   ACCEPT | REJECT   must LOSE nothing measurable
#                       | UNMEASURED      the removed skills never fired in the
#                                         suite, so "loses nothing" was not
#                                         measured and must not delete anything
#   either              RERUN             the data is not trustworthy
#
# scorable=false means DO NOT decide on this data. It is set when the sweep was
# truncated, when too many rollouts were invalid (infrastructure, not
# capability), when any task was not measured under BOTH variants at full k,
# when what a rollout loaded could not be read (firing unknown), or when the
# Claude Code CLI changed mid-sweep. A number computed from such data looks
# exactly like a real one.
#
# add mode has a fifth gate: a candidate that never loaded in any cand rollout
# cannot have caused a difference, so it is never KEPT. For a path-gated skill
# or a rule, "loaded" depends on the agent touching a matching file; `notes`
# says whether to fix the `paths` (never visible) or the description (visible,
# never invoked).
#
# EXPOSURE. A task where the change never entered the agent's context — the
# candidate never visible in any cand rollout, the replaced items never visible
# in any base rollout — ran the same harness in both arms: its difference is
# noise by construction. It stays in per_task (exposed:false) but no gate reads
# it. An always-on skill is visible everywhere, so it is exposed everywhere.
#
# RECHECK (add mode, confirm phase). At k=3 a single unlucky run on a task that
# happened to go 3/3 in base "breaks the protected set", and over a suite of
# 15+ tasks that happens to most good candidates by chance alone. So when the
# ONLY failed gates are per-task regressions (gate 2 / gate 3), the verdict is
# RECHECK: sweep just those tasks again (--phase recheck). Scoring that file
# pairs it with its confirm sweep: the regression must fail the same gate again
# on the fresh runs to KILL; otherwise the candidate is KEPT.
set -uo pipefail
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo '{"error":"not a git repo"}'; exit 1; }

R="${1:-}"
if [ -z "$R" ]; then
  R=$(ls -1t "$REPO/.evolve/runs/"*.jsonl 2>/dev/null | head -1)
fi
[ -n "$R" ] && [ -s "$R" ] || { echo '{"error":"no results"}'; exit 1; }

CFG="$REPO/.evolve/config.json"
MAXINV=$(jq -r '.max_invalid_rate // 0.1'      "$CFG" 2>/dev/null)
RTOL=$(  jq -r '.regression_tolerance // 0.34' "$CFG" 2>/dev/null)
MINNET=$(jq -r '.min_net_runs // 2'            "$CFG" 2>/dev/null)

# The gates live HERE, not in a prompt. A threshold only an LLM honours is a
# suggestion; one the scorer applies is a rule. score.sh therefore returns the
# verdict and /evolve reports it, rather than deciding for itself.
score_file() {
jq -s --arg file "$1" --argjson maxinv "$MAXINV" \
      --argjson rtol "$RTOL" --argjson minnet "$MINNET" '
  ([ .[] | select(.event == "start") ] | first)                as $start
  | ([ .[] | select(.event == "done")      ] | length > 0)     as $done
  | ([ .[] | select(.event == "truncated") ] | length > 0)     as $trunc
  # ended, but fewer rows than jobs: the queue broke or a worker died
  | ([ .[] | select(.event == "incomplete") ] | length > 0)    as $incomplete
  | ([ .[] | select(.event == "done" or .event == "truncated" or .event == "incomplete") | .epoch | numbers ] | first) as $end_epoch
  | ($start.k // 0)                                            as $k
  | ([ .[] | select(.v != null) ])                             as $all
  | ([ $all[] | select(.valid == 0) ])                         as $bad
  | ([ $all[] | select(.valid != 0) ])                         as $rows
  | ($start.mode // "add")                                     as $mode
  | (if (($start.candidate // "") == "") then null else $start.candidate end) as $cname
  | ($start.replaced // [])                                    as $replaced
  # results written before sweeps recorded invoked skills carry no "skills"
  # field: firing is then UNKNOWN, which must not read as "never fired"
  | ([ $all[] | has("skills") ] | any)                         as $tracked
  # a row whose "skills" is null means the stream could not be read: firing is
  # unknown for that rollout. Unknown must never count as "did not fire", or a
  # tooling failure would read as dead weight and /prune would delete a skill.
  | ([ $rows[] | select(has("skills") and .skills == null) ] | length) as $unknown
  # how many VALID rollouts actually invoked the skills under test
  | ([ $rows[] | select(.v == "cand" and $cname != null
                        and any((.skills // [])[]; . == $cname)) ] | length) as $cand_fired
  | ([ $rows[] | select(.v == "base"
                        and any((.skills // [])[]; . as $x | any($replaced[]; . == $x))) ]
     | length)                                                 as $repl_fired
  # visibility: did a path-gated skill ever enter the listing at all?
  | (($rows | length) > 0 and ([ $rows[] | has("visible") and .visible != null ] | all)) as $vtracked
  | ([ $rows[] | select(.v == "cand" and $cname != null
                        and any((.visible // [])[]; . == $cname)) ] | length) as $cand_visible
  | ([ $rows[] | select(.v == "base"
                        and any((.visible // [])[]; . as $x | any($replaced[]; . == $x))) ]
     | length)                                                 as $repl_visible
  | ($start.candidate_kind // "skill")                         as $ckind
  | ($start.candidate_tier // "")                              as $ctier
  # one sweep, one CLI: an auto-update mid-sweep changes how skills load
  | ([ $rows[] | .cli_version | select(. != null) ] | unique)  as $clis
  | (if ($all|length) > 0 then (($bad|length) / ($all|length)) else 0 end) as $invrate

  | ($rows | group_by(.v + "|" + .t)
           | map({v: .[0].v, t: .[0].t,
                  s: ((map(.pass) | add) / length),
                  n: length}))                                 as $agg
  | ($agg | map(select(.v=="base")) | map({(.t): .s}) | add // {}) as $base
  | ($agg | map(select(.v=="cand")) | map({(.t): .s}) | add // {}) as $cand
  | ($agg | map({ ("\(.v)|\(.t)"): .n }) | add // {})              as $counts
  | (($all | map(.t) | unique) + ($base|keys) + ($cand|keys) | unique | sort) as $tasks
  # every task the sweep planned must have rows: a task with none would vanish
  # from the scores instead of blocking them (results since planned/jobs exist)
  | (if ($start.planned | type) == "array"
     then [ $start.planned[] | . as $t | select(any($tasks[]; . == $t) | not) ] else [] end) as $missing_planned
  | ($start.jobs // null)                                      as $jobs
  # rollouts run while the machine had more runnable work than CPUs (the load
  # field of a row = runnable tasks sampled during it): their timings (agent
  # timeouts, test-internal timeouts) say nothing about the task
  | ($start.parallel.cpus // null)                             as $cpus
  | ($start.workers // 1)                                      as $workers
  | (if ($cpus | type) == "number"
     then [ $all[] | select((.load | type) == "number" and .load > $cpus) ] else [] end) as $oversub
  | ([ $all[] | .load | numbers ] | max // null)               as $peak_load
  # Rollouts do not have a CPU each: several agents on one machine sit above the
  # CPU count and still measure fine (a normal sweep of 8 sits near 1.5x). What
  # ruins a measurement is being slowed several times over, so only that blocks
  # the score; the precise harm — an agent that ran out of time while the
  # machine was oversubscribed — is already marked invalid in its row.
  | (if ($cpus | type) == "number"
     then [ $all[] | select((.load | type) == "number" and .load > (3 * $cpus)) ] else [] end) as $heavy
  | ($workers > 1 and ($all | length) > 0
     and (($heavy | length) > ($maxinv * ($all | length))))    as $overloaded

  # a task counts as measured only with k VALID rollouts under BOTH variants
  | ([ $tasks[] | select( (($counts["base|" + .]) // 0) < $k
                       or (($counts["cand|" + .]) // 0) < $k ) ]) as $unmeasured
  | ([ $tasks[] | select( (($counts["base|" + .]) // 0) >= $k
                      and (($counts["cand|" + .]) // 0) >= $k ) ]) as $measured

  # which tasks the change reached at all (null = results without visibility:
  # every task counts, as before)
  | (if $vtracked and $unknown == 0 then
       [ $rows[] | select(
           (.v == "cand" and $cname != null and any((.visible // [])[]; . == $cname))
           or (.v == "base" and any((.visible // [])[]; . as $x | any($replaced[]; . == $x))) )
         | .t ] | unique
     else null end)                                            as $exposed
  | ($measured | map(. as $t | { task: $t,
                       base: $base[$t],
                       cand: $cand[$t],
                       delta: ($cand[$t] - $base[$t]),
                       exposed: ($exposed == null or ($exposed | index($t)) != null) }))  as $per
  | [ $per[] | select(.exposed) ]                              as $scored
  | {
      file:        $file,
      phase:       ($start.phase // "unknown"),
      mode:        $mode,
      k:           $k,
      candidate:   $cname,
      replaced:    $replaced,
      candidate_kind: (if $cname != null then $ckind else null end),
      candidate_tier: (if $cname != null and $ctier != "" then $ctier else null end),
      candidate_fired_runs: (if $tracked and $unknown == 0 then $cand_fired else null end),
      replaced_fired_runs:  (if $tracked and $unknown == 0 then $repl_fired else null end),
      candidate_visible_runs: (if $vtracked and $unknown == 0 then $cand_visible else null end),
      replaced_visible_runs:  (if $vtracked and $unknown == 0 then $repl_visible else null end),
      firing_unknown_runs: $unknown,
      # what the sweep actually cost, as each rollout reported it (null for
      # results written before Cortex recorded it)
      tokens_total:   ([ $all[] | .tokens    | numbers ] | if length > 0 then add else null end),
      cost_usd_total: ([ $all[] | .cost_usd  | numbers ] | if length > 0 then (add * 100 | round / 100) else null end),
      wall_secs_total: ([ $all[] | .wall_secs | numbers ] | if length > 0 then add else null end),
      # the sweep ran `workers` rollouts at once: elapsed is the real duration,
      # wall_secs_total the sum over rollouts (null for older results files)
      workers:     ($start.workers // 1),
      elapsed_secs: (if ($start.epoch | type) == "number" and $end_epoch != null
                     then $end_epoch - $start.epoch else null end),
      cli_versions: $clis,
      model:       ($start.model // null),
      harness_base: ($start.harness_base // null),
      harness_cand: ($start.harness_cand // null),
      tasks_hash:   ($start.tasks_hash // null),
      finished:    ($done or $incomplete),
      truncated:   $trunc,
      incomplete:  $incomplete,
      jobs:        $jobs,
      planned_missing: $missing_planned,
      oversubscribed_runs: ($oversub | length),
      peak_load:   $peak_load,
      rollouts:    ($all | length),
      invalid:     ($bad | length),
      invalid_rate: ($invrate * 1000 | round / 1000),
      invalid_reasons: ($bad | map(.why) | group_by(.) | map({(.[0]): length}) | add // {}),
      unmeasured:  $unmeasured,
      per_task:    $per,
      # measured, but the change never reached the agent there: not gated
      unexposed:   [ $per[] | select(.exposed | not) | .task ],
      # No rollout of either arm passed, among the tasks the change actually
      # reached: too hard for the agent, or a check only the harvested fix can
      # pass (its names, its wording — /harvest rules 6 and 7). Tasks the change
      # never reached are NOT listed: there, "nobody passed" only says the live
      # harness fails them, which is what makes them worth targeting next.
      never_passed: [ $scored[] | select(.base == 0 and .cand == 0) | .task ],
      base_total:  ([ $per[].base ] | add // 0),
      cand_total:  ([ $per[].cand ] | add // 0),
      gain:        ([ $scored[].delta | select(. > 0) ] | add // 0),
      regression:  ([ $scored[].delta | select(. < 0) | -. ] | add // 0),
      net:         ([ $scored[].delta ] | add // 0),
      worst_drop:  ([ $scored[].delta | select(. < 0) | -. ] | max // 0),
      protected_broken: [ $scored[] | select(.base == 1 and .cand < 1) | .task ],
      scorable:    ($done and ($trunc | not) and ($incomplete | not) and ($invrate <= $maxinv) and (($unmeasured|length) == 0)
                    and (($measured|length) > 0) and ($unknown == 0) and (($clis|length) <= 1)
                    and (($missing_planned|length) == 0) and ($jobs == null or ($all|length) >= $jobs)
                    and ($overloaded | not)),
      thresholds:  { regression_tolerance: $rtol, min_net_runs: $minnet, max_invalid_rate: $maxinv },
      blocked_because: ([
          (if ($trunc)                    then "sweep was truncated at the run budget" else empty end),
          (if ($done | not) and ($incomplete | not) then "sweep did not finish" else empty end),
          (if ($incomplete)               then "the sweep recorded \($all|length) of \($jobs) rollouts: its job queue broke or a worker died — sweep again" else empty end),
          (if (($missing_planned|length) > 0) then "planned task(s) with no rollout recorded: \($missing_planned|join(","))" else empty end),
          (if ($done and ($incomplete | not) and $jobs != null and ($all|length) < $jobs)
                                          then "only \($all|length) of \($jobs) planned rollouts are in the file" else empty end),
          (if ($overloaded)               then "the machine was oversubscribed in \($heavy|length) of \($all|length) rollouts (up to \($peak_load) runnable tasks on \($cpus) CPUs, \($workers) rollouts at once): agent and test timings are unreliable — lower measurement.parallel.rollouts, or set measurement.parallel.cpus_per_rollout to about \([($peak_load / $workers | ceil), 1] | max), then sweep again" else empty end),
          (if ($invrate > $maxinv)        then "invalid rollout rate \($invrate*100|round)% exceeds limit" else empty end),
          (if (($unmeasured|length) > 0)  then "tasks not measured under both variants at k=\($k): \($unmeasured|join(","))" else empty end),
          (if (($measured|length) == 0)   then "no task was measured" else empty end),
          (if ($unknown > 0)              then "firing unknown in \($unknown) valid rollout(s): their output could not be read — re-run" else empty end),
          (if (($clis|length) > 1)        then "the Claude Code CLI changed mid-sweep (\($clis|join(", "))) — re-run on one version" else empty end)
        ])
    }
  | . as $r
  | $r.worst_drop                                               as $worst
  # the tasks behind a gate 2 / gate 3 failure: what a RECHECK re-measures
  | ([ $r.per_task[] | select(.exposed)
       | select((.base - .cand) > $rtol or (.base == 1 and .cand < 1)) | .task ]) as $regressed
  # net * k is a sum of thirds (or fifths...) and floating point does not add
  # those exactly: 7 x 1/3 x 3 = 6.999999. Round before comparing to a bar.
  | ($r.net * $r.k * 1000000 | round / 1000000)                 as $netruns
  | ([
      (if ($worst > $rtol)                     then "gate2 worst drop \($worst|.*100|round/100) exceeds tolerance \($rtol)" else empty end),
      (if (($r.protected_broken|length) > 0)   then "gate3 broke the protected set: \($r.protected_broken|join(","))" else empty end)
    ]) as $preserve
  | (if $mode == "replace" then
       ([ (if ($netruns <= -$minnet) then "gate1 the change loses \(-$netruns) runs, at least \($minnet) — a measurable loss" else empty end) ]
        + $preserve)
     else
       ([ (if ($r.gain <= 0) then "gate1 gain is \($r.gain) — helps nothing" else empty end) ]
        + $preserve
        + [ (if ($netruns < $minnet) then "gate4 net is \($netruns|.*100|round/100) runs, under \($minnet) — that is noise" else empty end) ]
        # gate 5: a win from a candidate that never loaded was not caused by it
        + [ (if ($tracked and $cname != null and $cand_fired == 0)
               then "gate5 the candidate never loaded in any cand rollout — any difference is noise, not the candidate" else empty end) ])
     end) as $failed
  # a KILL that rests ONLY on per-task regressions is re-measured first: at
  # k=3 one unlucky run on a 3/3 task looks exactly like a broken task
  | (($failed | length) > 0
     and ([ $failed[] | select(startswith("gate2") or startswith("gate3")) ] | length) == ($failed | length)
     and ($regressed | length) > 0)                             as $only_regressions
  # A task nobody passes in either arm, and a task the base already passes at
  # full marks, can show no gain whatever the candidate does. When EVERY gated
  # task is like that, the sweep measured nothing about the candidate: killing
  # it would bury an idea that was never tried. Say so instead (RERUN).
  | ([ $scored[] | select(.base < 1 and (.base > 0 or .cand > 0)) ] | length) as $informative
  | (($scored | length) > 0 and $informative == 0)              as $uninformative
  # a screen only decides whether the confirm is worth paying for: it never keeps
  | ([ (if ($r.gain <= 0) then "gate1 gain is \($r.gain) — helps nothing" else empty end),
       (if ($tracked and $cname != null and $cand_fired == 0)
          then "gate5 the candidate never loaded in any cand rollout" else empty end) ]) as $screen_failed
  | (if ($r.scorable | not) then "RERUN"
     elif ($mode == "add" and $uninformative) then "RERUN"
     elif $mode == "add" and $r.phase == "screen" then
       (if ($screen_failed | length) > 0 then "KILL" else "CONFIRM" end)
     elif $mode == "replace" and $r.phase == "screen" then
       # a screen is a filter, never a decision: it may say "not worth confirming"
       # (the live item stays), never "delete it" on a handful of rollouts
       (if (($failed|length) > 0) then "KILL" else "CONFIRM" end)
     elif $mode == "replace" then
       (if (($failed|length) > 0) then "REJECT"
        elif (($tracked | not) or $repl_fired == 0) then "UNMEASURED"
        else "ACCEPT" end)
     elif (($failed|length) > 0) then
       (if $only_regressions and $r.phase == "confirm" then "RECHECK" else "KILL" end)
     else "KEEP" end) as $verdict
  | $r + {
      net_runs: $netruns,
      gates_failed: (if ($r.scorable | not) then []
                     elif $mode == "add" and $r.phase == "screen" then $screen_failed
                     else $failed end),
      verdict: $verdict,
      recheck_tasks: (if $verdict == "RECHECK" then $regressed else [] end),
      uninformative: $uninformative,
      verdict_because: (if $verdict == "RERUN" and $uninformative and ($r.scorable)
                        then ["no task in this sweep could show a gain: "
                              + ([ $scored[] | select(.base == 0 and .cand == 0) | .task ] | join(",") | if . == "" then "none" else "\(.) never passed in either arm" end)
                              + ", " + ([ $scored[] | select(.base == 1) | .task ] | join(",") | if . == "" then "none" else "\(.) already pass without it" end)
                              + ". The candidate was not measured — repair those checks (/harvest rules 6 and 7) or screen tasks it can win, then sweep again"]
                        elif $verdict == "RERUN" then $r.blocked_because
                        elif $verdict == "CONFIRM" then
                          ["the screen passed: gain \($r.gain), the candidate loaded in \($cand_fired) rollout(s). Run the confirm over ALL tasks at k_confirm — a screen never keeps a candidate"]
                        elif $mode == "add" and $r.phase == "screen" then $screen_failed
                        elif $verdict == "RECHECK" then
                          $failed + ["only per-task regressions (\($regressed | join(","))): re-measure them with --phase recheck before killing — at k=\($r.k) one unlucky run looks the same"]
                        elif $verdict == "UNMEASURED" then
                          (if $tracked
                           then ["none of \($replaced|join(",")) fired in any base rollout — no task exercises them, so removing them was not measured"]
                           else ["this results file does not record which skills fired — re-run the sweep"] end)
                        elif (($failed|length) > 0) then $failed
                        else ["all gates passed"] end),
      notes: ([
          (if ($tracked and $cname != null and $cand_fired == 0 and $r.scorable) then
             (if $mode == "add" then "the candidate" else "the replacement \($cname)" end) + " never fired in any rollout — " +
             (if $ckind == "rule" then
                "no rollout read a file matching its paths: fix `paths`, or harvest a task that reads that area"
              elif ($ctier == "gated" and $vtracked and $cand_visible == 0) then
                "it never became visible: its paths never matched a file the agent read or wrote. Fix `paths`"
              elif ($vtracked and $cand_visible > 0) then
                "it was visible in \($cand_visible) rollout(s) but never invoked: its description did not trigger. When the fixes of these tasks edit an existing file in its area, a rule (injected on Read, no choice) would load there"
              else
                "its description did not trigger"
              end)
           else empty end),
          (if ($r.unexposed | length) > 0 and $r.scorable then
             "\($r.unexposed | length) task(s) never had the change in context (\($r.unexposed | join(","))): identical harness in both arms, so they are left out of the gates"
           else empty end),
          (if ($r.oversubscribed_runs > 0 and ($overloaded | not)) then
             "\($r.oversubscribed_runs) rollout(s) ran with more runnable work than CPUs (up to \($r.peak_load) on \($cpus)): they took longer than they would alone, which costs time, not correctness. An agent that ran out of time there is marked invalid, never failed"
           else empty end),
          (if ($r.never_passed | length) > 0 and $r.scorable then
             "task(s) \($r.never_passed | join(",")) never passed in any rollout of either arm, though the change reached them: too hard for the agent, or a check that accepts only the harvested fix (its names, its wording — /harvest rules 6 and 7). Read those check.sh files"
           else empty end)
        ])
    }
' "$1"
}

# Is a sweep running right now? sweep.sh holds .evolve/runs/.lock for its whole
# run, so an unfinished results file with a FREE lock is a sweep that died
# (killed, crashed, its terminal closed): polling it would wait forever.
RUNNING=false
if [ -f "$REPO/.evolve/runs/.lock" ]; then
  exec 8<"$REPO/.evolve/runs/.lock"
  flock -n 8 || RUNNING=true
  exec 8<&-
fi
annotate() {    # stdin: a score JSON
  jq --argjson running "$RUNNING" '. + {running: $running}
    | if (.finished == false) and (.truncated != true) and ($running | not)
      then .blocked_because = ((.blocked_because // []) + ["the sweep stopped without finishing and nothing is running (killed?) — launch the same sweep again"])
      else . end'
}

PHASE_R=$(jq -r 'select(.event == "start") | .phase // empty' "$R" 2>/dev/null | head -1)
if [ "$PHASE_R" != "recheck" ]; then
  score_file "$R" | annotate
  exit "${PIPESTATUS[0]}"
fi

# ---- a recheck: pair it with the confirm sweep that asked for it -----------
# Same candidate, same harness snapshots, and written before it (the file names
# start with a sortable timestamp).
RS=$(jq -c 'select(.event == "start")' "$R" | head -1)
CONF=""
# (read the names line by line: a repository path with a space in it split this
# list into pieces, so no confirm was ever found and every recheck answered
# "no confirm precedes this one" — a KILL on a regression it had just cleared)
while IFS= read -r f; do
  [[ "$(basename "$f")" < "$(basename "$R")" ]] || continue
  CS=$(jq -c 'select(.event == "start")' "$f" 2>/dev/null | head -1)
  [ -n "$CS" ] || continue
  if jq -en --argjson a "$RS" --argjson b "$CS" \
       '$a.candidate == $b.candidate and ($b.mode // "add") == "add"
        and $a.harness_base == $b.harness_base and $a.harness_cand == $b.harness_cand' >/dev/null 2>&1; then
    CONF="$f"; break
  fi
done < <(ls -1t "$REPO/.evolve/runs/"*-confirm.jsonl 2>/dev/null)
RC=$(score_file "$R") || exit 1
if [ -z "$CONF" ]; then
  echo "$RC" | jq '. + {verdict: "RERUN", scorable: false, gates_failed: [],
    blocked_because: ((.blocked_because // []) + ["no confirm sweep of this candidate with the same harness precedes this recheck"]),
    verdict_because: ["no confirm sweep of this candidate with the same harness precedes this recheck"]}' | annotate
  exit 0
fi
C=$(score_file "$CONF") || exit 1
jq -n --argjson c "$C" --argjson rc "$RC" --argjson rtol "$RTOL" '
  def plus(a; b): if a == null and b == null then null else (a // 0) + (b // 0) end;
  ($c.recheck_tasks // [])                                          as $want
  | [ $rc.per_task[] | select(.task as $t | $want | index($t) != null) ] as $got
  | [ $want[] | select(. as $t | [ $got[].task ] | index($t) == null) ] as $missing
  # the regression replicates when the fresh runs fail the SAME gate again
  | [ $got[] | select(.exposed and (((.base - .cand) > $rtol) or (.base == 1 and .cand < 1))) ] as $repl
  | ($c.per_task | map({(.task): .}) | add // {})                   as $cp
  | $c + {
      file: $rc.file, confirm_file: $c.file, phase: "recheck",
      finished: $rc.finished, truncated: $rc.truncated,
      rollouts: ($c.rollouts + $rc.rollouts), invalid: ($c.invalid + $rc.invalid),
      tokens_total: plus($c.tokens_total; $rc.tokens_total),
      cost_usd_total: (plus($c.cost_usd_total; $rc.cost_usd_total) | if . == null then null else (. * 100 | round / 100) end),
      wall_secs_total: plus($c.wall_secs_total; $rc.wall_secs_total),
      elapsed_secs: plus($c.elapsed_secs; $rc.elapsed_secs),
      recheck: { tasks: $want, per_task: $got, replicated: [ $repl[].task ],
                 missing: $missing, scorable: $rc.scorable, blocked_because: $rc.blocked_because }
    }
  | if $c.verdict != "RECHECK" then
      . + { notes: ((.notes // []) + ["this recheck was not asked for: the confirm verdict \($c.verdict) stands"]) }
    elif ($rc.scorable | not) or ($missing | length) > 0 then
      . + { verdict: "RERUN", scorable: false, gates_failed: [],
            blocked_because: (["the recheck sweep is not trustworthy"] + ($rc.blocked_because // [])
                              + (if ($missing | length) > 0 then ["recheck did not measure: \($missing | join(","))"] else [] end)),
            verdict_because: (["re-run the recheck: "] + ($rc.blocked_because // [])
                              + (if ($missing | length) > 0 then ["it did not measure \($missing | join(","))"] else [] end)) }
    elif ($repl | length) > 0 then
      ([ $repl[] | "task \(.task): confirm \($cp[.task].base * 100 | round)%->\($cp[.task].cand * 100 | round)%, recheck \(.base * 100 | round)%->\(.cand * 100 | round)%" ]) as $why
      | . + { verdict: "KILL",
              gates_failed: ["gate2/3 the regression replicated on recheck: " + ($why | join("; "))],
              verdict_because: ["gate2/3 the regression replicated on recheck: " + ($why | join("; "))] }
    else
      . + { verdict: "KEEP", gates_failed: [],
            verdict_because: ["all gates passed — the regression on \($want | join(",")) did not replicate on recheck"] }
    end' | annotate
