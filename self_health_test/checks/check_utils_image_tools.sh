#!/usr/bin/env bash
# make_thumbnails.py, tag_image.py, classify_images.py — real synthetic run.
set -euo pipefail
REPO="$1"
PY="$REPO/.venv/bin/python3"
TOOL="$REPO/TOOLS/utils_image_tools"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- make_thumbnails.py ---
"$PY" - "$TMP" <<'EOF'
import sys
from PIL import Image
Image.new("RGB", (400, 300), (200, 50, 50)).save(sys.argv[1] + "/sample.jpg")
EOF
"$PY" "$TOOL/make_thumbnails.py" "$TMP"
test -f "$TMP/thumbnails/sample_thumb.jpg"

# --- tag_image.py ---
"$PY" - "$TMP" <<'EOF'
import sys
from PIL import Image
Image.new("RGB", (100, 100), (10, 200, 10)).save(sys.argv[1] + "/tagme.png")
EOF
"$PY" "$TOOL/tag_image.py" "$TMP/tagme.png" testtag anothertag --title "Test" | grep -q "tagged"

# --- classify_images.py (dry-run) ---
cp "$TMP/tagme.png" "$TMP/20260101_120000_test-image.jpg" 2>/dev/null || true
"$PY" - "$TMP" <<'EOF'
import sys
from PIL import Image
Image.new("RGB", (50, 50), (0, 0, 255)).save(sys.argv[1] + "/20260101_120000_test-image.jpg")
EOF
cat > "$TMP/classif.md" <<'MD'
| Original filename | Category | Proposed filename | Confidence |
|---|---|---|---|
| 20260101_120000_test-image.jpg | TestCat | 20260101_120000_test-image.jpg | High |
MD
"$PY" "$TOOL/classify_images.py" classif.md --dry-run --workdir "$TMP" | grep -q "1 succeeded"

echo "utils_image_tools: OK (thumbnail, tag, dry-run classify all ran)"
