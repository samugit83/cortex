#!/usr/bin/env bash
# Stop hook — one line per session, then get out of the way.
#
# DESIGN RULE: this runs at the end of EVERY session. If it is ever slow or
# noisy you will disable it within a week, and then Cortex has no sensor.
# So: no test runs, no network, no AI. Metadata only, milliseconds.
#
# Install: see install.sh. Entirely optional — /harvest works without it.
set -uo pipefail
REPO="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -d "$REPO/.evolve" ] || exit 0
cd "$REPO" 2>/dev/null || exit 0

DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")

printf '{"t":"%s","branch":"%s","dirty":%s}\n' \
  "$(date -Is)" "$BRANCH" "$DIRTY" >> "$REPO/.evolve/sessions.jsonl" 2>/dev/null

# Nudge only when the session plausibly produced something worth capturing.
# Deliberately does NOT run the test suite: a 2-minute wait at every session
# end is how this feature gets uninstalled.
[ "$DIRTY" -gt 0 ] && echo "cortex: uncommitted work — consider /harvest" >&2
exit 0
