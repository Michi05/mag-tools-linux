# self_health_test

Basic health-check harness for every tool in this repo. Run after any tool
change to confirm nothing is broken; `results.md` records the last run.

## Usage

```
./run_all.sh        # summary only
./run_all.sh -v      # also show each check's output
```

Exits 0 if every check passes, 1 if any fail.

## What "pass" means, per tier

Checks live in `checks/check_<tool>.sh`, one per tool, each taking the repo
root as `$1` and exiting 0/1. What each one actually verifies differs by
tool tier — a check script's job is to assert the *right* thing for that
tool, not just to run it and shrug at the exit code:

- **Lightweight tools** (image tools, HTML/QR/similarity scripts, session
  finder, obsidian clipper, image stacking): a real synthetic run — generate
  tiny fixture input, run the tool, assert on real output content. These are
  full functional smoke tests, not just "did it crash."
- **Heavy ML tools** (`ai_whisper_transcription`, `ai_screenshot_ocr`,
  `video_ai_upscale`): their model/binary downloads are deliberately
  deferred (see `docs/porting-notes.md`), so a check here proves the CLI
  works — `--help` succeeds with **zero** heavy deps installed (this is why
  both scripts' heavy imports are deferred into `main()`, after argparse,
  rather than at module scope), and a real invocation attempt fails with the
  documented graceful setup-instructions message, not a raw traceback. Full
  inference is NOT exercised — run each tool's own `setup.sh` first if you
  want that.
- **Static/doc-only tools** (`browser_youtubewl_cleaner`,
  `data_btc_nasdaq_correlation`, `utils_hydrate_onedrive`): file
  existence/well-formedness, or (for `utils_hydrate_onedrive`) that the
  README actually documents why there's no script.
- **System-binary tools** (`video_yt_dlp`, `vpn_wireguard`,
  `mag_vid_compress`): confirm the expected system binary/encoder is present
  and runs, since these have no bundled code of their own to unit-test.

## Adding a check for a new tool

Copy the closest existing `checks/check_*.sh` as a template. Keep it
self-contained (own temp dir, cleans up after itself via `trap`) and make it
assert something meaningful about that specific tool's behavior — not just
"the command didn't crash."
