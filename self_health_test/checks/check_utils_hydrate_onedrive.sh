#!/usr/bin/env bash
# Not ported (see the tool's README) — the only thing to check is that the
# README actually documents that decision, so a future reader isn't left
# wondering why the folder has no script.
set -euo pipefail
REPO="$1"
F="$REPO/TOOLS/utils_hydrate_onedrive/README.md"
test -s "$F"
grep -qi "not ported" "$F"
echo "utils_hydrate_onedrive: OK (documented as not-applicable, as intended)"
