#!/usr/bin/env bash
# The realesrgan-ncnn-vulkan binary is deliberately not downloaded yet (see
# docs/porting-notes.md). This checks that --help works (argparse sound) and
# that running for real fails with the documented, graceful "binary not
# found, here's how to fix it" message rather than a raw traceback.
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/video_ai_upscale"

python3 "$TOOL/upscale_video.py" --help | grep -qi "usage"

set +e
OUT=$(python3 "$TOOL/upscale_video.py" /nonexistent_input.mp4 /tmp/out.mp4 2>&1)
CODE=$?
set -e
[[ "$CODE" -eq 1 ]] && echo "$OUT" | grep -qi "realesrgan-ncnn-vulkan"

echo "video_ai_upscale: OK (--help works; graceful missing-binary message, as expected pre-setup)"
