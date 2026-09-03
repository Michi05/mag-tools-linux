#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
PY="$REPO/.venv/bin/python3"
TOOL="$REPO/TOOLS/media_pic_similarity_match"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$PY" - "$TMP" <<'EOF'
import sys
from PIL import Image
Image.new("RGB", (100, 100), (200, 30, 30)).save(sys.argv[1] + "/a.jpg")
Image.new("RGB", (100, 100), (205, 32, 28)).save(sys.argv[1] + "/b.jpg")
Image.new("RGB", (100, 100), (10, 30, 200)).save(sys.argv[1] + "/c.jpg")
EOF

OUT=$("$PY" "$TOOL/similar_pic_matcher.py" "$TMP" --all)
echo "$OUT" | grep -q "Comparing 3 images"
echo "$OUT" | grep -q "Nearest match per image"
echo "media_pic_similarity_match: OK"
