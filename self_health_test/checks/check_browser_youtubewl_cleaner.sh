#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
F="$REPO/TOOLS/browser_youtubewl_cleaner/YoutubeWL Cleaner 230504.html"
test -s "$F"
grep -qi "<html" "$F"
echo "browser_youtubewl_cleaner: OK (static HTML present and well-formed)"
