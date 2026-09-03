#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
F="$REPO/TOOLS/data_btc_nasdaq_correlation/bitcoin_vs_nasdaq.html"
J="$REPO/TOOLS/data_btc_nasdaq_correlation/ndx_weekly.json"
test -s "$F"
test -s "$J"
python3 -c "import json; json.load(open('$J'))"
echo "data_btc_nasdaq_correlation: OK (HTML present, JSON parses)"
