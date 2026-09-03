#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/utils_findfiles"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

touch "$TMP/report_january.txt" "$TMP/other.txt"

OUT=$("$TOOL/find_files.sh" -s report -p "$TMP")
echo "$OUT" | grep -q "report_january.txt"
! echo "$OUT" | grep -q "other.txt"
echo "utils_findfiles: OK"
