# TOOLS.md — MAG Tools (Linux) Reference

Detailed profiles for each tool in this folder. Run everything from this
directory unless noted. This is the Linux counterpart to the Windows
`mag-tools` repo's `TOOLS.md` — ported and, where the hardware differs,
redesigned rather than translated. See `CLAUDE.md` for the machine this
targets.

---

## FFmpeg — Video Compression (`/mag_vid_compress`)

**What it does:** Compresses screen recordings using hardware AV1 encoding
for maximum storage reduction (typically 15–30× smaller than H.264).
**When to use:** Archiving screen recordings, walkthroughs, or meeting
captures where file size matters and pixel-perfect fidelity is not required.

**Invoke via skill:** `/mag_vid_compress` — accepts a file name, full path,
or folder.

**Agent defaults (always applied unless user specifies otherwise):**
- Output folder: `~/Videos/mag_compressed/`
- Output filename: `<original_name>_AV1.mp4`
- Encoder: `av1_qsv` (Intel QSV, via the Iris Xe iGPU) — confirmed available
  on this machine; `av1_nvenc` (NVIDIA RTX 3060) is also available as an
  alternate path
- Frame rate: `fps=15` (screen recording sweet spot)
- Quality: `-global_quality 20` (sharp text; range 1–51, lower = higher quality)
- Preset: `veryslow` (best quality-per-bit on hardware encoders)
- Audio: `-c:a copy` (passthrough — zero loss, no echo artifacts)

**Core command:**
```sh
ffmpeg -y -loglevel error -stats -i "<input>" -vf "fps=15" -c:v av1_qsv -global_quality 20 -preset veryslow -c:a copy "<output>"
```

**Common variations:**
- Lower quality / smaller file → increase `-global_quality` (e.g. 35)
- Re-encode audio → `-c:a aac -b:a 64k` instead of copy
- No fps reduction → drop `-vf "fps=15"`
- Use the NVIDIA GPU instead → `-c:v av1_nvenc -cq 20`

**Requirements:** FFmpeg (already installed system-wide via apt on this
machine: `ffmpeg version 6.1.1`). Check available encoders with
`ffmpeg -encoders | grep -E 'av1_(qsv|vaapi|nvenc)'` — both `av1_qsv` and
`av1_nvenc` were confirmed present. If neither is available, fall back to
CPU encoding with `libsvtav1` (much slower).

---

## yt-dlp (`TOOLS/video_yt_dlp/`)

**What it does:** Downloads video and audio from YouTube and 1000+ other sites.
**When to use:** Saving a video locally, extracting audio from a video,
archiving content.

**Agent defaults — always include these unless the user specifies otherwise:**
- `-o "$HOME/Downloads/%(title)s.%(ext)s"` — output folder
- `--merge-output-format mkv` — container format

**Invoke:**
```sh
yt-dlp <URL> -o "$HOME/Downloads/%(title)s.%(ext)s" --merge-output-format mkv [options]
```

**Key options:**

| Flag | Description |
|------|-------------|
| `-x` | Extract audio only |
| `--audio-format mp3\|wav\|m4a\|...` | Audio format (use with `-x`) |
| `-f <format>` | Select specific quality/format code |
| `-F` | List all available formats for a URL |
| `-o <template>` | Output filename template (e.g. `%(title)s.%(ext)s`) |
| `--write-subs` | Download subtitles |
| `--sub-lang en` | Select subtitle language |
| `--playlist-start N` / `--playlist-end N` | Partial playlist download |
| `--cookies-from-browser brave` | Use Brave cookies (for age-gated/private content) |

**Output:** File(s) saved to current directory by default.
**Requirements:** Apt-installed system binary (`/usr/bin/yt-dlp`) — no
bundled binary needed, unlike the Windows repo's `yt-dlp.exe`.

---

## Real-ESRGAN — AI Video Upscale (`TOOLS/video_ai_upscale/upscale_video.py`)

**What it does:** Upscales a video using Real-ESRGAN (ncnn-vulkan build) — a
GAN-based super-resolution model, sharper/more detailed than classic
Lanczos/bicubic scaling. Runs via Vulkan on any GPU. The
`realesrgan-ncnn-vulkan` binary only works on still images, so the wrapper
script extracts frames with ffmpeg, upscales each frame, then re-encodes back
to video at the original fps with the original audio muxed back in.
**When to use:** Boosting resolution/detail on phone or screen-recorded
footage, especially after a denoise pass. Not a substitute for a genuinely
higher-res source.

**Invoke:**
```sh
python3 TOOLS/video_ai_upscale/upscale_video.py <input_video> <output_video> [--scale 2|3|4] [--model realesrgan-x4plus|realesr-animevideov3|realesrgan-x4plus-anime] [--keep-frames]
```

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input_video` | Yes | — | Source video file |
| `output_video` | Yes | — | Destination video file |
| `--scale` | No | `2` | Upscale factor. 4x on already-1080p+ sources is usually overkill/slow — default 2x. |
| `--model` | No | `realesrgan-x4plus` | `realesrgan-x4plus` for general/realistic footage (default); `realesr-animevideov3` for animation (faster); `realesrgan-x4plus-anime` for anime images |
| `--keep-frames` | No | Off | Keep the temp `_upscale_tmp/frames` and `_upscale_tmp/upscaled` folders instead of deleting them |

**Output:** Re-encoded video (H.264, crf 16, preset slow, original audio
copied) at `<output_video>`, same fps as source.
**Requirements:** `ffmpeg`/`ffprobe` in PATH (present). `realesrgan-ncnn-vulkan`
Linux binary + `models/` folder must be placed in
`TOOLS/video_ai_upscale/` manually (not fetched as part of this repo build —
see the tool's README for the download link and exact steps). Vulkan
confirmed present on this machine (1.3.275, via Iris Xe/RTX 3060).

---

## MAG - Captive Portals (`TOOLS/browser_captive_portal/`)

**What it does:** Resolves the current default gateway IP and opens the
**Captive Portal Redirector** dashboard in the default browser — it probes
plain-HTTP connectivity URLs and opens the first reachable one in a new tab,
for captive-portal logins (hotel/airport Wi-Fi). The gateway is tried first,
then `neverssl.com` → `httpforever.com` → `captive.apple.com` → `generate_204`.
**When to use:** Connected to a new network that blocks internet until a
portal login is completed.

**Invoke:**
```sh
./TOOLS/browser_captive_portal/captive_portal.sh
```

**Parameters:** optional positional arg — dashboard filename to open
(defaults to `Captive Portal Redirector.html`).
**Output:** Opens the browser (`xdg-open`, falling back to `brave-browser` or
`firefox`) at the dashboard, pre-loaded with the gateway candidate.
**Requirements:** `ip` (iproute2) and one of `xdg-open`/`brave-browser`/`firefox`.
Ported from PowerShell (`Get-NetRoute`/`ipconfig` + `Start-Process chrome.exe`)
to bash (`ip route` + `xdg-open`) — see the tool's README.

---

## find_files (`TOOLS/utils_findfiles/find_files.sh`)

**What it does:** Searches for files whose name contains a given string.
Thin bash wrapper around `find` (which already does this natively).
**When to use:** Locating files when you only remember part of the filename.

**Invoke:**
```sh
./TOOLS/utils_findfiles/find_files.sh -s SEARCH_STRING [-p PATH] [-r]
```

**Parameters:**

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-s` | Yes | — | Substring to match in filename (case-insensitive) |
| `-p` | No | current directory | Directory to search |
| `-r` | No | off | Search all subdirectories |

**Output:** Prints full paths of matching files to console.
**Requirements:** Standard coreutils/findutils.

---

## Hydrate-OneDrive — not ported

**Status:** Deliberately not ported. The Windows tool worked around a
Windows-OneDrive-specific behavior (cloud-only placeholder files) that has no
direct equivalent on Linux (no OneDrive client installed on this machine; the
two realistic Linux sync options — the abraunegg client or an rclone mount —
each have a different, non-analogous file-materialization model). Full
reasoning and options in `TOOLS/utils_hydrate_onedrive/README.md`. Don't
build a speculative port — decide the sync method first if this becomes a
real need.

---

## classify_images (`TOOLS/utils_image_tools/classify_images.py`)

**What it does:** Reads a markdown classification table (rows with Original
filename / Category / Proposed filename / Confidence columns — the kind
produced by a vision-model classification pass) and, for each "High"
confidence row, moves the source image into a folder named after its
category, renames it to the proposed filename, and — for JPEGs — writes the
category plus terms parsed from the filename as XMP `dc:subject` keywords.
**When to use:** Bulk-sorting a folder of photos after generating a
classification markdown file (e.g. from a VLM pass, such as
`ai_screenshot_ocr` in this repo).

**Invoke:**
```sh
python3 TOOLS/utils_image_tools/classify_images.py [markdown_file] [--dry-run] [--limit N] [--workdir <dir>]
```

**Parameters:**

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `markdown` | No | `image_classif.md` | Path to the classification markdown file |
| `--dry-run` | No | off | Preview moves/tags without writing anything |
| `--limit N` | No | all | Process only the first N high-confidence rows |
| `--workdir` | No | `.` | Directory containing the images and where category folders are created |

**Output:** Console log per image (source, target, tags written); summary
count of successes/errors.
**Requirements:** Python 3, no third-party deps (writes XMP into JPEGs via
raw byte manipulation, no Pillow needed).

---

## make_thumbnails (`TOOLS/utils_image_tools/make_thumbnails.py`)

**What it does:** Generates downscaled JPEG thumbnails (longest side 1024px,
quality 72, EXIF stripped) for every `.jpg`/`.JPG` in a folder, saved to a
`thumbnails/` subfolder with a `_thumb` suffix.
**When to use:** Producing lightweight preview copies of a photo batch —
e.g. before feeding images to a VLM for classification.

**Invoke:**
```sh
python3 TOOLS/utils_image_tools/make_thumbnails.py [folder]
```

**Parameters:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `folder` | No | folder the script lives in | Directory of JPGs to thumbnail |

**Output:** `thumbnails/<name>_thumb.jpg` per source image; console log with
output file sizes.
**Requirements:** Pillow (`pip install pillow`).

---

## tag_image (`TOOLS/utils_image_tools/tag_image.py`)

**What it does:** Writes XMP `dc:subject` tags (plus optional
title/description) into a PNG's metadata.
**When to use:** Manually tagging a single PNG (complements
`classify_images.py`, which only handles JPEGs in its bulk flow).

**Invoke:**
```sh
python3 TOOLS/utils_image_tools/tag_image.py IMAGE.png TAG [TAG ...] [--title TITLE] [--description DESC]
```

**Parameters:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `image` | Yes | — | Target PNG file (PNG only — errors on other extensions) |
| `tags` | Yes | — | One or more tags (space-separated) |
| `--title` | No | none | XMP title |
| `--description` | No | none | XMP description |

**Output:** Tags written in-place to the PNG; console confirmation of
tags/title/description set. Verify with `exiftool -XMP:Subject IMAGE.png`
(Linux file managers don't surface a Tags column the way Windows Explorer does).
**Requirements:** Pillow (`pip install pillow`).

---

## html_to_text (`TOOLS/utils_html_to_text/html_to_text.py`)

**What it does:** Strips HTML down to plain text — concatenates the text
content of every `<p>` tag, double-newline separated. Not a full HTML→text
converter (ignores headings, lists, tables — paragraphs only).
**When to use:** Quick plain-text extraction from a saved HTML page when you
don't need full structure preserved.

**Invoke:**
```sh
python3 TOOLS/utils_html_to_text/html_to_text.py input.html [output.txt]
```

**Parameters:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input.html` | Yes | — | Source HTML file |
| `output.txt` | No | stdout | Where to write extracted text |

**Output:** Plain text printed to stdout, or written to `output.txt` if given.
**Requirements:** `pip install beautifulsoup4`.

---

## AI — Local Whisper Transcription (`TOOLS/ai_whisper_transcription/`)

**What it does:** Transcribes video or audio files locally using
**faster-whisper (CTranslate2) on CUDA**, falling back to CPU. This is a
redesign, not a straight port — see the tool's README for why (the Windows
version targeted an Intel NPU this machine doesn't have; this machine has an
RTX 3060 instead, which faster-whisper uses well). Loads the model once and
can batch multiple files in a single process. Exports `.md` (with metadata
table + segments), `.txt`, `.srt`, and/or `.vtt` next to each input file.
**When to use:** Transcribing meeting recordings, screen-recording narration,
voice notes, or any video/audio file without sending data to the cloud.

**First time:** `TOOLS/ai_whisper_transcription/.venv/` doesn't exist until
you run `TOOLS/ai_whisper_transcription/setup.sh` — do that first, or the
invoke command below fails with "No such file or directory".

**Invoke:**
```sh
TOOLS/ai_whisper_transcription/.venv/bin/python3 \
  TOOLS/ai_whisper_transcription/whisper_video_transcriber.py \
  -a "<input_file>" [options]

# Batch an entire folder (recommended — single model load for all files):
TOOLS/ai_whisper_transcription/.venv/bin/python3 \
  TOOLS/ai_whisper_transcription/whisper_video_transcriber.py \
  --folder "<folder_of_videos>"
```

**Parameters:**

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-a` / `--audio` | One of `-a`/`--folder` | — | Input video/audio file(s), space-separated for multiple |
| `--folder` | One of `-a`/`--folder` | — | Folder of video/audio files to transcribe, sorted by name |
| `--model` | No | `medium` | faster-whisper model name (`tiny`/`base`/`small`/`medium`/`large-v3`) or local CTranslate2 model dir |
| `--device` | No | `cuda` | Preferred device; auto-falls back cuda→cpu |
| `--lang` | No | `en` | Language code, e.g. `es` for Spanish (also accepts old `<\|en\|>` token form) |
| `--beam-size` | No | `1` | Beam search width — safe to raise on CUDA (unlike the old NPU int8 pipeline, this doesn't degrade quality) |
| `--repetition-penalty` | No | `1.3` | Suppresses "Music"/hallucination repeats on silent segments |
| `--prompt` | No | none | Initial prompt to bias vocabulary — safe to use here (the NPU-crash caveat doesn't apply to this engine) |
| `--output-dir` | No | same folder as each input | Where to write output files |
| `--formats` | No | `md,txt,srt` | Comma-separated: `md`, `txt`, `srt`, `vtt` |

**Output:** Console progress per file; `<name>.md` / `.txt` / `.srt` / `.vtt`
written per the `--formats` selection.
**Requirements:** `python3.12-venv` installed system-wide (`sudo apt install
python3.12-venv`) before running `setup.sh` — without it, `setup.sh`
silently produces a broken venv missing `pip`; see the tool's README
troubleshooting section. Own `.venv`
(`TOOLS/ai_whisper_transcription/setup.sh`; installs `faster-whisper`). The
model itself downloads from Hugging Face on first run. CUDA acceleration
needs cuDNN9/cuBLAS reachable at runtime (init succeeds either way, but
transcription then fails per-file with `libcublas.so.12 not found` if
missing) — see the tool's README for the pip + `LD_LIBRARY_PATH` fix;
`--device cpu` always works with zero extra setup.

---

## AI — Local Screenshot OCR / VLM Analyzer (`TOOLS/ai_screenshot_ocr/`)

**What it does:** Runs a local vision-language model (InternVL2-1B INT8 via
OpenVINO GenAI) on an image to extract context, a short title, and a
one-sentence description. Proposes a structured filename. Exports a `.json`
metadata file. Unlike the Whisper tool, this one kept its original engine —
OpenVINO's GPU plugin runs on Linux and this machine's Intel Iris Xe iGPU is
exactly the device class it already targeted.
**When to use:** Auto-labeling screenshots, extracting text or context from
an image without uploading to a cloud API.

**First time:** `TOOLS/ai_screenshot_ocr/.venv/` doesn't exist until you run
`TOOLS/ai_screenshot_ocr/setup.sh` — do that first, or the invoke command
below fails with "No such file or directory".

**Invoke:**
```sh
TOOLS/ai_screenshot_ocr/.venv/bin/python3 TOOLS/ai_screenshot_ocr/screenshot_metadata.py -i <image_file> [options]
```

**Parameters:**

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-i` / `--image` | Yes | — | Path to image file (JPG, PNG, BMP) |
| `--model` | No | `InternVL2-1B-int8-ov` | Path to OpenVINO model folder |
| `--device` | No | `GPU` | Inference device: `GPU` (Intel Iris Xe) or `CPU` |

**Output:**
- Console summary: `context`, `proposed filename`, inference time.
- `<image_filename>.json` alongside the image with: original name, proposed
  name (format: `Context - Relevance _ YYMMDD`), full AI analysis, and
  timing stats.

**First run:** Downloads model from HuggingFace (~1 GB) if not already
present — not done yet as part of this repo build.
**Requirements:** Own `.venv` (`TOOLS/ai_screenshot_ocr/setup.sh` — not run
yet). GPU inference needs the Intel OpenCL driver:
`sudo apt install intel-opencl-icd`.

---

## image_stacking — Noise Reduction via Photo Stacking (`TOOLS/video_image_stacking/`)

**What it does:** Aligns and stacks multiple photos of the same scene to
produce a single low-noise image. Useful for night/low-light photography
without a tripod.
**When to use:** You have several handheld shots of the same scene and want
to reduce noise by merging them.

**Invoke:**
```sh
python3 TOOLS/video_image_stacking/auto_stack.py <input_dir> <output.jpg> --method <ORB|ECC|FLOW> [--blend mean|median] [--show]
```

**Parameters:**

| Argument | Required | Description |
|----------|----------|-------------|
| `input_dir` | Yes | Folder containing the images to stack (JPG/PNG/BMP) |
| `output_image` | Yes | Output filename (e.g. `result.jpg`) |
| `--method` | Yes | `ORB` (faster, keypoint-based), `ECC` (slower, more precise, global), or `FLOW` (dense optical flow, corrects local/non-rigid motion) |
| `--blend` | No | `mean` (default) or `median` (rejects ghosting from local motion) |
| `--show` | No | Display result in a window after saving (needs an X11/Wayland display — present on this machine) |

**When to choose which:** ORB handles large misalignments well. ECC is more
accurate for subtle global alignment but slower. FLOW corrects per-pixel
local motion (e.g. an animal's fur/breathing) that a single global transform
can't touch.
**Requirements:** Python + OpenCV 3+. No venv included — install with
`pip install -r TOOLS/video_image_stacking/requirements.txt`.

---

## YoutubeWL Cleaner (`TOOLS/browser_youtubewl_cleaner/`)

**What it does:** A local HTML utility for managing a YouTube Watch Later
playlist.
**When to use:** Bulk-cleaning your YouTube Watch Later list.

**Invoke:** Open `TOOLS/browser_youtubewl_cleaner/YoutubeWL Cleaner 230504.html`
directly in a browser (`xdg-open "..."`). No server needed.

---

## WireGuard VPN (UpCloud) (`TOOLS/vpn_wireguard/`)

**What it does:** Configuration files and setup notes for a self-hosted
WireGuard VPN running as a Docker container on UpCloud (the server side is
already Linux — unchanged from the Windows repo).
**When to use:** Setting up or reconnecting to the personal VPN.

**Files:**
- `TOOLS/vpn_wireguard/docker-compose.yaml` — Docker stack definition
- `TOOLS/vpn_wireguard/vpn_setup.sh` — Init script for new server
- `TOOLS/vpn_wireguard/WireGuard VPN @UpCloud -- Notes.md` — Full deployment walkthrough
- `TOOLS/vpn_wireguard/ROTATE_WIREGUARD_KEY.md` — Key rotation procedure

**Quick reconnect (if server already running):**
```sh
ssh root@<server-ip>
cd /root/wireguard && docker compose start
```

**Connecting from this Linux client** (the Windows repo assumed the
WireGuard Windows GUI client): use `nmcli connection import type wireguard
file peers/peer1/peer1.conf` (NetworkManager, no extra install) or
`wg-quick` (needs `sudo apt install wireguard-tools`) — see the tool's
README for both.

**Note:** Docker is not installed on this machine yet (it only runs
server-side; nothing here needs it unless standing up the server itself from
this box). This repo has no `_local_only/` secrets folder yet since no SSH
key/log has been copied over — see the tool's README for the recommendation
to use a standard OpenSSH key instead of the Windows repo's PuTTY-format one.

---

## clip_page — Browser-CDP Page Clipper → Obsidian (`TOOLS/browser_obsidian_clip/`)

**What it does:** Replicates the Obsidian Web Clipper browser extension
without the extension — grabs the active browser tab over the DevTools
Protocol (CDP), strips boilerplate (`script`/`style`/`nav`/`header`/`footer`/
`aside`/`iframe`/`form`), converts to Markdown, and writes it into an
Obsidian vault with enriched YAML frontmatter (page/course/lesson identity,
source URL, saved date, ordered outline, tags). Inline base64 images are
decoded to real files under `attachments/`, deduped by SHA-256. Also
batch-converts a folder of already-saved local HTML files, no live tab needed.
**When to use:** Saving a web page or an offline-saved HTML export as a
Markdown note in Obsidian.

**Invoke:**
```sh
python3 TOOLS/browser_obsidian_clip/clip_page.py [--match TEXT] [--vault PATH] [--out DIR] [--dir DIR] [--tag TAG ...]
```

**Parameters:**

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--match` | No | none | Filter open tabs by title/URL substring (live-tab mode) |
| `--vault` | No | currently-open Obsidian vault (from `~/.config/obsidian/obsidian.json`) | Target vault path |
| `--out` | No | — | Output directory, overrides `--vault` entirely |
| `--dir` | No | — | Batch-convert local HTML files in this directory instead of a live tab (bypasses CDP) |
| `--tag` | No | none | Tag to add to frontmatter (repeatable) |

**Output:** `<name>.md` written to the vault/output dir; extracted images
under `attachments/`.
**Requirements:** Python 3 with `requests`, `websocket-client`,
`beautifulsoup4`, `markdownify`, `lxml`. Live-tab mode needs **Brave**
running with `--remote-debugging-port=9223` (this machine has Brave and
Firefox, not Chrome — CDP only works with Chromium-family browsers, so
Firefox can't be used for live-tab mode; use `--dir` batch mode for
Firefox-saved pages). `--dir` batch mode needs neither a browser nor a debug port.
**Note:** Obsidian's config path on Linux is `~/.config/obsidian/obsidian.json`
(not `%AppData%\obsidian\obsidian.json`).

---

## Similar Pic Matcher (`TOOLS/media_pic_similarity_match/`)

What it does: Compute HSV color-histogram fingerprints and find visually
similar images by color palette.
CLI: `python3 similar_pic_matcher.py <folder> [--count N] [--bins B] [--all]`.
Requirements: Pillow, numpy. Notes: O(n²) pairwise comparisons; thresholds
and usage documented in the tool's README.

## Dewarp Flexible QR (`TOOLS/dewarp_flexible_qr/`)

What it does: Non-rigid thin-plate-spline dewarp for QR/barcode images
photographed on wrinkled or curved flexible surfaces.
CLI: `python3 dewarp_flexible_qr.py INPUT.jpg [--crop ...] [--decode] [--save-debug DIR]`.
Requirements: `opencv-python-headless`, `scipy`, `pyzbar`, `pillow`, plus the
system package `libzbar0` (pyzbar's native dependency —
`sudo apt install libzbar0`). See the tool's README for parameters.

## BTC-Nasdaq correlation (`TOOLS/data_btc_nasdaq_correlation/`)

What it is: Interactive HTML visualization (`bitcoin_vs_nasdaq.html`) and
accompanying data. Self-contained artifact — open the HTML to view the
chart. Renamed from the Windows repo's `BTC-Nasdaq correlation` (space in the
folder name) to the `data_` category prefix for consistency.

## ai_session_finder (`TOOLS/ai_session_finder/build_index.py`)

**What it does:** Searches the local stores of all three terminal AI coders
(Claude Code, OpenCode, Copilot) to find past sessions/conversations by
title, first prompt, folder, or id. `--search <term>` returns plain text for
agent ingestion; run with no arguments to refresh the visual `sessions.html`.

**When to use:** The user asks to find/locate a past conversation or
workspace, or asks to refresh/open the session browser page.

**Invoke (agent / find mode — preferred):**
```sh
python3 TOOLS/ai_session_finder/build_index.py --search <term> [<term> ...]
```
Returns one block per matching session (newest first): tool, title, prompt,
folder, updated, and `id`. All terms must match (case-insensitive, AND).
This mode writes no files and needs no browser.

**Invoke (browser / refresh mode):**
```sh
python3 TOOLS/ai_session_finder/build_index.py        # refresh / rebuild sessions.html
xdg-open TOOLS/ai_session_finder/sessions.html
```
Clicking a row (or its Copy button) copies the resume command to the
clipboard — paste it into a terminal. (The Windows version's click-to-open a
new terminal via a custom `magopen://` protocol handler wasn't ported; see
the tool's README for why.)

**Data sources:** `~/.claude/projects/*.jsonl`,
`~/.local/share/opencode/opencode.db`, `~/.copilot/session-state/*/workspace.yaml`.

**Requirements:** Python 3 (stdlib only).
