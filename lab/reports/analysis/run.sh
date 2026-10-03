#!/usr/bin/env bash
# run.sh — rebuild every table and figure from reports/data/, offline.
#
#   lab/reports/analysis/run.sh
#
# It needs no API key, no network and no Cortex: everything comes from the JSONL
# rows shipped beside it. That is the part of this work a reviewer is most likely
# to try, so it is the part that has to work on a machine that has never seen
# this project.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${CORTEX_ANALYSIS_VENV:-$HERE/.venv}"

if [ ! -x "$VENV/bin/python" ]; then
  echo "creating $VENV"
  if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV" >/dev/null
    uv pip install --python "$VENV/bin/python" -r "$HERE/requirements.txt" >/dev/null
  else
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --quiet -r "$HERE/requirements.txt"
  fi
fi
exec "$VENV/bin/python" "$HERE/rebuild.py" "$@"
