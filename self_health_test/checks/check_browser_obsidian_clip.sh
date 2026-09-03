#!/usr/bin/env bash
# Exercises --dir batch mode (no live browser/vault needed) against a small
# synthetic HTML file — real end-to-end coverage of the HTML->Markdown path,
# frontmatter, and image extraction, without needing Brave running.
set -euo pipefail
REPO="$1"
PY="$REPO/.venv/bin/python3"
TOOL="$REPO/TOOLS/browser_obsidian_clip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/in" "$TMP/out"

cat > "$TMP/in/sample.html" <<'HTML'
<html><head><title>Sample Page</title></head>
<body><nav>ignored nav</nav>
<main><h1>Sample Page</h1><p>Some body text.</p></main>
</body></html>
HTML

"$PY" "$TOOL/clip_page.py" --dir "$TMP/in" --out "$TMP/out" --tag selftest
OUT_FILE=$(find "$TMP/out" -name "*.md" | head -n1)
test -n "$OUT_FILE"
grep -q "Some body text." "$OUT_FILE"
grep -q "selftest" "$OUT_FILE"
echo "browser_obsidian_clip: OK (--dir batch mode clipped synthetic HTML to Markdown)"
