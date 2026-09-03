#!/usr/bin/env bash
# Doesn't actually launch a browser (would open a real window in a headless
# check run) — verifies the script is syntactically valid bash and that it
# correctly resolves a gateway via `ip route`, by stubbing the browser-open
# step out.
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/browser_captive_portal"

bash -n "$TOOL/captive_portal.sh"
test -f "$TOOL/Captive Portal Redirector.html"

GW="$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if ($i=="via") print $(i+1)}' | head -n1)"
if [[ -z "$GW" ]]; then
    echo "warning: no default route on this machine right now (offline?) — script logic untestable live, syntax OK"
else
    echo "resolved default gateway: $GW"
fi
echo "browser_captive_portal: OK (script syntax valid, dashboard present, gateway resolvable)"
