#!/usr/bin/env bash
# preflight.sh — prove every task still discriminates.
#
# A task is only useful if it FAILS on the broken state and PASSES on the
# fixed state. If either is untrue the task measures nothing, and evolving
# against it is optimising noise. Costs zero tokens: pure git + shell.
#
# A third state guards the check itself: when the fix edits test CODE, the
# check must still pass without it. A check that needs the fix's own new test
# would grade every rollout agent on writing that same test, which it never
# does — such a task fails in both arms, forever. Test DATA the fix adds (a
# golden file, a fixture) stays: producing it can be the very house rule.
#
# Tasks are checked measurement.parallel.preflight at a time (--parallel N|auto
# overrides it), each worker in a git worktree of its own. It takes its own lock,
# not the sweeps': a /harvest can check its new task while /evolve measures in
# the background. A sweep copies the tasks only while no preflight is moving
# them (the tasks lock).
#
# Running checks side by side must never cost a good task. A check that fails
# beside the others is checked again ALONE before it is quarantined; if it passes
# alone it stays, marked `exclusive: true` in its task.yaml (it uses something
# machine-wide: a port, a path outside the repository), so sweeps run its
# rollouts one at a time. Each task's check is also run twice at the same moment,
# once per version of the task, for the same reason. Tasks marked exclusive, or needing services, are checked alone after
# the others. Every decision is written as it is made to .evolve/runs/
# preflight.log, and a quarantined task carries its reason in QUARANTINED.txt.
set -uo pipefail

# Stale build caches are the #1 silent corrupter of these measurements:
# an edit of identical size within the same second can leave Python reusing
# the OLD .pyc. Never let a check see a cache built from the other state.
PAR_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --parallel) [ $# -ge 2 ] || { echo "preflight: --parallel needs a value" >&2; exit 1; }; PAR_OVERRIDE="$2"; shift 2 ;;
    *) echo "preflight: unknown arg $1" >&2; exit 1 ;;
  esac
done
if [ -n "$PAR_OVERRIDE" ] && ! [[ "$PAR_OVERRIDE" =~ ^(auto|[1-9][0-9]?)$ ]]; then
  echo "preflight: --parallel must be auto or a number from 1 to 64, not '$PAR_OVERRIDE'" >&2; exit 1
fi
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || { echo "preflight: not inside a git repository" >&2; exit 1; }
EV="$REPO/.evolve"
CFG="$EV/config.json"
[ -f "$CFG" ] || { echo "preflight: no .evolve/config.json — run 'cortex init'" >&2; exit 1; }
CORTEX_HOME="${CORTEX_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
if [ -f "$EV/config.yaml" ] && { [ ! -f "$CFG" ] || [ "$EV/config.yaml" -nt "$CFG" ]; }; then
  "$CORTEX_HOME/bin/compile-config.py" "$REPO" --quiet || { echo "preflight: config.yaml is invalid" >&2; exit 1; }
fi
WT_ROOT="$(jq -r '.sandbox_root // .worktree_root // empty' "$CFG")"
[ -n "$WT_ROOT" ] || { echo "preflight: sandbox_root unset" >&2; exit 1; }
WT_ROOT="$WT_ROOT/$(printf '%s' "$REPO" | sha256sum | cut -c1-12)"   # this repository's own folder
CHECK_TIMEOUT="$(jq -r '.check_timeout_s // 120' "$CFG")"
mapfile -t CACHE_DIRS < <(jq -r '.cache_dirs[]?' "$CFG")
mapfile -t ROLLOUT_ENV < <(jq -r '.rollout_env // {} | to_entries[] | "\(.key)=\(.value)"' "$CFG")

purge_caches() {
  local d
  for d in "${CACHE_DIRS[@]}"; do
    [ -n "$d" ] || continue
    find "$1" -name "$d" -prune -exec rm -rf {} + 2>/dev/null
  done
  true
}
# The check runs exactly as a sweep runs it: from a COPY of the task folder,
# outside the repository, with the checkout under test as the working directory.
# Run from inside the user's repo instead, a check that cd's relative to its own
# location lands in the user's working copy — the FIXED code — and "passes".
# Its output is kept for the one line of diagnosis printed on quarantine.
# (CHECK_LOG, like WT and TC below, is each worker's own: set in check_task.)
run_check() {   # $1=dir $2=taskdir ; 0 pass, 1 fail, 124 hung
  ( cd "$1" && env "${ROLLOUT_ENV[@]}" timeout "$CHECK_TIMEOUT" bash "$2/check.sh" >"$CHECK_LOG" 2>&1 )
}
last_lines() {  # the check's own last words, for a quarantined task
  grep -v '^[[:space:]]*$' "$CHECK_LOG" 2>/dev/null | tail -n 2 | cut -c1-160 | sed 's/^/          check said: /'
}
run_precondition() {
  [ -f "$2/precondition.sh" ] || return 0
  ( cd "$1" && env "${ROLLOUT_ENV[@]}" timeout "$CHECK_TIMEOUT" bash "$2/precondition.sh" >/dev/null 2>&1 )
}
WITH_SERVICES=$(jq -r '.parallel_with_services // false' "$CFG")
# shellcheck source=parallel.sh
. "$CORTEX_HOME/bin/parallel.sh"

mkdir -p "$WT_ROOT" "$EV/runs"

# One preflight at a time. It no longer shares the sweeps' lock: its worktrees
# are its own (preflight-N), and a sweep never deletes them.
exec 9>"$EV/runs/.preflight.lock"
flock -n 9 || { echo "preflight: another preflight is already running" >&2; exit 1; }
# While this runs it may move tasks into _broken/: a sweep starting now waits to
# copy them until it is done (and this waits for a sweep that is copying them).
exec 8>>"$EV/runs/.tasks.lock"
flock -w 900 8 || { echo "preflight: a sweep kept the tasks locked for 15 min" >&2; exit 1; }

# The broken state, exactly as a sweep sandbox sees it: no .evolve/ (sweeps
# hide it — other tasks' fixes and the lessons live there).
to_base() {     # $1 = sha
  git -C "$WT" checkout -f "$1" >/dev/null 2>&1 || return 1
  git -C "$WT" clean -fdx -e .claude >/dev/null 2>&1
  rm -rf "$WT/.evolve"
}
# A patch written by an older /harvest may carry .evolve/ hunks: never apply them.
apply_fix() {   # $1 = patch, then extra git-apply flags
  local p="$1"; shift
  git -C "$WT" apply --exclude='.evolve/*' "$@" "$p" >/dev/null 2>&1
}
# Test CODE, by the conventions of most languages: a source file with a test
# name, or a source file inside a test folder. Data in a test folder (golden
# files, fixtures, snapshots) is not test code.
is_test_code() {  # $1 = path
  local b="${1##*/}"
  case "$b" in
    *.py|*.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs|*.go|*.rs|*.rb|*.java|*.kt|*.scala|*.cs|*.php|*.c|*.cc|*.cpp|*.h|*.hpp|*.swift|*.m|*.sh|*.bash|*.pl|*.lua|*.ex|*.exs|*.clj|*.dart|*.jl) ;;
    *) return 1 ;;
  esac
  case "$b" in
    test_*|*_test.*|*.test.*|*.spec.*|*_spec.*|conftest.py|*Test.java|*Tests.java|*Test.kt|*Tests.kt|*Test.cs|*Tests.cs) return 0 ;;
  esac
  case "/$1" in
    */tests/*|*/test/*|*/spec/*|*/__tests__/*) return 0 ;;
  esac
  return 1
}
TEST_EXCLUDES=()
test_excludes() { # $1 = patch ; fills TEST_EXCLUDES, one exact path per test-code file it edits
  local rec path
  TEST_EXCLUDES=()
  while IFS= read -r -d '' rec; do
    path="${rec#*$'\t'}"; path="${path#*$'\t'}"
    is_test_code "$path" || continue
    TEST_EXCLUDES+=("--exclude=$(printf '%s' "$path" | sed 's/[][*?\\]/\\&/g')")
  done < <(git -C "$WT" apply --numstat -z --exclude='.evolve/*' "$1" 2>/dev/null)
  [ "${#TEST_EXCLUDES[@]}" -gt 0 ]
}

PFLOG="$EV/runs/preflight.log"; PROBES="$EV/runs/.parallel-safe"
EXCL_WAIT="${CORTEX_EXCLUSIVE_WAIT:-20}"   # seconds a lone task waits for a sweep to free the services

# mv fails silently if the id is already quarantined; make re-runs idempotent.
# The reason goes WITH the task: whoever finds it in _broken/ reads why.
quarantine() {    # $1 = task dir, $2 = id, $3 = file with its table line and diagnosis
  mkdir -p "$EV/tasks/_broken"; rm -rf "$EV/tasks/_broken/$2"; mv "$1" "$EV/tasks/_broken/$2"
  { echo "quarantined by cortex preflight, $(date -Is):"; cat "$3" 2>/dev/null; } > "$EV/tasks/_broken/$2/QUARANTINED.txt"
}

# task.yaml flags. `exclusive: true` = the task uses something machine-wide.
is_exclusive()      { grep -qiE '^exclusive:[[:space:]]*(true|yes)([[:space:]]|#|$)' "$1/task.yaml" 2>/dev/null; }
has_exclusive_key() { grep -qiE '^exclusive:' "$1/task.yaml" 2>/dev/null; }
runs_alone() {    # $1 = task dir: exclusive, or services nobody declared isolated
  is_exclusive "$1" && return 0
  [ -f "$1/precondition.sh" ] && [ "$WITH_SERVICES" != "true" ]
}
mark_exclusive() {  # $1 = task dir, $2 = why ; never overrides a value someone wrote
  has_exclusive_key "$1" && return 0
  printf '# set by cortex preflight, %s: %s\nexclusive: true\n' "$(date +%F)" "$2" >> "$1/task.yaml"
}
probe_key() {     # $1 = task dir: what its parallel-safety verdict depends on
  cat "$1/task.yaml" "$1/check.sh" "$1/fix.patch" 2>/dev/null | sha256sum | cut -c1-16
}
want_probe() {    # $1 = task dir
  # always, whatever measurement.parallel says: a sweep can be launched with
  # --parallel N on a repo configured for 1, and would then meet the collision
  has_exclusive_key "$1" && return 1                   # decided already (by preflight or by hand)
  runs_alone "$1" && return 1
  grep -qxF "$(basename "$1") $(probe_key "$1")" "$PROBES" 2>/dev/null && return 1
  return 0
}

# The same fixed state, in two checkouts, checked at the same moment. A check
# that fails beside a copy of itself holds something machine-wide, and a
# parallel sweep would run exactly that: two rollouts of one task side by side.
# 0 = both passed, 1 = they collided, 2 = could not probe.
probe_pair() {    # $1 = worker, $2 = task dir, $3 = base_sha (the worker's own checkout is at the fixed state)
  local WT2="$WT_ROOT/preflight-$1-b" TC2="$WT_ROOT/preflight-task-$1-b" p1 p2 a b
  if [ ! -e "$WT2/.git" ]; then
    rm -rf "$WT2"
    git -C "$REPO" worktree add -f --detach "$WT2" HEAD >/dev/null 2>&1 || return 2
  fi
  ( WT="$WT2"; to_base "$3" && apply_fix "$2/fix.patch" ) || return 2
  rm -rf "$TC2"; mkdir -p "$TC2"; cp -r "$2/." "$TC2/"
  purge_caches "$WT"; purge_caches "$WT2"
  ( CHECK_LOG="$CHECK_LOG.p1"; run_check "$WT" "$TC" ) & p1=$!
  ( CHECK_LOG="$CHECK_LOG.p2"; run_check "$WT2" "$TC2" ) & p2=$!
  wait "$p1"; a=$?; wait "$p2"; b=$?
  [ "$a" -eq 0 ] && [ "$b" -eq 0 ] && return 0
  return 1
}

finish() {        # $1 = id, $2 = outcome ; the decision, recorded as it is made
  echo "$2" > "$OUTD/$1.status"
  append_file "$PFLOG" "$OUTD/$1.txt"
}

# One task, all three states, in worker $1's own worktree. Its table line (and
# diagnosis) go to $OUTD/<id>.txt, its outcome (ok | broken | skip | busy |
# retry) to .status. `retry`: it failed while other checks ran beside it, and is
# checked again alone before anything is decided.
check_task() {    # $1 = worker, $2 = task dir, $3 = parallel | alone | retry
  local WT="$WT_ROOT/preflight-$1" TC="$WT_ROOT/preflight-task-$1" CHECK_LOG="$WT_ROOT/preflight-check-$1.log"
  local dir="$2" mode="${3:-alone}" id base_sha bstate fstate noapply why o note="" pr
  id="$(basename "$dir")"
  o="$OUTD/$id.txt"; : > "$o"

  base_sha=$(awk '/^base_sha:/{print $2; exit}' "$dir/task.yaml" 2>/dev/null)
  if [ -z "$base_sha" ]; then
    printf '%-6s  %-12s  %-11s  QUARANTINE (no base_sha)\n' "$id" "--" "--" >> "$o"
    quarantine "$dir" "$id" "$o"; finish "$id" broken; return 0
  fi

  if ! to_base "$base_sha"; then
    echo "$id      --            --           QUARANTINE (sha gone)" >> "$o"
    quarantine "$dir" "$id" "$o"; finish "$id" broken; return 0
  fi
  rm -rf "$TC"; mkdir -p "$TC"; cp -r "$dir/." "$TC/"     # the copy a sweep would run

  # A down environment is NOT a bad task. Quarantining the suite because Postgres
  # is stopped would destroy it over a transient outage, so report and skip.
  if ! run_precondition "$WT" "$TC"; then
    printf '%-6s  %-12s  %-11s  SKIP (environment not ready)\n' "$id" "--" "--" >> "$o"
    finish "$id" skip; return 0
  fi

  # 1. broken state MUST fail
  purge_caches "$WT"
  run_check "$WT" "$TC"
  case $? in
    0)   bstate="PASS" ;;      # bad: the check passes before the fix
    124) bstate="HUNG" ;;      # bad: the verifier itself hangs
    *)   bstate="fail" ;;      # good
  esac
  cp "$CHECK_LOG" "$CHECK_LOG.broken" 2>/dev/null

  # 2. fixed state MUST pass
  noapply=0
  if apply_fix "$dir/fix.patch"; then
    purge_caches "$WT"
    run_check "$WT" "$TC"
    case $? in
      0)   fstate="pass" ;;    # good
      124) fstate="HUNG" ;;    # the verifier hangs
      *)   fstate="FAIL" ;;    # the fix does not fix
    esac
  else
    fstate="FAIL"; noapply=1   # patch no longer applies
  fi

  # 2b. the fixed state must pass twice at the same moment, as it will when a
  # sweep runs two rollouts of this task side by side — however many workers
  # this preflight has (once per version of the task: the result is kept)
  if [ "$mode" != "retry" ] && [ "$bstate" = "fail" ] && [ "$fstate" = "pass" ] && want_probe "$dir"; then
    probe_pair "$1" "$dir" "$base_sha"; pr=$?
    if [ "$pr" -eq 0 ]; then
      append_line "$PROBES" "$id $(probe_key "$dir")"
    elif [ "$pr" -eq 1 ]; then
      mark_exclusive "$dir" "its check failed when two copies ran at the same moment"
      note=" (exclusive: its check fails when two copies run at once — its rollouts will run one at a time)"
    fi
  fi

  # 3. the check must pass without the fix's own test code, when the fix has some
  why=""
  if [ "$bstate" = "fail" ] && [ "$fstate" = "pass" ] && test_excludes "$dir/fix.patch"; then
    to_base "$base_sha"
    if apply_fix "$dir/fix.patch" "${TEST_EXCLUDES[@]}"; then
      purge_caches "$WT"
      run_check "$WT" "$TC"
      [ $? -eq 0 ] || why=" (the check needs the fix's own test code — see /harvest rule 4)"
    else
      why=" (the fix's code does not apply without its test code)"
    fi
  fi

  if [ "$bstate" = "fail" ] && [ "$fstate" = "pass" ] && [ -z "$why" ]; then
    if [ "$mode" = "retry" ]; then
      mark_exclusive "$dir" "its check failed beside other checks and passed alone"
      note=" (exclusive: it failed beside other checks and passed alone — its rollouts will run one at a time)"
    fi
    printf '%-6s  %-12s  %-11s  ok%s\n' "$id" "$bstate" "$fstate" "$note" >> "$o"
    rm -f "$dir/QUARANTINED.txt"                        # repaired: an old reason no longer applies
    finish "$id" ok
    return 0
  fi
  # What running beside other checks can cause — a failing or hanging check —
  # is never decided in parallel: that task is checked again, alone.
  if [ "$mode" = "parallel" ] && [ "$bstate" != "PASS" ] && [ "$noapply" -eq 0 ]; then
    echo retry > "$OUTD/$id.status"
    return 0
  fi
  printf '%-6s  %-12s  %-11s  QUARANTINE%s\n' "$id" "$bstate" "$fstate" "$why" >> "$o"
  # one line of diagnosis: a quarantine with no reason sends the author
  # debugging blind, in a working copy that already contains the fix
  if [ -z "$why" ]; then
    if [ "$bstate" = "PASS" ]; then
      echo "          the check passes BEFORE the fix: it does not test the problem. check.sh runs" >> "$o"
      echo "          with the repository as its working directory; it must never cd elsewhere." >> "$o"
    elif [ "$bstate" = "HUNG" ] || [ "$fstate" = "HUNG" ]; then
      echo "          the check did not finish within check_timeout_s" >> "$o"
    elif [ "$noapply" -eq 1 ]; then
      echo "          fix.patch does not apply to base_sha any more" >> "$o"
    elif [ "$fstate" = "FAIL" ]; then
      echo "          the check fails WITH the fix applied:" >> "$o"
      last_lines >> "$o"
    fi
  fi
  quarantine "$dir" "$id" "$o"
  finish "$id" broken
}

# A task that runs alone waits a little for a sweep to free the services lock,
# never for as long as a rollout: /harvest runs this under a command timeout.
check_alone() {   # $1 = task dir, $2 = alone | retry
  local fd id; id="$(basename "$1")"
  exec {fd}>>"$EV/runs/.services.lock"
  if ! flock -w "$EXCL_WAIT" "$fd"; then
    exec {fd}>&-
    printf '%-6s  %-12s  %-11s  SKIP (busy: a running sweep holds the machine-wide resources it needs)\n' "$id" "--" "--" > "$OUTD/$id.txt"
    finish "$id" busy; return 0
  fi
  check_task 1 "$1" "$2"
  flock -u "$fd"; exec {fd}>&-
}

# ---- the tasks, and the workers that check them -----------------------------
Q="$WT_ROOT/preflight-queue"; OUTD="$WT_ROOT/preflight-out"
ALL=(); LANE=(); PAR=()
for dir in "$EV/tasks"/*/; do
  [ -d "$dir" ] || continue
  [ "$(basename "$dir")" = "_broken" ] && continue
  ALL+=("$dir")
  if runs_alone "$dir"; then LANE+=("$dir"); else PAR+=("$dir"); fi
done
{ printf '%s\n' "${PAR[@]}" | grep . || true; } | queue_init "$Q" || { echo "preflight: cannot create its job queue" >&2; exit 1; }
NTASKS=${#ALL[@]}
WORKERS=$(cd "$REPO" && python3 "$CORTEX_HOME/bin/harness.py" parallel --kind preflight --jobs "$(queue_size "$Q")" \
            ${PAR_OVERRIDE:+--override "$PAR_OVERRIDE"} 2>/dev/null)
[[ "${WORKERS:-}" =~ ^[1-9][0-9]?$ ]] || WORKERS=1

WPIDS=()
cleanup() {
  local k p
  for p in "${WPIDS[@]}"; do kill_tree "$p"; done
  wait 2>/dev/null
  for k in $(seq 1 "$WORKERS"); do
    for w in "$WT_ROOT/preflight-$k" "$WT_ROOT/preflight-$k-b"; do
      git -C "$REPO" worktree remove -f "$w" >/dev/null 2>&1
      rm -rf "$w"
    done
    rm -rf "$WT_ROOT/preflight-task-$k" "$WT_ROOT/preflight-task-$k-b" \
           "$WT_ROOT/preflight-check-$k.log"* 2>/dev/null
  done
  rm -rf "$Q" "$OUTD" "$WT_ROOT/preflight" "$WT_ROOT/preflight-task" 2>/dev/null
  git -C "$REPO" worktree prune >/dev/null 2>&1
  rmdir "$WT_ROOT" 2>/dev/null   # this repository's folder, when a sweep is not using it
  true
}
print_table() {   # every decided task, in task order
  local f id
  echo "task    broken-state  fixed-state  verdict"
  echo "------  ------------  -----------  -------"
  for f in "$OUTD"/*.status; do
    [ -e "$f" ] || continue
    [ "$(cat "$f")" = "retry" ] && continue
    id=$(basename "$f" .status)
    cat "$OUTD/$id.txt"
  done
}
# Stopped part-way (Ctrl-C, a command timeout): say what was decided — some
# tasks may already be in _broken/ — before cleaning up.
interrupted() {
  local p d=0
  for p in "${WPIDS[@]}"; do kill_tree "$p"; done
  wait 2>/dev/null
  WPIDS=()
  print_table
  for p in "$OUTD"/*.status; do [ -e "$p" ] && [ "$(cat "$p")" != "retry" ] && d=$((d+1)); done
  echo ""
  echo "preflight INTERRUPTED: $d of $NTASKS task(s) decided, the rest not checked."
  echo "Every decision is also in .evolve/runs/preflight.log; a quarantined task keeps its reason"
  echo "in .evolve/tasks/_broken/<id>/QUARANTINED.txt."
  cleanup; exit 130
}
trap 'cleanup' EXIT
trap 'interrupted' INT TERM

rm -rf "$OUTD"; mkdir -p "$OUTD"
{ echo "preflight $(date -Is): $NTASKS task(s), $WORKERS at a time"; } > "$PFLOG"
for k in $(seq 1 "$WORKERS"); do
  rm -rf "$WT_ROOT/preflight-$k"
  git -C "$REPO" worktree remove -f "$WT_ROOT/preflight-$k" 2>/dev/null || true
  git -C "$REPO" worktree add -f --detach "$WT_ROOT/preflight-$k" HEAD >/dev/null 2>&1 \
    || { echo "preflight: cannot create worktree $k"; exit 1; }
done

MODE_P=parallel; [ "$WORKERS" -gt 1 ] || MODE_P=alone
worker() {        # $1 = worker number: checks tasks until none is left
  local dir
  while dir=$(queue_claim "$Q"); do
    check_task "$1" "$dir" "$MODE_P"
  done
}
for k in $(seq 1 "$WORKERS"); do
  worker "$k" &
  WPIDS+=($!)
done
wait "${WPIDS[@]}"
WPIDS=()

# Nothing else runs now: the tasks that failed beside others, then the tasks
# that must run alone, one at a time.
for dir in "${ALL[@]}"; do
  id=$(basename "$dir")
  if [ -f "$OUTD/$id.status" ] && [ "$(cat "$OUTD/$id.status")" = "retry" ]; then
    check_alone "$dir" retry
  fi
done
for dir in "${LANE[@]}"; do
  check_alone "$dir" alone
done

print_table
valid=0; broken=0; envdown=0; busy=0
for f in "$OUTD"/*.status; do
  [ -e "$f" ] || continue
  case "$(cat "$f")" in
    ok)     valid=$((valid+1)) ;;
    skip)   envdown=$((envdown+1)) ;;
    busy)   busy=$((busy+1)) ;;
    *)      broken=$((broken+1)) ;;
  esac
done

cleanup
trap - EXIT INT TERM
echo ""
echo "valid=$valid quarantined=$broken skipped=$((envdown + busy))"
if [ "$envdown" -gt 0 ] || [ "$busy" -gt 0 ]; then
  echo ""
  [ "$envdown" -gt 0 ] && echo "$envdown task(s) skipped: precondition.sh says the environment is not ready." \
    && echo "Start the stack those tasks need, then run preflight again."
  [ "$busy" -gt 0 ] && echo "$busy task(s) skipped: a running sweep is using the machine-wide resources they need." \
    && echo "Run preflight again when the sweep is done."
  echo "Nothing was quarantined for this — an unavailable environment is not a broken task."
  exit 3
fi
[ "$valid" -ge "$(jq -r '.min_valid_tasks' "$CFG")" ] || {
  echo "NOT ENOUGH VALID TASKS — harvest more before evolving"; exit 2; }
