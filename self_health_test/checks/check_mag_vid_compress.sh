#!/usr/bin/env bash
# Slash-command skill, not a TOOLS/ folder — checks the two things the skill
# doc claims: ffmpeg is present, and at least one hardware AV1 encoder
# (av1_qsv or av1_nvenc) is available, matching what CLAUDE.md/TOOLS.md say
# about this machine.
set -euo pipefail
command -v ffmpeg >/dev/null
ENCODERS=$(ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "av1_(qsv|nvenc|vaapi)" || true)
[[ -n "$ENCODERS" ]]
echo "$ENCODERS"
echo "mag_vid_compress: OK (ffmpeg present with at least one hardware AV1 encoder)"
