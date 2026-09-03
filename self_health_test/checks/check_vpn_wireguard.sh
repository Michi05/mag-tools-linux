#!/usr/bin/env bash
set -euo pipefail
REPO="$1"
TOOL="$REPO/TOOLS/vpn_wireguard"
bash -n "$TOOL/vpn_setup.sh"
test -s "$TOOL/docker-compose.yaml"
grep -q "linuxserver/wireguard" "$TOOL/docker-compose.yaml"
echo "vpn_wireguard: OK (setup script syntax valid, compose file present)"
