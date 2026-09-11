#!/usr/bin/env bash
# Slash-command skill, not a TOOLS/ folder — checks the two things the skill
# doc claims: ffmpeg is present, and at least one hardware HEVC encoder
# (hevc_qsv or hevc_nvenc) is available, matching what CLAUDE.md/TOOLS.md say
# about this machine's default GPU encode path. AV1 hardware (av1_qsv/
# av1_nvenc) is NOT checked here — both are compiled into ffmpeg but
# confirmed non-functional on this machine's silicon (see TOOLS.md pitfall);
# CPU libsvtav1 is the AV1 fallback and needs no hardware check.
set -euo pipefail
command -v ffmpeg >/dev/null
ENCODERS=$(ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "hevc_(qsv|nvenc|vaapi)" || true)
[[ -n "$ENCODERS" ]]
echo "$ENCODERS"
echo "mag_vid_compress: OK (ffmpeg present with at least one hardware HEVC encoder)"
