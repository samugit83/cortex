#!/usr/bin/env bash
# sweep.sh — run base vs candidate over tasks, k times each, headless.
#
#   sweep.sh --candidate <name>                       add a skill or rule  (/evolve)
#   sweep.sh --replace "<a> [b]"                      remove live items    (/prune)
#   sweep.sh --candidate <name> --replace "<a> [b]"   swap them for <name> (/prune)
#            [--tasks "01 04"] [--k 3] [--phase screen|confirm|recheck] [--dry-run] [--detach]
#            [--parallel auto|N]
#
# --detach checks everything, then runs the sweep in a session of its own, so it
# survives the shell that started it (a headless agent exiting, a closed chat),
# logging to .evolve/runs/sweep.log. /evolve and /prune launch sweeps this way.
#
# --phase recheck re-measures the tasks a confirm sweep flagged as regressed
# (score.sh verdict RECHECK), at k_confirm; score.sh pairs it with that confirm.
#
# A candidate is .evolve/candidate/<name>/SKILL.md (a skill) or RULE.md (a rule).
# base is ALWAYS the live harness as it is now: .claude/skills/ AND
# .claude/rules/. cand is the harness with the change applied. The live folders
# are never touched.
#
# --dry-run runs every check that can refuse a sweep (names, binaries, CLI
# version, reachability, budget, lock) and exits 0 without spending anything.
# Every refusal line starts with "sweep: REFUSED:" so a caller greps one marker.
#
# Writes one JSON line per rollout to .evolve/runs/<timestamp>-<phase>.jsonl.
# Launched in the BACKGROUND by /evolve and /prune: it takes tens of minutes.
#
# Rollouts run measurement.parallel.rollouts at a time (--parallel overrides it),
# each worker in a sandbox clone of its own. `auto` sizes that from ram_percent of
# the RAM available at the start (harness.py parallel). Jobs start in the same
# interleaved order as a serial sweep, so both arms of a run go side by side.
# Tasks with a precondition.sh share their services: one of them at a time,
# unless measurement.parallel.with_services says they are isolated. A task whose
# task.yaml says `exclusive: true` (it uses something machine-wide: a fixed port,
# a fixed path outside the repository) also runs one rollout at a time; preflight
# writes that flag when a check fails beside a copy of itself. Every worker gets
# a TMPDIR of its own. Each row records the machine's load: an agent that timed
# out while the CPUs were oversubscribed is INVALID, not a capability failure.
#
# CORRECTNESS INVARIANTS THIS FILE ENFORCES
#   I1  a rollout never mutates anything outside its own sandbox
#   I2  base and cand differ ONLY by the change under test
#   I3  every rollout starts from the task's broken state
#   I4  a recorded pass reflects capability, not infrastructure
#   I5  a scored task was actually measured under both variants
set -uo pipefail

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "sweep: not in a git repo" >&2; exit 1; }
EV="$REPO/.evolve"; CFG="$EV/config.json"
CORTEX_HOME="${CORTEX_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# config.yaml is the source of truth; recompile when the human edited it
if [ -f "$EV/config.yaml" ] && { [ ! -f "$CFG" ] || [ "$EV/config.yaml" -nt "$CFG" ]; }; then
  "$CORTEX_HOME/bin/compile-config.py" "$REPO" --quiet || { echo "sweep: config.yaml is invalid" >&2; exit 1; }
fi
CAND=""; REPLACE=""; TASKS=""; K=""; PHASE="confirm"; DRY=0; DETACH=0; PAR_OVERRIDE=""
ORIG_ARGS=("$@")

while [ $# -gt 0 ]; do
  case "$1" in
    --candidate) [ $# -ge 2 ] || { echo "sweep: REFUSED: --candidate needs a value" >&2; exit 1; }; CAND="$2"; shift 2 ;;
    --replace)   [ $# -ge 2 ] || { echo "sweep: REFUSED: --replace needs a value" >&2; exit 1; }; REPLACE="$2"; shift 2 ;;
    --tasks)     [ $# -ge 2 ] || { echo "sweep: REFUSED: --tasks needs a value" >&2; exit 1; }; TASKS="$2"; shift 2 ;;
    --k)         [ $# -ge 2 ] || { echo "sweep: REFUSED: --k needs a value" >&2; exit 1; }; K="$2"; shift 2 ;;
    --phase)     [ $# -ge 2 ] || { echo "sweep: REFUSED: --phase needs a value" >&2; exit 1; }; PHASE="$2"; shift 2 ;;
    --parallel)  [ $# -ge 2 ] || { echo "sweep: REFUSED: --parallel needs a value" >&2; exit 1; }; PAR_OVERRIDE="$2"; shift 2 ;;
    --dry-run)   DRY=1; shift ;;
    --detach)    DETACH=1; shift ;;
    *) echo "sweep: REFUSED: unknown arg $1" >&2; exit 1 ;;
  esac
done
refuse() { echo "sweep: REFUSED: $*" >&2; exit 1; }
read -r -a _rep <<< "$REPLACE"; REPLACE="${_rep[*]}"   # normalise whitespace, no globbing
[ -n "$CAND" ] || [ -n "$REPLACE" ] || refuse "--candidate and/or --replace required"
# PHASE names the results file and a jq key; K is arithmetic, where bash would
# evaluate something like 'a[$(cmd)]'. Both are closed sets, so check them.
case "$PHASE" in screen|confirm|recheck) ;; *) refuse "--phase must be screen, confirm or recheck, not '$PHASE'" ;; esac
if [ -n "$K" ] && ! [[ "$K" =~ ^[1-9][0-9]{0,2}$ ]]; then refuse "--k must be a positive integer, not '$K'"; fi
if [ -n "$PAR_OVERRIDE" ] && ! [[ "$PAR_OVERRIDE" =~ ^(auto|[1-9][0-9]?)$ ]]; then
  refuse "--parallel must be auto or a number from 1 to 64, not '$PAR_OVERRIDE'"
fi

# letters, digits, dot, underscore, hyphen: safe as a path AND inside JSON.
# A leading '-' would be read as an option, a leading '.' is a hidden entry.
valid_name() {
  case "$1" in ""|.|..|.*|-*|*[!A-Za-z0-9._-]*) refuse "invalid ${2:-skill name}: '$1'" ;; esac
}

# A name is a skill (.claude/skills/<n>/) or a rule (.claude/rules/<n>.md),
# never both: firing is recorded by name, so it could not be attributed.
live_kind() {
  local s=0 r=0
  [ -d "$REPO/.claude/skills/$1" ] && s=1
  [ -f "$REPO/.claude/rules/$1.md" ] && r=1
  case "$s$r" in 10) echo skill ;; 01) echo rule ;; 00) echo none ;; *) echo both ;; esac
}

# add     = cand is base + .evolve/candidate/<name>
# replace = cand is base - the --replace items (+ the candidate, if one is given)
MODE="add"; [ -n "$REPLACE" ] && MODE="replace"
CAND_PATH=""; CAND_KIND=""
if [ -n "$CAND" ]; then
  valid_name "$CAND"
  [ -d "$EV/candidate/$CAND" ] || refuse "no such candidate: $CAND (expected .evolve/candidate/$CAND)"
  CAND_PATH="$EV/candidate/$CAND"
  # one name, one idea: a buried name reused for a revised candidate makes the
  # graveyard, the journal and the cycle counts ambiguous about which is which
  if compgen -G "$EV/graveyard/$CAND" >/dev/null || compgen -G "$EV/graveyard/$CAND-20*" >/dev/null; then
    refuse "a candidate called '$CAND' is already in the graveyard: a revised idea needs a new name (e.g. $CAND-v2)"
  fi
  if   [ -f "$CAND_PATH/SKILL.md" ] && [ ! -f "$CAND_PATH/RULE.md" ]; then CAND_KIND=skill
  elif [ -f "$CAND_PATH/RULE.md" ] && [ ! -f "$CAND_PATH/SKILL.md" ]; then CAND_KIND=rule
  else refuse "candidate $CAND must contain exactly one of SKILL.md or RULE.md"; fi
fi
REPLACED_KINDS=()
for s in $REPLACE; do
  valid_name "$s"
  case "$(live_kind "$s")" in
    none) refuse "--replace: no such live skill or rule: $s" ;;
    both) refuse "--replace: '$s' is both a live skill and a live rule — fix that first (cortex skills)" ;;
    *)    REPLACED_KINDS+=("$(live_kind "$s")") ;;
  esac
done
# A candidate named like a live item would be copied INTO that skill's folder
# (cp -r nests), or sit beside a rule of the same name, so cand would silently
# test the old one. Replacing it is the only meaningful reading, and it has to
# be asked for.
if [ -n "$CAND" ] && [ "$(live_kind "$CAND")" != "none" ]; then
  case " $REPLACE " in
    *" $CAND "*) ;;
    *) refuse "a live $(live_kind "$CAND") is already called '$CAND'. To test a new version of it pass --replace $CAND; otherwise rename the candidate." ;;
  esac
fi

# FINDING 2: a missing binary would fail EVERY rollout, which reads as "the
# candidate is terrible" rather than "the environment is broken".
for c in claude jq timeout git flock python3; do
  command -v "$c" >/dev/null 2>&1 || refuse "'$c' not found on PATH"
done
HARNESS="$CORTEX_HOME/bin/harness.py"
# shellcheck source=parallel.sh
. "$CORTEX_HOME/bin/parallel.sh"

# Path-gated skills and rules load by rules verified on one CLI version. An
# older (or unreadable) CLI would measure a different loading behaviour.
MINCLI=$(jq -r '.min_claude_version // "2.1.276"' "$CFG" 2>/dev/null); MINCLI="${MINCLI:-2.1.276}"
CLI_VERSION=$(python3 "$HARNESS" cli-version --min "$MINCLI" 2>/dev/null); cvrc=$?
case $cvrc in
  0) ;;
  1) refuse "claude $CLI_VERSION is older than min_claude_version $MINCLI: path-gated skills and rules may load differently" ;;
  *) refuse "cannot read \`claude --version\` — refusing rather than measure an unknown CLI" ;;
esac

K="${K:-$(jq -r ".k_$PHASE // .k_confirm" "$CFG")}"
[[ "$K" =~ ^[1-9][0-9]{0,2}$ ]] || refuse "k from config.json is not a positive integer: '$K'"
TIMEOUT=$(jq -r '.rollout_timeout_s' "$CFG")
CHECK_TIMEOUT=$(jq -r '.check_timeout_s // 120' "$CFG")
PMODE=$(jq -r '.permission_mode' "$CFG")
MAXRUNS=$(jq -r '.max_runs_per_cycle' "$CFG")
MODEL=$(jq -r '.model // ""' "$CFG")
WT_ROOT=$(jq -r '.sandbox_root // .worktree_root' "$CFG")
[ -n "$WT_ROOT" ] && [ "$WT_ROOT" != "null" ] || { echo "sweep: sandbox_root unset" >&2; exit 1; }
case "$WT_ROOT" in
  /|/tmp|/var|/home|/usr|/etc) echo "sweep: sandbox_root is too shallow: $WT_ROOT" >&2; exit 1 ;;
  /*) ;;
  *)  echo "sweep: sandbox_root must be an absolute path" >&2; exit 1 ;;
esac
# Every repository sweeps in a folder of its own under sandbox_root. The lock is
# per repository, so two repositories (or the test suite) sweeping at once in one
# shared folder wiped each other's clone and task snapshot mid-rollout.
WT_ROOT="$WT_ROOT/$(printf '%s' "$REPO" | sha256sum | cut -c1-12)"

mapfile -t CACHE_DIRS   < <(jq -r '.cache_dirs[]?'    "$CFG")
mapfile -t HARNESS_FILES < <(jq -r '.harness_files[]?' "$CFG")
mapfile -t ROLLOUT_ENV  < <(jq -r '.rollout_env // {} | to_entries[] | "\(.key)=\(.value)"' "$CFG")

mkdir -p "$EV/runs" "$WT_ROOT"

# Sandboxes must go even when this process does not reach the end: Ctrl-C, OOM,
# a killed terminal. Without a trap they sit in /tmp until the next sweep.
# The trap is installed only AFTER the lock is held (below): a sweep refused
# because another one is running must not delete that one's sandbox on exit.
cleanup_sandboxes() {
  rm -rf "$WT_ROOT/work" "$WT_ROOT"/work-* "$WT_ROOT"/tmp-* "$WT_ROOT"/load-* "$WT_ROOT/harness-base" "$WT_ROOT/harness-cand" \
         "$WT_ROOT/tasks" "$WT_ROOT/queue" "$WT_ROOT/rollout.out" "$WT_ROOT"/rollout-*.out 2>/dev/null
  [ -n "${RESULTS:-}" ] && rm -f "$RESULTS.lock"
  rmdir "$WT_ROOT" 2>/dev/null   # this repository's folder, when nothing else is in it
  true
}

# task ids and commit ids reach paths and git arguments: validate both
task_sha() { awk '/^base_sha:/{print $2; exit}' "$EV/tasks/$1/task.yaml" 2>/dev/null; }

if [ -z "$TASKS" ]; then
  TASKS=$(find "$EV/tasks" -maxdepth 1 -mindepth 1 -type d ! -name '_broken' \
          -printf '%f\n' 2>/dev/null | sort | tr '\n' ' ')
fi
[ -n "${TASKS// /}" ] || refuse "no tasks"
for t in $TASKS; do
  valid_name "$t" "task id"
  sha="$(task_sha "$t")"
  if [ -n "$sha" ] && ! [[ "$sha" =~ ^[0-9a-f]{7,40}$ ]]; then
    refuse "task $t: base_sha '$sha' is not a commit id"
  fi
done

# ---- budget: refuse up front, never truncate ------------------------------
# A sweep that hits max_runs_per_cycle is unscorable, so every rollout it spent
# was wasted, and re-running it hits the same wall. Count before spending.
PLANNED=0
for t in $TASKS; do [ -n "$(task_sha "$t")" ] && PLANNED=$((PLANNED + K * 2)); done
if [ "$PLANNED" -eq 0 ]; then
  refuse "none of the tasks ($TASKS) exists with a base_sha — nothing to measure"
fi
if [ "$PLANNED" -gt "$MAXRUNS" ]; then
  echo "sweep: REFUSED: this sweep needs $PLANNED rollouts but max_runs_per_cycle is $MAXRUNS." >&2
  echo "       Raise measurement.max_runs_per_cycle in .evolve/config.yaml, or pass fewer --tasks." >&2
  exit 1
fi

# ---- parallel: how many rollouts at once ------------------------------------
# A number from config (or --parallel) as given; auto sized from the RAM free now.
PAR_JSON=$(cd "$REPO" && python3 "$HARNESS" parallel --kind rollouts --jobs "$PLANNED" \
             ${PAR_OVERRIDE:+--override "$PAR_OVERRIDE"} --json 2>&1) \
  || refuse "cannot size the parallel workers: $PAR_JSON"
WORKERS=$(echo "$PAR_JSON" | jq -r '.workers' 2>/dev/null)
[[ "$WORKERS" =~ ^[1-9][0-9]?$ ]] || refuse "parallel workers is not a number: '$WORKERS'"
WITH_SERVICES=$(jq -r '.parallel_with_services // false' "$CFG")
CPUS=$(echo "$PAR_JSON" | jq -r '.cpus // empty' 2>/dev/null)
TMP_ENV=()                    # a worker's own TMPDIR, set in worker()

# ---- routing: can this sweep measure the change at all? --------------------
# A path-gated skill or a rule only loads when a rollout touches a matching
# file. If no task in THIS sweep can, every rollout would measure nothing. The
# same check refuses a malformed candidate, a skill/rule name clash, and a
# symlink that would copy a file from outside the repository into the sandbox.
CHECK_OUT=$(cd "$REPO" && python3 "$HARNESS" check --quiet \
              ${CAND:+--candidate "$CAND"} ${REPLACE:+--replace "$REPLACE"} --tasks "$TASKS" 2>&1)
if [ $? -ne 0 ]; then
  echo "sweep: REFUSED: the harness check failed:" >&2
  echo "$CHECK_OUT" | grep '^error:' | sed 's/^/       /' >&2
  exit 1
fi

# ---- FINDING 3: mutual exclusion -----------------------------------------
# Two sweeps would truncate each other's results and delete each other's
# sandboxes mid-rollout. Refuse rather than interleave garbage.
exec 9>"$EV/runs/.lock"
flock -n 9 || refuse "another sweep or preflight is running (lock held)"

if [ "$DRY" -eq 1 ]; then
  echo "sweep: OK — $PLANNED rollouts, $WORKERS at a time, mode $MODE${CAND:+, candidate $CAND ($CAND_KIND)}${REPLACE:+, replacing $REPLACE}" >&2
  exit 0
fi
# --detach: every check above has passed, so a refusal was already reported. Now
# re-run this same sweep in a session of its own, so that it outlives the shell
# that started it. A `nohup ... &` from inside an agent's shell dies with the
# agent's session (a headless `claude -p` exiting, a closed chat or terminal).
if [ "$DETACH" -eq 1 ]; then
  ARGS=(); for a in "${ORIG_ARGS[@]}"; do [ "$a" = "--detach" ] || ARGS+=("$a"); done
  exec 9>&-                                   # hand the lock to the detached copy
  LOG="$EV/runs/sweep.log"
  pid=$(python3 - "$0" "$LOG" "$REPO" "${ARGS[@]}" <<'PY'
import os, sys
script, log, repo, args = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
pid = os.fork()
if pid:
    print(pid)
    sys.exit(0)
os.setsid()                                   # a new session: no hangup, no group kill
fd_in = os.open(os.devnull, os.O_RDONLY)
fd_out = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
os.dup2(fd_in, 0); os.dup2(fd_out, 1); os.dup2(fd_out, 2)
os.chdir(repo)
os.execvp("bash", ["bash", script] + args)
PY
)
  echo "sweep: started in the background (pid $pid, $PLANNED rollouts) — progress: .evolve/runs/sweep.log" >&2
  exit 0
fi
WPIDS=()
stop_workers() { local p; for p in "${WPIDS[@]}"; do kill_tree "$p"; done; wait 2>/dev/null; }
trap 'stop_workers; cleanup_sandboxes; exit 130' INT TERM
trap 'cleanup_sandboxes' EXIT

# ---- FINDING 9: one file per phase, never overwritten ---------------------
STAMP=$(date +%Y%m%dT%H%M%S)
RESULTS="$EV/runs/$STAMP-$PHASE.jsonl"
: > "$RESULTS"

# ---- FINDING 1: real isolation, not a worktree ----------------------------
# `git worktree` SHARES .git — refs, objects, stash, config. A rollout agent
# running "commit this" or "make a branch" (both ordinary harvested prompts)
# writes into the real repository. A clone has its own object store; removing
# the origin remote means a rollout cannot even push back.
make_sandbox() {
  local W="$1"
  rm -rf "$W"
  git clone --no-hardlinks --quiet --no-checkout "$REPO" "$W" 2>/dev/null || return 1
  local t sha
  for t in $TASKS; do
    sha="$(task_sha "$t")"; [ -n "$sha" ] || continue
    git -C "$W" cat-file -e "${sha}^{commit}" 2>/dev/null \
      || git -C "$W" fetch --quiet origin "$sha" 2>/dev/null || true
  done
  git -C "$W" remote remove origin 2>/dev/null || true
  git -C "$W" config user.email "cortex@local" 2>/dev/null || true
  git -C "$W" config user.name  "cortex" 2>/dev/null || true
  # .evolve/ is the experimenter's notebook: every earlier task's fix.patch,
  # the lessons, the graveyard's skills. Committed (as it should be), it sits
  # in the tree at each later base_sha — so without this the agent in BOTH
  # arms could read the answers, hiding exactly the gain being measured. A
  # sparse checkout never writes it to disk, and `git status` stays clean.
  git -C "$W" config core.sparseCheckout true 2>/dev/null || return 1
  mkdir -p "$W/.git/info"
  printf '/*\n!/.evolve/\n' > "$W/.git/info/sparse-checkout" || return 1
  return 0
}

# ---- FINDING 6: snapshot the harness ONCE ---------------------------------
# install_skills used to read $REPO/.claude/skills at every rollout, so editing
# a skill mid-sweep changed the experiment underneath itself. Freeze it.
HB="$WT_ROOT/harness-base"; HC="$WT_ROOT/harness-cand"; TS="$WT_ROOT/tasks"
# One sandbox per WORKER, never per arm: the arms differ only by which harness is
# installed, and reset_to_broken re-verifies the broken state before every
# rollout, so a clone per arm would guard nothing the reset does not already
# catch. Workers need their own only because they run at the same time.
snapshot_harness() {
  rm -rf "$HB" "$HC"; mkdir -p "$HB/skills" "$HC/skills" "$HB/rules" "$HC/rules"
  # -L: copy what the links point at, as Claude Code reads it live. Copied as
  # links they would resolve, inside the sandbox, to the files committed at the
  # task's base_sha — the old harness. Safe because the harness check has
  # already refused any link that leaves the repository or dangles.
  local d
  for d in skills rules; do
    [ -d "$REPO/.claude/$d" ] || continue
    cp -rL "$REPO/.claude/$d/." "$HB/$d/" || return 1
    cp -rL "$REPO/.claude/$d/." "$HC/$d/" || return 1
  done
  local s
  for s in $REPLACE; do rm -rf "${HC:?}/skills/$s" "${HC:?}/rules/$s.md"; done
  if [ -n "$CAND_PATH" ]; then
    rm -rf "${HC:?}/skills/$CAND" "${HC:?}/rules/$CAND.md"
    if [ "$CAND_KIND" = "rule" ]; then
      cp "$CAND_PATH/RULE.md" "$HC/rules/$CAND.md" || return 1
    else
      cp -rL "$CAND_PATH" "$HC/skills/$CAND" || return 1
    fi
  fi
  # harness_files that do not exist live must not exist in the sandbox either:
  # otherwise both arms silently run the copy committed at the task's base_sha
  local f
  : > "$HB/absent"; : > "$HC/absent"
  for f in "${HARNESS_FILES[@]}"; do
    [ -n "$f" ] || continue
    if [ -f "$REPO/$f" ]; then
      mkdir -p "$HB/files/$(dirname "$f")" "$HC/files/$(dirname "$f")"
      cp "$REPO/$f" "$HB/files/$f"; cp "$REPO/$f" "$HC/files/$f"
    else
      echo "$f" >> "$HB/absent"; echo "$f" >> "$HC/absent"
    fi
  done
  return 0
}
# The task definition is the other half of the experiment. Freeze it too, so a
# sweep measures the tasks as they were when it started even if you edit them.
# A preflight may be running (it can, during a sweep): it moves failing tasks
# into _broken/, so copy them only while it is not.
snapshot_tasks() {
  local t fd
  exec {fd}>>"$EV/runs/.tasks.lock" || return 1
  flock -w 900 "$fd" || { exec {fd}>&-; echo "sweep: a preflight kept the tasks locked for 15 min" >&2; return 1; }
  rm -rf "$TS"; mkdir -p "$TS"
  for t in $TASKS; do
    [ -d "$EV/tasks/$t" ] || continue
    cp -r "$EV/tasks/$t" "$TS/$t" || { exec {fd}>&-; return 1; }
  done
  exec {fd}>&-
  return 0
}

# Paths are part of the fingerprint: the same text moved from a skill into a
# rule is a different harness. Byte-order sort, NUL-safe names.
harness_hash() {
  ( cd "$1" 2>/dev/null && find . \( -type f -o -type l \) -print0 | LC_ALL=C sort -z \
      | xargs -0r sha256sum 2>/dev/null ) | sha256sum | cut -c1-16
}

install_harness() {           # $1 = variant, $2 = sandbox
  local v="$1" W="$2" H f
  [ "$v" = "base" ] && H="$HB" || H="$HC"
  # the checkout at base_sha may carry OLD tracked skills and rules: replace both
  rm -rf "$W/.claude/skills" "$W/.claude/rules"; mkdir -p "$W/.claude"
  cp -r "$H/skills" "$W/.claude/skills"
  cp -r "$H/rules" "$W/.claude/rules"
  [ -d "$H/files" ] && cp -r "$H/files/." "$W/" 2>/dev/null
  while IFS= read -r f; do [ -n "$f" ] && rm -f "$W/$f"; done < "$H/absent"
  return 0
}

# Stale build caches are the #1 silent corrupter of these measurements: an edit
# of identical size within the same second can leave the OLD artefact in place.
# Which directories those are is language-specific, hence configurable.
purge_caches() {
  local d
  for d in "${CACHE_DIRS[@]}"; do
    [ -n "$d" ] || continue
    find "$1" -name "$d" -prune -exec rm -rf {} + 2>/dev/null
  done
  true
}

# The verifier is part of the rollout. It gets the same env as the agent, runs
# under check_timeout_s, and ALWAYS starts from a purged cache — an edit of
# identical size within the same second can otherwise leave the old artefact
# in place and the check reads the previous state. Never rely on an env var
# alone for this; purge as well.
run_check() {                 # $1 = sandbox, $2 = task dir
  purge_caches "$1"
  ( cd "$1" && env "${TMP_ENV[@]}" "${ROLLOUT_ENV[@]}" timeout "$CHECK_TIMEOUT" bash "$2/check.sh" >/dev/null 2>&1 )
}

# An optional precondition.sh asserts the ENVIRONMENT is ready: containers up,
# database reachable, service answering. Without it, a stack that dies mid-sweep
# makes every remaining rollout fail and reads as "the candidate is terrible".
# A failed precondition marks the rollout INVALID, so it is excluded from the
# scores and counts against max_invalid_rate instead of being scored as a loss.
# Absent file = nothing to check; the task needs no services.
run_precondition() {          # $1 = sandbox, $2 = task dir ; 0 ok, 1 down, 124 hung
  [ -f "$2/precondition.sh" ] || return 0
  ( cd "$1" && env "${TMP_ENV[@]}" "${ROLLOUT_ENV[@]}" timeout "$CHECK_TIMEOUT" bash "$2/precondition.sh" >/dev/null 2>&1 )
}

# A rollout needs the machine to itself when its task says so (task.yaml
# `exclusive: true`) or when it needs services nobody declared isolated.
needs_exclusive() {           # $1 = task dir
  grep -qiE '^exclusive:[[:space:]]*(true|yes)[[:space:]]*$' "$1/task.yaml" 2>/dev/null && return 0
  [ -f "$1/precondition.sh" ] && [ "$WITH_SERVICES" != "true" ]
}

# How loaded the machine was during a rollout: the number of runnable tasks,
# sampled every second while the agent and its check ran, averaged. More
# runnable work than CPUs means every rollout ran slower than it would alone.
# (Not the 1-minute load average: it lags, and missed a whole burst of
# timeouts.) CORTEX_LOADAVG pins the value, for tests.
SAMPLER=""
sampler_start() {             # $1 = file
  : > "$1"
  if [ -n "${CORTEX_LOADAVG:-}" ]; then echo "$CORTEX_LOADAVG" > "$1"; return 0; fi
  [ -r /proc/loadavg ] || return 0
  # fd 9 is the sweep lock: a sampler (or its `sleep`) must never hold it
  ( exec 9>&-; while :; do cut -d' ' -f4 /proc/loadavg | cut -d/ -f1 >> "$1"; sleep 1; done ) &
  SAMPLER=$!
}
sampler_stop() {              # $1 = file ; prints the mean, or null
  if [ -n "$SAMPLER" ]; then kill_tree "$SAMPLER"; wait "$SAMPLER" 2>/dev/null; SAMPLER=""; fi
  awk '{ s += $1; n++ } END { if (n) printf "%.1f\n", s / n; else print "null" }' "$1" 2>/dev/null || echo null
}
oversubscribed() {            # $1 = mean runnable tasks
  awk -v l="${1:-}" -v c="${CPUS:-}" 'BEGIN { exit !(l != "" && l != "null" && c != "" && l + 0 > c + 0) }'
}

# ---- FINDINGS 3 + 4: reset must be verified, not assumed -------------------
# An unchecked `checkout` left the PREVIOUS rollout's fix in the tree, so the
# next rollout passed without doing anything — a manufactured gain. Prove the
# broken state is actually broken before handing it to the agent.
#   0 = ready   1 = reset failed   2 = state does not fail the check (I3 violated)
reset_to_broken() {
  local W="$1" sha="$2" d="$3" v="$4"   # W is this worker's sandbox
  git -C "$W" checkout -f --detach "$sha" >/dev/null 2>&1 || return 1
  git -C "$W" clean -qfdx >/dev/null 2>&1
  rm -rf "$W/.evolve"           # the sparse checkout already hides it; this also
                                # drops anything a previous rollout wrote there
  purge_caches "$W"
  install_harness "$v" "$W" || return 1
  run_check "$W" "$d"
  case $? in
    0)   return 2 ;;   # broken state PASSES the check -> the task measures nothing
    124) return 3 ;;   # the verifier itself hung -> the task is broken, not the agent
    *)   return 0 ;;   # fails as it should
  esac
}

snapshot_harness || { echo "sweep: cannot snapshot harness" >&2; exit 1; }
snapshot_tasks   || { echo "sweep: cannot snapshot tasks" >&2; exit 1; }

# ---- the jobs, in the order they must start ---------------------------------
# FINDING 8: interleave base and cand. Running every base rollout before every
# cand rollout put an hour between the two arms, so any drift (model deploy,
# rate limit, load) was perfectly correlated with the variant. Alternate them;
# with several workers, both arms of a run go side by side.
truncated=0
Q="$WT_ROOT/queue"
for t in $TASKS; do
  [ -n "$(task_sha "$t")" ] || continue          # never planned: no base_sha
  for r in $(seq 1 "$K"); do for v in base cand; do echo "$t $r $v"; done; done
done | head -n "$MAXRUNS" | queue_init "$Q" || { echo "sweep: cannot create the job queue" >&2; exit 1; }
NJOBS=$(queue_size "$Q")
[ "$NJOBS" -lt "$PLANNED" ] && truncated=1
# the tasks that got jobs: the scorer refuses a sweep where one of them has no row
PLANNED_JSON=$(cut -d' ' -f1 "$Q/jobs" | uniq | jq -R . | jq -s -c 'map(select(length > 0))')
[ "$WORKERS" -gt "$NJOBS" ] && WORKERS=$NJOBS
[ "$WORKERS" -ge 1 ] || WORKERS=1

for k in $(seq 1 "$WORKERS"); do
  make_sandbox "$WT_ROOT/work-$k" || { echo "sweep: cannot create sandbox $k" >&2; exit 1; }
done

REPLACED_JSON=$(printf '%s\n' $REPLACE | jq -R . | jq -s -c 'map(select(length > 0))')
RKINDS_JSON=$(printf '%s\n' "${REPLACED_KINDS[@]}" | jq -R . | jq -s -c 'map(select(length > 0))')
CAND_TIER=""
[ -n "$CAND" ] && CAND_TIER=$(cd "$REPO" && python3 "$HARNESS" candidate-info "$CAND" 2>/dev/null | jq -r '.tier // ""')
PAR_REC=$(echo "$PAR_JSON" | jq -c --argjson w "$WORKERS" '{setting, workers: $w, limited_by, ram_available_mb, ram_percent, per_worker_mb, cpus, max}')
printf '{"event":"start","schema":2,"t":"%s","epoch":%s,"phase":"%s","mode":"%s","k":%s,"candidate":"%s","candidate_kind":"%s","candidate_tier":"%s","replaced":%s,"replaced_kinds":%s,"tasks":"%s","harness_base":"%s","harness_cand":"%s","tasks_hash":"%s","model":"%s","cli_version":"%s","workers":%s,"parallel":%s,"jobs":%s,"planned":%s}\n' \
  "$(date -Is)" "$(date +%s)" "$PHASE" "$MODE" "$K" "$CAND" "$CAND_KIND" "$CAND_TIER" "$REPLACED_JSON" "$RKINDS_JSON" "${TASKS% }" "$(harness_hash "$HB")" "$(harness_hash "$HC")" "$(harness_hash "$TS")" "${MODEL:-default}" "$CLI_VERSION" "$WORKERS" "$PAR_REC" "$NJOBS" "$PLANNED_JSON" >> "$RESULTS"
echo "sweep: $NJOBS rollouts, $WORKERS at a time — $(echo "$PAR_JSON" | jq -r '.why')" >&2

# What did a rollout actually load? Skills show up as Skill tool calls; a
# path-gated skill also shows when it became visible; a rule leaves no trace
# at all, so it is inferred from the files the agent Read (or @-mentioned)
# matched against the rule's paths in THIS variant's snapshot.
# A stream that cannot be read gives null, never []: "unknown" must not be
# scored as "never fired".
observe_rollout() {           # $1 = variant, $2 = task dir, $3 = sandbox, $4 = stream
  local H o
  [ "$1" = "base" ] && H="$HB" || H="$HC"
  if o=$(python3 "$HARNESS" observe "$4" "$H" "$3" "$2/prompt.txt" 2>/dev/null) \
     && echo "$o" | jq -e 'has("skills")' >/dev/null 2>&1; then
    echo "$o" | jq -c '{skills, rules, visible, cli_version, tokens, cost_usd}'
  else
    echo '{"skills":null,"rules":null,"visible":null,"cli_version":null,"tokens":null,"cost_usd":null}'
  fi
}

# One rollout, start to finish, in worker $1's own sandbox.
run_rollout() {               # $1 = worker, $2 = task, $3 = run, $4 = variant
  local k="$1" t="$2" r="$3" v="$4"
  local W="$WT_ROOT/work-$1" OUT="$WT_ROOT/rollout-$1.out" d="$TS/$2"
  local tag="" sfd="" base_sha tw0 rst why t0 t1 rc loaded crc pass valid row load
  [ "$WORKERS" -gt 1 ] && tag=" [w$k]"
  rm -rf "$WT_ROOT/tmp-$k"; mkdir -p "$WT_ROOT/tmp-$k"    # a fresh TMPDIR for this rollout
  # the snapshot of a planned task must still be there. If something deleted it
  # mid-sweep, say so in the results rather than skipping the task in silence
  if [ ! -f "$d/task.yaml" ]; then
    append_line "$RESULTS" "$(printf '{"v":"%s","t":"%s","r":%s,"pass":0,"valid":0,"why":"snapshot_lost","secs":0,"wall_secs":0,"agent_rc":null,"skills":[],"rules":[],"visible":[],"w":%s}' "$v" "$t" "$r" "$k")"
    echo "[$PHASE] $v task $t run $r: its frozen snapshot vanished mid-sweep -> INVALID (snapshot_lost)$tag" >&2
    return 0
  fi
  base_sha="$(awk '/^base_sha:/{print $2; exit}' "$d/task.yaml" 2>/dev/null)"
  [ -n "$base_sha" ] || return 0

  # a task that needs the machine to itself, or services nobody declared
  # isolated, runs one rollout at a time (the lock preflight shares)
  if needs_exclusive "$d"; then
    exec {sfd}>>"$EV/runs/.services.lock"; flock "$sfd"
  fi

  tw0=$(date +%s)             # wall clock of the whole rollout: reset, checks, agent
  reset_to_broken "$W" "$base_sha" "$d" "$v"; rst=$?

  # environment gate: only meaningful once the repo is checked out
  if [ "$rst" -eq 0 ]; then
    run_precondition "$W" "$d"
    case $? in
      0)   ;;
      124) rst=5 ;;
      *)   rst=4 ;;
    esac
  fi

  if [ "$rst" -ne 0 ]; then
    case "$rst" in
      1) why="reset_failed" ;;
      2) why="broken_state_passes_check" ;;
      3) why="check_timeout" ;;
      4) why="precondition_failed" ;;
      5) why="precondition_timeout" ;;
    esac
    append_line "$RESULTS" "$(printf '{"v":"%s","t":"%s","r":%s,"pass":0,"valid":0,"why":"%s","secs":0,"wall_secs":%s,"agent_rc":null,"skills":[],"rules":[],"visible":[],"w":%s}' \
      "$v" "$t" "$r" "$why" "$(( $(date +%s) - tw0 ))" "$k")"
    printf '[%s] %s task %s run %s -> INVALID (%s)%s\n' "$PHASE" "$v" "$t" "$r" "$why" "$tag" >&2
    [ -n "$sfd" ] && { flock -u "$sfd"; exec {sfd}>&-; }
    return 0
  fi

  t0=$(date +%s)
  sampler_start "$WT_ROOT/load-$k"
  # A model change mid-cycle would silently invalidate the comparison, so
  # pin it when configured. rollout_env is applied per rollout, never
  # exported into this shell.
  ( cd "$W" && env "${TMP_ENV[@]}" "${ROLLOUT_ENV[@]}" timeout "$TIMEOUT" \
      claude -p "$(cat "$d/prompt.txt")" \
      --output-format stream-json --verbose \
      --permission-mode "$PMODE" ${MODEL:+--model "$MODEL"} >"$OUT" 2>/dev/null )
  rc=$?
  t1=$(date +%s)
  loaded=$(observe_rollout "$v" "$d" "$W" "$OUT")
  rm -f "$OUT"                # it holds whatever the agent read: never keep it

  # ---- FINDING 2: infrastructure failure is NOT a capability failure ----
  # rc 0   = agent finished        -> the check decides
  # rc 124 = timeout               -> a real failure (agent ran out of budget)
  # else   = auth, rate limit, 5xx -> INVALID, must not be scored
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then
    run_check "$W" "$d"
    crc=$?
    if [ "$crc" -eq 124 ]; then
      pass=0; valid=0; why="check_timeout"
    else
      [ "$crc" -eq 0 ] && pass=1 || pass=0
      [ "$rc" -eq 124 ] && pass=0
      valid=1; why=""
    fi
  else
    pass=0; valid=0; why="agent_rc_$rc"
  fi
  load=$(sampler_stop "$WT_ROOT/load-$k")
  # An agent that ran out of time while the machine had more runnable work than
  # CPUs was slowed down by the other rollouts, not by the task: not a result.
  if [ "$rc" -eq 124 ] && [ "$valid" -eq 1 ] && oversubscribed "$load"; then
    pass=0; valid=0; why="timeout_under_load"
  fi
  [ -n "$sfd" ] && { flock -u "$sfd"; exec {sfd}>&-; }

  row=$(printf '{"v":"%s","t":"%s","r":%s,"pass":%s,"valid":%s,"why":"%s","secs":%s,"wall_secs":%s,"agent_rc":%s,"w":%s,"load":%s}' \
    "$v" "$t" "$r" "$pass" "$valid" "$why" "$((t1-t0))" "$(( $(date +%s) - tw0 ))" "$rc" "$k" "$load" \
    | jq -c --argjson l "$loaded" '. + $l')
  append_line "$RESULTS" "$row"
  printf '[%s] %s task %s run %s -> %s (%ss)%s\n' "$PHASE" "$v" "$t" "$r" \
    "$([ "$valid" -eq 0 ] && echo "INVALID $why" || { [ "$pass" -eq 1 ] && echo PASS || echo FAIL; })" \
    "$((t1-t0))" "$tag" >&2
}

worker() {                    # $1 = worker number: claims jobs until none is left
  local job t r v st
  TMP_ENV=("TMPDIR=$WT_ROOT/tmp-$1")       # this worker process only
  while :; do
    job=$(queue_claim "$Q"); st=$?
    [ "$st" -eq 0 ] || break
    read -r t r v <<< "$job"
    run_rollout "$1" "$t" "$r" "$v"
  done
  # 1 = every job handed out. 2 = the queue broke (deleted, a full disk): stop,
  # and let the count below mark the sweep incomplete rather than done
  [ "$st" -eq 2 ] && echo "[$PHASE] worker $1: the job queue is broken — stopping" >&2
  return 0
}

for k in $(seq 1 "$WORKERS"); do
  worker "$k" &
  WPIDS+=($!)
done
wait "${WPIDS[@]}"
WPIDS=()

runs=$(jq -s '[.[] | select(.v != null)] | length' "$RESULTS" 2>/dev/null); runs="${runs:-0}"
invalid=$(jq -s '[.[] | select(.v != null and .valid == 0)] | length' "$RESULTS" 2>/dev/null); invalid="${invalid:-0}"
# every job writes exactly one row. Fewer rows than jobs means some never ran
# (the queue broke, a worker died): that sweep is NOT done, whatever else held.
incomplete=0
[ "$truncated" -eq 0 ] && [ "$runs" -lt "$NJOBS" ] && incomplete=1

cleanup_sandboxes

# ---- FINDING 5: a truncated sweep must NOT claim to be finished ------------
# The budget check above makes this unreachable in normal use; it stays as the
# last line of defence if the plan and the loop ever disagree.
if [ "$truncated" -eq 1 ]; then
  printf '{"event":"truncated","runs":%s,"invalid":%s,"limit":%s,"jobs":%s,"t":"%s","epoch":%s}\n' \
    "$runs" "$invalid" "$MAXRUNS" "$NJOBS" "$(date -Is)" "$(date +%s)" >> "$RESULTS"
  echo "sweep TRUNCATED at $runs rollouts (budget $MAXRUNS); $invalid invalid" >&2
elif [ "$incomplete" -eq 1 ]; then
  printf '{"event":"incomplete","runs":%s,"invalid":%s,"jobs":%s,"t":"%s","epoch":%s}\n' \
    "$runs" "$invalid" "$NJOBS" "$(date -Is)" "$(date +%s)" >> "$RESULTS"
  echo "sweep INCOMPLETE: $runs of $NJOBS rollouts recorded — the job queue broke or a worker died (see above); nothing here can be scored" >&2
else
  printf '{"event":"done","runs":%s,"invalid":%s,"jobs":%s,"t":"%s","epoch":%s}\n' \
    "$runs" "$invalid" "$NJOBS" "$(date -Is)" "$(date +%s)" >> "$RESULTS"
  echo "sweep done: $runs rollouts, $invalid invalid" >&2
fi
echo "results: $RESULTS" >&2
