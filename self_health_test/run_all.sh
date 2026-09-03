#!/usr/bin/env bash
# Basic health check for every tool in this repo.
#
# "Pass" means different things per tool tier (documented per-row in
# results.md and in each check_*.sh):
#   - lightweight tools: an actual synthetic run, checking real output.
#   - heavy ML tools (whisper/screenshot-ocr): argparse/--help succeeds
#     without the heavy deps installed (proves the CLI and lazy-import
#     structure are sound) — full inference is NOT exercised here, since
#     that needs a setup.sh run + multi-GB model download (deliberately
#     deferred, see docs/porting-notes.md).
#   - static/doc-only tools: file existence + (for HTML) well-formedness.
#
# Usage: ./run_all.sh          # run every check, print PASS/FAIL summary
#        ./run_all.sh -v       # also show each check's raw output

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd .. && pwd)"
VERBOSE=0
[[ "${1:-}" == "-v" ]] && VERBOSE=1

PASS=0
FAIL=0
RESULTS=()

run_check() {
    local name="$1"
    local script="$2"
    echo -n "[ ] $name ... "
    local out
    if out=$(bash "$script" "$REPO_ROOT" 2>&1); then
        echo "PASS"
        PASS=$((PASS+1))
        RESULTS+=("PASS  $name")
    else
        echo "FAIL"
        FAIL=$((FAIL+1))
        RESULTS+=("FAIL  $name")
    fi
    if [[ "$VERBOSE" -eq 1 ]]; then
        echo "$out" | sed 's/^/      /'
    fi
}

for check in checks/check_*.sh; do
    name="$(basename "$check" .sh)"
    name="${name#check_}"
    run_check "$name" "$check"
done

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
printf '%s\n' "${RESULTS[@]}"

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
