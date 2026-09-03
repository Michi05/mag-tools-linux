# vpn_wireguard

Configuration files and setup notes for a self-hosted WireGuard VPN running
as a Docker container on UpCloud. The server side is already Linux (the
`linuxserver/wireguard` image), so `docker-compose.yaml` and `vpn_setup.sh`
are unchanged from the Windows repo — nothing there was ever Windows-specific.

What changes on this machine is the **client** side: connecting *to* the VPN.

## Quick reconnect (server already running)

```sh
ssh root@<server-ip>
cd /root/wireguard && docker compose start   # or docker-compose, see note below
```

## Connecting from this Linux client

The Windows repo assumed the WireGuard Windows GUI client for importing a
peer config. On Linux, either of these works:

**Option A — NetworkManager (nmcli), no extra install:**
```sh
nmcli connection import type wireguard file peers/peer1/peer1.conf
nmcli connection up peer1
```

**Option B — wg-quick (needs `wireguard-tools`):**
```sh
sudo apt install wireguard-tools
sudo cp peers/peer1/peer1.conf /etc/wireguard/wg0.conf
sudo wg-quick up wg0
```

Import the peer config from `docker-compose logs` (QR code) or from
`peers/peer1/` on the server. Verify the tunnel at https://iplocation.io.

## Note on `docker-compose` vs `docker compose`

This machine does not have Docker installed at all yet (checked:
`docker`/`docker-compose` not on PATH) — Docker only runs server-side, so
nothing here needs it unless you're standing up the server itself from this
machine. If you do: modern Debian/Ubuntu ship the `docker-compose-plugin`
(invoked as `docker compose`, no hyphen) rather than the standalone
`docker-compose` binary the original `vpn_setup.sh` installs via
`apt-get install docker-compose`. Both work; prefer the plugin form if
setting this up fresh:
```sh
sudo apt-get install docker.io docker-compose-plugin
docker compose up -d
```

## Files

- `docker-compose.yaml` — Docker stack definition (server-side, unchanged)
- `vpn_setup.sh` — init script for a new server (server-side, unchanged)
- `WireGuard VPN @UpCloud -- Notes.md` — full deployment walkthrough
- `ROTATE_WIREGUARD_KEY.md` — key rotation procedure

**Secrets:** the original repo kept `id_rsa.ppk` (PuTTY-format SSH key) and a
`putty.log` out of the tool folder in `_local_only/wireguard/`. PuTTY is
Windows-only — on Linux, use a standard OpenSSH private key instead (`ssh
root@<server-ip>` needs no PuTTY conversion). Keep any private key out of
this repo; `.gitignore` excludes a `_local_only/` folder here too if you want
to mirror that pattern.
