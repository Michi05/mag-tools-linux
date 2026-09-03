# utils_hydrate_onedrive — not ported (no Linux equivalent problem)

The Windows tool worked around a specific OneDrive-for-Windows behavior:
cloud-only "Files On-Demand" placeholder files that show up in the filesystem
but have no local bytes until something reads them, which silently breaks
downstream tools (ffmpeg, whisper, etc.) that expect a real file.

**That specific problem doesn't exist on Linux the same way.** There's no
official OneDrive client here, and this machine doesn't have one installed
(checked: no `onedrive` package, no rclone mount). The two realistic ways to
get OneDrive files onto this box each have a different (non-)placeholder
model:

- **[abraunegg/onedrive](https://github.com/abraunegg/onedrive)** (the
  de facto Linux OneDrive client) syncs real files by default — no
  placeholder/hydration step needed. It optionally supports an on-demand
  mode (`--download-only` is the opposite; on-demand hydration is a newer,
  less mature feature), but the default sync path never needs "hydrating."
- **rclone mount** (`rclone mount onedrive: ~/OneDrive --vfs-cache-mode full`)
  fetches file bytes lazily on first read, similar in spirit to Windows'
  placeholders — but the fix is the same trick (read the file once), so if
  you go this route the old script's *logic* (open each file, read a few
  bytes) still applies; only the detection of "is this a placeholder" would
  need rewriting (no `ReparsePoint`/`FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`
  attributes on Linux — you'd check `st_blocks == 0` on a sparse rclone VFS
  cache file instead, which is fragile and cache-mode-dependent).

**Recommendation:** don't port this speculatively. If OneDrive sync becomes
a real need on this machine, decide the sync method first (abraunegg client
vs. rclone mount) — the right fix depends entirely on which one, and forcing
today's Windows-shaped script onto either would be guessing at a problem
that may not even occur with the default sync-not-mount approach.
