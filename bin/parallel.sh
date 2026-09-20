# parallel.sh — sourced by sweep.sh and preflight.sh: a job queue that N worker
# processes share, and a way to stop a worker together with everything it started.
#
# The queue is a folder: `jobs` (one job per line, in the order they must start)
# and `next` (the line number the next claim gets), guarded by flock. Workers
# claim jobs one at a time, so a slow job never holds up the others, and the
# start order is exactly the order of `jobs`.

queue_init() {   # $1 = queue dir ; the jobs are read from stdin, one per line
  rm -rf "$1" && mkdir -p "$1" || return 1
  cat > "$1/jobs"
  echo 1 > "$1/next"
  : > "$1/lock"
}

queue_size() {   # $1 = queue dir
  local n; n=$(grep -c . "$1/jobs" 2>/dev/null); echo "${n:-0}"
}

# prints the next job and returns 0; returns 1 when every job has been handed out,
# 2 when the queue itself is broken (deleted, unreadable, a disk too full to
# advance `next`). The two must never be confused: a broken queue read as "no
# jobs left" once let a sweep stop early and still call itself done.
queue_claim() {  # $1 = queue dir
  local q="$1" n line fd total
  # (never `exec … 2>/dev/null`: on exec that silences the shell's stderr for good)
  [ -d "$q" ] || { echo "queue: $q is gone" >&2; return 2; }
  exec {fd}>>"$q/lock" || { echo "queue: cannot open $q/lock" >&2; return 2; }
  flock "$fd"
  n=$(cat "$q/next" 2>/dev/null)
  if ! [[ "$n" =~ ^[1-9][0-9]*$ ]] || [ ! -r "$q/jobs" ]; then
    flock -u "$fd"; exec {fd}>&-
    echo "queue: $q is broken (next='${n}')" >&2; return 2
  fi
  total=$(grep -c . "$q/jobs" 2>/dev/null)
  if [ "$n" -gt "${total:-0}" ]; then
    flock -u "$fd"; exec {fd}>&-; return 1                       # all handed out
  fi
  line=$(sed -n "${n}p" "$q/jobs" 2>/dev/null)
  # advance `next` atomically: a failed write (a full disk) leaves the old value,
  # and the job is not handed out, so it can never run twice or go missing
  if [ -z "$line" ] || ! { echo $((n + 1)) > "$q/next.tmp" && mv -f "$q/next.tmp" "$q/next"; } 2>/dev/null; then
    flock -u "$fd"; exec {fd}>&-
    echo "queue: cannot advance $q/next (disk full?)" >&2; return 2
  fi
  flock -u "$fd"; exec {fd}>&-
  printf '%s\n' "$line"
}

append_file() {  # $1 = file, $2 = a file whose content is appended whole, even with many writers
  local fd
  exec {fd}>>"$1.lock" || return 1
  flock "$fd"
  cat "$2" >> "$1" 2>/dev/null
  flock -u "$fd"; exec {fd}>&-
}

append_line() {  # $1 = file, $2 = one line ; appends it whole, even with many writers
  local fd
  exec {fd}>>"$1.lock" || return 1
  flock "$fd"
  printf '%s\n' "$2" >> "$1"
  flock -u "$fd"; exec {fd}>&-
}

# A worker runs agents under `timeout`, which runs checks, which run tests. TERM
# to the worker alone would orphan all of them, still writing into a sandbox that
# is being deleted. So: freeze the whole tree first (a frozen process cannot fork),
# pick up anything forked meanwhile, then TERM everything and let it go.
tree_pids() {    # $1 = pid ; it and all its descendants
  local c
  echo "$1"
  for c in $(pgrep -P "$1" 2>/dev/null); do tree_pids "$c"; done
}

kill_tree() {    # $1 = pid
  local pids more
  pids=$(tree_pids "$1")
  # shellcheck disable=SC2086
  kill -STOP $pids 2>/dev/null
  more=$(for p in $pids; do tree_pids "$p"; done | sort -u)
  # shellcheck disable=SC2086
  kill -STOP $more 2>/dev/null
  # shellcheck disable=SC2086
  kill -TERM $more 2>/dev/null
  # shellcheck disable=SC2086
  kill -CONT $more 2>/dev/null
  true
}
