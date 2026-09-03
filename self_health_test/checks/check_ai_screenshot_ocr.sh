#!/usr/bin/env bash
# openvino-genai is deliberately not installed yet (own .venv + setup.sh,
# not run as part of this build — see docs/porting-notes.md). This checks
# that --help works using plain system python3 with NO deps installed
# (this required moving the heavy imports out of module scope and into
# main(), after argparse — see docs/porting-notes.md / git history), plus
# the graceful missing-dependency message on a real invocation attempt.
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/ai_screenshot_ocr"

python3 "$TOOL/screenshot_metadata.py" --help | grep -qi "usage"

set +e
OUT=$(python3 "$TOOL/screenshot_metadata.py" -i /nonexistent.png 2>&1)
CODE=$?
set -e
[[ "$CODE" -ne 0 ]] && echo "$OUT" | grep -qi "MISSING DEPENDENCIES"

echo "ai_screenshot_ocr: OK (--help works with zero deps installed; graceful missing-dep message)"
