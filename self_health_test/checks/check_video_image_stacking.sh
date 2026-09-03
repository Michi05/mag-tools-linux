#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
PY="$REPO/.venv/bin/python3"
TOOL="$REPO/TOOLS/video_image_stacking"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$PY" "$TOOL/auto_stack.py" "$TOOL/images" "$TMP/out_orb.jpg" --method ORB
test -f "$TMP/out_orb.jpg"
echo "video_image_stacking: OK (ORB stack of 3 sample images produced output)"
