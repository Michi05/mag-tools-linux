#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
PY="$REPO/.venv/bin/python3"
TOOL="$REPO/TOOLS/utils_html_to_text"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/sample.html" <<'HTML'
<html><body><p>Hello world.</p><script>ignored()</script><p>Second paragraph.</p></body></html>
HTML

OUT=$("$PY" "$TOOL/html_to_text.py" "$TMP/sample.html")
echo "$OUT" | grep -q "Hello world."
echo "$OUT" | grep -q "Second paragraph."
echo "utils_html_to_text: OK"
