#!/usr/bin/env bash
set -euo pipefail
command -v yt-dlp >/dev/null
yt-dlp --version
echo "video_yt_dlp: OK (system binary present and runs)"
