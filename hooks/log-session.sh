#!/usr/bin/env bash
# Stop hook — one line per session, then get out of the way.
#
# DESIGN RULE: this runs at the end of EVERY session. If it is ever slow or
# noisy you will disable it within a week, and then Cortex has no sensor.
# So: no test runs, metadata only, milliseconds.
#
# That rule used to end "no network, no AI", because an LLM call per session end
# was unaffordable. At ~200 ms and ~$0.0002 it no longer is, so with Jev enabled
# the hook stops guessing from `git status --porcelain | wc -l` and asks the real
# question instead. The rule itself is unchanged and still outranks the feature:
# if the call is disabled, slow, refused or absent, everything below behaves
# exactly as it did before Jev existed — the same line, on the same condition.
#
# Install: see install.sh. Entirely optional — /harvest works without it.
set -uo pipefail

# The hook's hard ceiling. This is a timeout, not an expected duration: a Jev
# answer takes ~200 ms, and this is what stops a hung endpoint from adding
# seconds to every session end. Lower JEV_TIMEOUT_S to lower it further — the
# client takes the smaller of the two.
HOOK_BUDGET_S=5

REPO="${CLAUDE_PROJECT_DIR:-$PWD}"

# Claude Code sends the hook a JSON payload on stdin. Read it before anything
# else can block on it, and never wait on a terminal.
PAYLOAD=""
if [ ! -t 0 ]; then PAYLOAD=$(timeout 2 cat 2>/dev/null || true); fi

[ -d "$REPO/.evolve" ] || exit 0
cd "$REPO" 2>/dev/null || exit 0

# install.sh links `cortex` into ~/.local/bin, so resolve symlinks before
# deriving CORTEX_HOME or every path below breaks.
_self="${BASH_SOURCE[0]}"
while [ -L "$_self" ]; do
  _tgt="$(readlink "$_self")"
  case "$_tgt" in /*) _self="$_tgt" ;; *) _self="$(dirname "$_self")/$_tgt" ;; esac
done
CORTEX_HOME="${CORTEX_HOME:-$(cd "$(dirname "$_self")/.." && pwd)}"
export CORTEX_HOME

DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")

printf '{"t":"%s","branch":"%s","dirty":%s}\n' \
  "$(date -Is)" "$BRANCH" "$DIRTY" >> "$REPO/.evolve/sessions.jsonl" 2>/dev/null

# Nudge only when the session plausibly produced something worth capturing.
# Deliberately does NOT run the test suite: a 2-minute wait at every session
# end is how this feature gets uninstalled.
#
# With Jev on, "plausibly" stops meaning "some file changed":
#   fixed:     did something go from broken to working?
#   corrected: did the user correct the assistant?
# One request, two answers in parallel, over the working tree and the last few
# things the USER said. Above jev.harvest.noul_threshold it nudges; below it, it
# stays silent — the hook's first duty is to never be annoying.
JEV_RC=4
JEV_OUT=""
if [ -f "$CORTEX_HOME/bin/jev.py" ] && command -v python3 >/dev/null 2>&1; then
  TRANSCRIPT=""
  if [ -n "$PAYLOAD" ] && command -v jq >/dev/null 2>&1; then
    TRANSCRIPT=$(printf '%s' "$PAYLOAD" | jq -r '.transcript_path // empty' 2>/dev/null || true)
  fi
  JEV_OUT=$(timeout "$HOOK_BUDGET_S" python3 "$CORTEX_HOME/bin/jev.py" harvest \
              --repo "$REPO" --timeout "$HOOK_BUDGET_S" \
              ${TRANSCRIPT:+--transcript "$TRANSCRIPT"} 2>/dev/null)
  JEV_RC=$?
fi

case "$JEV_RC" in
  0)  [ -n "$JEV_OUT" ] && echo "$JEV_OUT" >&2 ;;      # Jev answered: nudge
  3)  : ;;                                              # Jev answered: nothing to capture
  *)  # Jev is off, refused, slow or absent. Today's behaviour, byte for byte.
      [ "$DIRTY" -gt 0 ] && echo "cortex: uncommitted work — consider /harvest" >&2 ;;
esac
exit 0
