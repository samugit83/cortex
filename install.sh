#!/usr/bin/env bash
# install.sh — put `cortex` on PATH and optionally register the Stop hook.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${HOME}/.local/bin"

mkdir -p "$BIN"
ln -sf "$HERE/bin/cortex" "$BIN/cortex"
echo "linked $BIN/cortex -> $HERE/bin/cortex"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo ""
     echo "  WARNING: $BIN is not on your PATH. Add to ~/.bashrc:"
     echo "    export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

echo ""
"$HERE/bin/cortex" doctor || true

cat <<NEXT

Next steps
  1. cd into a repo you actually work in
  2. cortex init
  3. work normally, then run /harvest before closing the session
  4. after ~5 harvested tasks, run /evolve

Optional — register the Stop hook so sessions are logged automatically.
Add to ~/.claude/settings.json (or the project's .claude/settings.json):

  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command",
                     "command": "$HERE/hooks/log-session.sh" } ] }
    ]
  }

That path is already filled in above. The hook is optional — /harvest works
without it; the hook only adds a one-line session record and a nudge.
NEXT
