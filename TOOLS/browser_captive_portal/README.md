# browser_captive_portal

Resolves the current default gateway IP and opens the **Captive Portal
Redirector** dashboard in the browser — it probes plain-HTTP connectivity
URLs and opens the first reachable one in a new tab, for captive-portal
logins (hotel/airport Wi-Fi). The gateway is tried first, then
`neverssl.com` → `httpforever.com` → `captive.apple.com` → `generate_204`.

Ported from `MAG - Captive Portals.ps1` (`Get-NetRoute`/`ipconfig` +
`Start-Process chrome.exe`) to bash (`ip route` + `xdg-open`, falling back to
`brave-browser`/`firefox` directly — this machine has Brave and Firefox, no
Chrome).

## Usage

```
./captive_portal.sh
```

**Parameters:** optional positional arg — dashboard filename to open
(defaults to `Captive Portal Redirector.html`), in case it's ever renamed.
Errors out if the file doesn't exist.

**Output:** Opens the default browser at the dashboard, pre-loaded with the
gateway candidate. The dashboard can also be opened directly (no gateway
row) via `xdg-open "Captive Portal Redirector.html"`.

## Requirements

`ip` (iproute2, standard on Linux Mint) and one of `xdg-open` / `brave-browser`
/ `firefox` on PATH.
