#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/ai_session_finder"

# stdlib only — plain system python3, no venv needed.
OUT=$(python3 "$TOOL/build_index.py" --search "__no_such_session_should_exist__")
echo "$OUT" | grep -q "No sessions matched"

# Real-world search: this very session is a claude-code session whose
# project folder encodes "mag-tools" (search matches folder text, not the
# tool-name column), so this should find at least one match if
# ~/.claude/projects exists on this machine.
if [[ -d "$HOME/.claude/projects" ]]; then
    OUT2=$(python3 "$TOOL/build_index.py" --search "mag-tools")
    echo "$OUT2" | grep -q "match(es)"
fi

echo "ai_session_finder: OK (stdlib-only search mode works)"
