#!/usr/bin/env bash
# faster-whisper is deliberately not installed yet (own .venv + setup.sh,
# not run as part of this build — see docs/porting-notes.md). This checks
# that --help works using plain system python3 with NO deps installed,
# proving the deferred-import structure actually works, plus the graceful
# missing-dependency message on a real invocation attempt.
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/ai_whisper_transcription"

python3 "$TOOL/whisper_video_transcriber.py" --help | grep -qi "usage"

set +e
OUT=$(python3 "$TOOL/whisper_video_transcriber.py" -a /nonexistent.wav 2>&1)
CODE=$?
set -e
[[ "$CODE" -ne 0 ]] && echo "$OUT" | grep -qi "faster-whisper"

echo "ai_whisper_transcription: OK (--help works with zero deps installed; graceful missing-dep message)"
