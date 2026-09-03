#!/usr/bin/env bash
# Resolves the current default gateway IP and opens the Captive Portal
# Redirector dashboard in the browser, pre-loaded with that gateway.
#
# Linux port of the original MAG - Captive Portals.ps1 (which used
# Get-NetRoute / ipconfig to find the gateway and Start-Process chrome.exe
# to open it). Here: `ip route` for the gateway, and whichever browser is
# actually installed (this machine has Brave, not Chrome) via xdg-open.
#
# Usage: ./captive_portal.sh [html_file]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HTML_FILE="${1:-Captive Portal Redirector.html}"
HTML_PATH="$SCRIPT_DIR/$HTML_FILE"

if [[ ! -f "$HTML_PATH" ]]; then
    echo "Error: dashboard not found: $HTML_PATH" >&2
    exit 1
fi

# Default gateway for the route actually used to reach the internet (metric-lowest default route).
GW="$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if ($i=="via") print $(i+1)}' | head -n1)"

if [[ -n "${GW:-}" ]]; then
    URL="file://$HTML_PATH?gw=$GW"
else
    echo "Warning: could not determine default gateway; opening without ?gw=" >&2
    URL="file://$HTML_PATH"
fi

open_url() {
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$1" >/dev/null 2>&1 &
    elif command -v brave-browser >/dev/null 2>&1; then
        brave-browser "$1" >/dev/null 2>&1 &
    elif command -v firefox >/dev/null 2>&1; then
        firefox "$1" >/dev/null 2>&1 &
    else
        echo "Error: no xdg-open/brave-browser/firefox found to open the page." >&2
        exit 1
    fi
}

open_url "$URL"
echo "Opened: $URL"
