# Porting notes — mag-tools → mag-tools-linux

Source repo: `../mag-tools` (Windows-targeted). This repo is a from-scratch
build for this Linux Mint machine, not a copy — see `CLAUDE.md` for the
target hardware.

## Problems found in the source repo, and how this repo avoids them

1. **`.gitignore` blocked everything by default** (`# Ignore everything` /
   `/*` then re-allow only directories and `*.md`), so every real script had
   to be force-added — fragile, and a likely contributor to the next problem.
   Fixed here with a normal deny-list `.gitignore` (venvs, caches, models,
   secrets) that tracks source files by default.
2. **A tool folder (`dewarp_flexible_qr`) was committed in two places at
   once** — root and `TOOLS/`. Every tool here has exactly one canonical
   location.
3. **A folder name had a space in it** (`BTC-Nasdaq correlation`), fragile
   for shell scripting. Renamed to `data_btc_nasdaq_correlation` here.
4. **Some tool folders didn't follow the documented `<category>_<name>`
   naming convention** (`AI02_LocalCaptureOCR`, `media_pic_similarity_match`,
   `dewarp_flexible_qr` lacked a recognized prefix). Every folder here uses
   `ai_`/`video_`/`browser_`/`utils_`/`media_`/`vpn_`/`data_`.
5. **`TOOLS.md` and the actual folder disagreed** after a manual rename
   (`ai_screenshot_ocr` renamed to `AI02_LocalCaptureOCR` on disk, but
   `TOOLS.md`'s own section body still said `TOOLS/ai_screenshot_ocr/`).
   This repo generated `TOOLS.md` from the final folder layout, not the
   other way around, specifically to avoid this drift.
6. **`CLAUDE.md` described folders that didn't exist in this checkout**
   (`_pending_review/`, `Archive/`, `WiFi dongles/`, `Run-MAGTool.ps1`) —
   real on the Windows machine, absent here, and `CLAUDE.md` didn't say so.
   This repo's `CLAUDE.md` only describes what actually exists.

## Hardware-driven redesigns (not just OS translation)

- **ai_whisper_transcription**: the source tool targets an Intel NPU via
  OpenVINO GenAI. This machine (11th-gen Intel, TigerLake) has no NPU — NPU
  support only shipped from Meteor Lake onward. It does have an NVIDIA RTX
  3060 the Windows machine doesn't. Rebuilt on faster-whisper (CTranslate2)
  targeting CUDA, not ported as OpenVINO/NPU code that would never load.
- **ai_screenshot_ocr**: kept its original OpenVINO GenAI engine — this
  machine's Intel Iris Xe iGPU is exactly the device class OpenVINO's GPU
  plugin already targeted, and that plugin works on Linux. Only the install
  instructions changed (venv/pip, `intel-opencl-icd` instead of a Windows
  driver update).
- **video_ai_upscale**: needs the Linux build of `realesrgan-ncnn-vulkan`
  (same upstream project, different binary) — logic unchanged.
- **utils_hydrate_onedrive**: not ported. The Windows-placeholder-hydration
  problem doesn't exist in the same shape on Linux (no OneDrive client
  installed; the two realistic options — abraunegg client vs. rclone mount —
  have different, non-analogous file-materialization models). See that
  tool's own README for the full reasoning.
- **browser_captive_portal / browser_obsidian_clip**: this machine has Brave
  and Firefox, not Chrome. Captive-portal opening uses `xdg-open` with a
  Brave/Firefox fallback chain. Obsidian clipping's live-tab (CDP) mode
  needs a Chromium-family browser specifically — pointed at Brave.

## Scope of this initial build

Per an explicit choice made when this repo was created: the lightweight,
dependency-light tools (image tools, HTML/QR/similarity scripts, session
finder, WireGuard docs, browser automation) were built and smoke-tested in
full. The three heavy-ML tools (Whisper transcription, screenshot VLM OCR,
video upscaling) were fully coded and documented but their multi-GB
model/dependency downloads were deliberately deferred — each has a
`setup.sh` to run when you're ready to pull that download. See
`self_health_test/results.md` for what was actually verified to run, versus
what's expected to work once its setup step is run.
