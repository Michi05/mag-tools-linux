#!/usr/bin/env bash
# Finds files whose name contains a given substring.
# Linux port of FindFilesByName.ps1 (which wrapped Get-ChildItem) — here it's
# a thin wrapper around `find`, which already does this natively; the wrapper
# just gives matching CLI ergonomics (-SearchString/-Path/-Recurse) and the
# same "no matches" messaging.
#
# Usage: ./find_files.sh -s SEARCH_STRING [-p PATH] [-r]

set -euo pipefail

usage() {
    echo "Usage: $0 -s SEARCH_STRING [-p PATH] [-r]"
    echo "  -s  Substring to match in filename (required)"
    echo "  -p  Directory to search (default: current directory)"
    echo "  -r  Search recursively through subdirectories (default: current dir only)"
    exit 1
}

SEARCH_STRING=""
SEARCH_PATH="."
RECURSE=0

while getopts "s:p:rh" opt; do
    case "$opt" in
        s) SEARCH_STRING="$OPTARG" ;;
        p) SEARCH_PATH="$OPTARG" ;;
        r) RECURSE=1 ;;
        h|*) usage ;;
    esac
done

[[ -z "$SEARCH_STRING" ]] && usage

echo "Searching for files containing '$SEARCH_STRING' in their name..."
echo "Search location: $SEARCH_PATH"
[[ "$RECURSE" -eq 1 ]] && echo "Searching recursively through subdirectories."
echo

if [[ "$RECURSE" -eq 1 ]]; then
    MAXDEPTH_ARGS=()
else
    MAXDEPTH_ARGS=(-maxdepth 1)
fi

mapfile -t RESULTS < <(find "$SEARCH_PATH" "${MAXDEPTH_ARGS[@]}" -type f -iname "*${SEARCH_STRING}*" 2>/dev/null)

if [[ "${#RESULTS[@]}" -eq 0 ]]; then
    echo "No files found containing '$SEARCH_STRING' in their name."
else
    echo "Found ${#RESULTS[@]} file(s):"
    for f in "${RESULTS[@]}"; do
        echo "  $(realpath "$f")"
    done
fi
