# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Context

This is a personal tools folder — the Linux counterpart to `mag-tools`
(the original Windows repo, at `../mag-tools` on this machine). The role here
is to **run tools on behalf of the user**, not develop them. Read code only
when you need to clarify usage.

Full tool profiles (options, outputs, requirements) are in
[`TOOLS.md`](TOOLS.md).

## Machine this repo targets

Linux Mint 22.3, Intel Core i7-11370H (TigerLake, **no NPU** — NPU support
only shipped from Meteor Lake onward), Intel Iris Xe iGPU, NVIDIA RTX 3060
Mobile (6GB VRAM, CUDA). Browsers: Brave and Firefox (no Chrome). This is
**different hardware** from the Windows machine `mag-tools` targets, not just
a different OS — some tools were redesigned around what's actually here
(e.g. Whisper transcription uses CUDA via faster-whisper instead of trying to
reproduce an NPU pipeline this machine can't run), not just translated
line-by-line. Each tool's README says which case it is.

## Folder structure

- `TOOLS/<category>_<name>/` — every tool, one folder each, category-prefixed
  (`ai_`, `video_`, `browser_`, `utils_`, `media_`, `vpn_`, `data_`). This is
  where to look for a tool's actual files. No tool folder has spaces in its
  name and none exist in more than one location — both were real problems in
  the Windows repo (a `BTC-Nasdaq correlation` folder with a space, and a
  `dewarp_flexible_qr` folder committed in two places at once).
- `docs/` — porting notes and other non-tool reference material.
- `self_health_test/` — smoke-test harness that exercises every tool at a
  basic level (imports resolve, `--help` works, a tiny synthetic input runs
  end-to-end where that's cheap to do). Run `self_health_test/run_all.sh`
  after any tool change; see its README for what "pass" means per tool.
- `CLAUDE.md`, `TOOLS.md`, `README.md` — stay at root. `TOOLS.md` is read
  from the current working directory by the `/run-tool` skill.

There is no `_pending_review/`, `_local_only/`, `Archive/`, or
`WiFi dongles/` here (yet) — those existed in the Windows repo for
machine-specific secrets and cold storage that doesn't apply to this fresh
checkout. If/when secrets show up (SSH keys, tokens), put them in
`_local_only/` and keep `.gitignore`'s existing exclusion for it; don't
invent the other folders speculatively.

## Tools at a glance

| Tool | Location | What it does |
|------|----------|--------------|
| `yt-dlp` | `TOOLS/video_yt_dlp/` (system package, no bundled binary) | Download video/audio from YouTube and other sites |
| `captive_portal.sh` | `TOOLS/browser_captive_portal/` | Open captive portal login page in the default browser |
| `find_files.sh` | `TOOLS/utils_findfiles/` | Search files by name substring |
| `Hydrate-OneDrive` | **not ported** — `TOOLS/utils_hydrate_onedrive/README.md` explains why | N/A on this machine (no OneDrive client installed) |
| `whisper_video_transcriber.py` | `TOOLS/ai_whisper_transcription/` | Transcribe video/audio locally (faster-whisper, CUDA/CPU, batch-capable) |
| `screenshot_metadata.py` | `TOOLS/ai_screenshot_ocr/` | Analyze/label screenshots locally (InternVL2 VLM via OpenVINO GPU) |
| `auto_stack.py` | `TOOLS/video_image_stacking/` | Stack photos to reduce noise (ORB, ECC, or optical-flow) |
| `upscale_video.py` | `TOOLS/video_ai_upscale/` | AI video upscaling (Real-ESRGAN ncnn-vulkan) |
| `YoutubeWL Cleaner 230504.html` | `TOOLS/browser_youtubewl_cleaner/` | YouTube Watch Later cleaner (open in browser) |
| `clip_page.py` | `TOOLS/browser_obsidian_clip/` | Browser-CDP page clipper → Markdown → Obsidian vault |
| `classify_images.py`, `make_thumbnails.py`, `tag_image.py` | `TOOLS/utils_image_tools/` | Bulk photo classify/rename/tag, thumbnail generation, PNG XMP tagging |
| `html_to_text.py` | `TOOLS/utils_html_to_text/` | Strip HTML to plain text (paragraph text only) |
| `build_index.py` | `TOOLS/ai_session_finder/` | Find past claude/opencode/copilot sessions (`--search <term>` returns plain text; bare run refreshes the `.html`) |
| `similar_pic_matcher.py` | `TOOLS/media_pic_similarity_match/` | Find visually similar images by color palette |
| `dewarp_flexible_qr.py` | `TOOLS/dewarp_flexible_qr/` | Dewarp QR/barcodes photographed on wrinkled flexible surfaces |
| `bitcoin_vs_nasdaq.html` | `TOOLS/data_btc_nasdaq_correlation/` | Static BTC/Nasdaq correlation chart |
| WireGuard config/notes | `TOOLS/vpn_wireguard/` | Self-hosted VPN on UpCloud — setup/reconnect |

Also available via slash command (not a `TOOLS/` folder): `/mag_vid_compress`
— FFmpeg screen-recording compression, hardware AV1 (QSV or NVENC, both
confirmed available on this machine).

## Important notes

- **ai_whisper_transcription** and **ai_screenshot_ocr** each use their own
  `.venv/` (create with each tool's `setup.sh`) — heavier/conflicting deps
  (CUDA stack vs. OpenVINO stack) don't share an environment. Neither venv
  nor the models they download are committed to git (see `.gitignore`);
  run `setup.sh` yourself before first use.
- **video_ai_upscale** needs a Linux `realesrgan-ncnn-vulkan` binary + its
  `models/` folder placed in that tool's directory — not included in this
  repo (binary, and large); see that tool's README for the download step.
- **yt-dlp** is the apt-installed system package (`/usr/bin/yt-dlp`) — no
  bundled binary, unlike the Windows repo's `yt-dlp.exe`.
- **browser_obsidian_clip** and **browser_captive_portal** target **Brave**
  (Chromium-based, supports `--remote-debugging-port` for CDP) since this
  machine has no Chrome installed. Firefox can't be used for CDP-based
  clipping (use `--dir` batch mode instead for Firefox-saved pages).
- Every tool with third-party Python deps has its own `requirements.txt` in
  its folder — install with `pip install -r requirements.txt` (in a venv;
  see each tool's README for whether it expects its own or a shared one).
