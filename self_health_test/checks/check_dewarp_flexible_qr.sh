#!/usr/bin/env bash
# No real wrinkled-QR photo is available as a repo fixture, so this checks
# --help (CLI/imports sound) and a real synthetic-image run through the full
# segment->contour->TPS pipeline (expected to gracefully report "no panel
# found" on a plain image with no HSV-contrasted panel — that IS the correct
# behavior, not a bug, so we assert on the graceful message, not on success).
set -euo pipefail
REPO="$1"
PY="$REPO/.venv/bin/python3"
TOOL="$REPO/TOOLS/dewarp_flexible_qr"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$PY" "$TOOL/dewarp_flexible_qr.py" --help | grep -qi "usage"

"$PY" - "$TMP" <<'EOF'
import sys
from PIL import Image
Image.new("RGB", (200, 200), (128, 128, 128)).save(sys.argv[1] + "/flat.jpg")
EOF

set +e
OUT=$("$PY" "$TOOL/dewarp_flexible_qr.py" "$TMP/flat.jpg" 2>&1)
CODE=$?
set -e
[[ "$CODE" -eq 2 ]] && echo "$OUT" | grep -qi "segmentation/corner detection failed"

echo "dewarp_flexible_qr: OK (--help works; correctly rejects a panel-less image)"
