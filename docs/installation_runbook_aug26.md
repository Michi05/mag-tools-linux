# Installation Runbook — mag-tools-linux

**Audience:** an AI (or human) operator setting up this repo's runtime
environment — on this machine again after a wipe, or on a similar Linux
machine. This is an **installation** runbook (system packages, venvs,
models/binaries, verification) — the ported code itself already lives in
this repo; you're not re-deriving it, just making it runnable.

**How to use this document:** every step is tagged `[GLOBAL]` or
`[TOOL: <name>]`. Tools are independent by design (see `CLAUDE.md` —
"no shared framework, each tool is self-contained") — **skip any
`[TOOL: x]` block for a tool you don't want; it has no effect on any other
tool's steps.** `[GLOBAL]` steps are shared infrastructure; a couple of
tools depend on one specific `[GLOBAL]` step, called out where relevant. Run
steps top to bottom within a block you keep; blocks can be reordered freely
across tools.

Each step names the underlying package/binary it installs (not just the
repo folder), so you can tell what's actually landing on the system.

---

## 0. Context — decisions made building this repo (read once, applies everywhere)

- **Why a separate repo instead of editing `../mag-tools` in place:** that
  repo targets a different, Windows machine. This one targets *this*
  machine — different OS, different hardware (see below) — so it's a
  from-scratch build informed by the source repo's logic, not a copy.
- **Hardware this repo assumes** (re-check if installing on different
  hardware): Linux Mint 22.3 (Ubuntu/Debian-based, so `apt` applies as
  written), Intel Core i7-11370H (TigerLake — **no NPU**; NPU support only
  exists from Meteor Lake onward), Intel Iris Xe iGPU, NVIDIA RTX 3060
  Mobile (6GB VRAM, CUDA 13 driver already installed), Brave + Firefox
  installed (no Chrome), `ffmpeg` already installed system-wide via apt,
  `yt-dlp` already installed system-wide via apt, ~430GB free disk.
- **Build-depth decision made when this repo was created:** the
  lightweight/dependency-light tools were fully installed and verified; the
  three heavy-ML tools (Whisper transcription, screenshot VLM OCR, video
  upscaling) were fully coded but their multi-GB model/dependency downloads
  were **deliberately deferred** — each has its own `[TOOL: ...]` section
  below with the deferred step clearly marked. If reinstalling and you *do*
  want them immediately, just don't defer that step.
- **Problems found in the source repo that this install avoids repeating**
  (full detail in `docs/porting-notes.md`): a `.gitignore` that blocked
  everything by default (fixed here — normal deny-list); a tool folder
  committed in two places at once; a folder name with a space in it; folder
  names that didn't follow the `<category>_<name>` convention; `TOOLS.md`
  drifting from the actual folder layout after a manual rename. None of
  these are installation steps, but they're why this runbook's file
  layout looks the way it does — don't reintroduce them.

---

## 1. `[GLOBAL]` Base repo skeleton

**Underlying tool:** `git`, standard filesystem layout — no package installs.

1. Create the repo directory as a *sibling* of the source repo (not nested
   inside it): `mkdir -p mag-tools-linux && cd mag-tools-linux`
2. `git init` (no commits made automatically as part of this build — see
   §7 "Not done yet").
3. Directory layout (`mkdir -p` each): `.claude/commands/`,
   `TOOLS/<category>_<name>/` — one per tool you're keeping (see §4), `docs/`,
   `self_health_test/checks/`.
4. Write `.gitignore` — deny-list style (venvs, `__pycache__`, downloaded
   models/binaries, `_local_only/` secrets, OS/editor cruft, `.claude/settings.local.json`).
   **This is the one fix from §0 that must not be skipped or reverted** —
   don't recreate the source repo's "ignore everything, allow only .md"
   pattern.
5. Write root docs: `README.md` (one-liner pointer), `CLAUDE.md` (repo intent
   + machine profile + folder map — keep this in sync with whichever tools
   you actually install; don't describe a tool folder that isn't there),
   `TOOLS.md` (per-tool profiles — generate this FROM the final folder
   layout, never let it lead the layout, that's exactly the drift bug in §0).
6. Write `.claude/settings.json` — Bash permission allowlist
   (`ffmpeg`, `ffprobe`, `mkdir`, `ls`, `find`, `python3`, `yt-dlp`). Adjust
   if you drop tools that used a permission not needed elsewhere.
7. Write `.claude/commands/run-tool.md` (generic tool-runner protocol — not
   tool-specific, always keep) and `.claude/commands/mag_vid_compress.md`
   (see `[TOOL: mag_vid_compress]` below — this one command file IS
   tool-specific and droppable).

---

## 2. `[GLOBAL]` Environment discovery (run before deciding anything hardware-specific)

**Underlying tools:** `lscpu`, `lspci`, `python3`, `ffmpeg`, `vulkaninfo`,
`nvidia-smi`, `pip`. No installs — read-only checks that inform every
hardware-dependent decision downstream (which AV1 encoder to default to,
whether CUDA is available for Whisper, whether OpenVINO GPU has a target,
whether Vulkan is available for the upscaler).

```sh
cat /etc/os-release
lscpu | grep "Model name"
lspci | grep -iE "vga|3d|display"                    # GPU(s) present
python3 --version
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "av1_(qsv|vaapi|nvenc)"
which google-chrome chromium brave-browser firefox    # which browser(s) exist
nvidia-smi                                            # NVIDIA driver/CUDA version, if any
vulkaninfo --summary                                  # Vulkan instance, if any
which yt-dlp docker wg wg-quick nmcli
python3 -m pip list 2>/dev/null | grep -iE "opencv|pillow|numpy|openvino|torch|beautifulsoup"
```

On re-install on the **same** machine, this step should reproduce the
findings in §0 exactly. On a **different** machine, re-derive the
hardware-driven decisions in the tool sections below from fresh output
instead of assuming this machine's answers (e.g. a machine with an Intel
NPU should probably keep the source repo's NPU pipeline for Whisper instead
of this repo's CUDA redesign — see `[TOOL: ai_whisper_transcription]`).

---

## 3. `[GLOBAL]` Shared Python venv for lightweight tools

**Underlying tool:** `python3 -m venv` (stdlib) or, if that fails, the
`virtualenv` pip package; then `pip`.

**Depends on:** nothing else in this runbook. **Depended on by:**
`utils_image_tools`, `utils_html_to_text`, `media_pic_similarity_match`,
`dewarp_flexible_qr`, `video_image_stacking`, `browser_obsidian_clip` — skip
this whole step only if you're dropping **all six** of those tools.

1. Try the stdlib venv first: `python3 -m venv .venv`
   - **Known failure mode hit during this build:** on Debian/Ubuntu-derived
     systems, this can fail with `ensurepip is not available` if the
     `python3.X-venv` apt package isn't installed, and installing it needs
     `sudo` (a password prompt an AI agent can't answer non-interactively).
   - **Fallback that worked without sudo:** the `virtualenv` pip package was
     already present in user site-packages on this machine (bundles its own
     pip, doesn't need `ensurepip`): `virtualenv .venv`. If `virtualenv`
     isn't available either, that's the point to actually ask the human to
     run `sudo apt install python3.12-venv` (adjust version) themselves.
2. Install the shared lightweight dependencies:
   ```sh
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install pillow numpy beautifulsoup4 markdownify lxml \
       requests websocket-client opencv-python-headless scipy pyzbar
   ```
3. System library dependency for one of the above:
   `pyzbar` needs `libzbar0` (Linux shared library, not a pip package).
   Check first (`ldconfig -p | grep -i zbar`) — it was already present on
   this machine via `libzbar0t64`. If missing: `sudo apt install libzbar0`.

**Verify:** `.venv/bin/python3 -c "import cv2, numpy, PIL, bs4, markdownify, scipy, pyzbar; print('ok')"`

---

## 4. Per-tool installation

### `[TOOL: video_yt_dlp]`

**Underlying binary:** `yt-dlp` (already an apt package on this machine).

1. Check first: `which yt-dlp && yt-dlp --version`.
2. If missing: `sudo apt install yt-dlp`, or for a newer release than the
   distro ships: `python3 -m pip install --user -U yt-dlp`.
3. No venv, no Python deps, no bundled binary (unlike the source repo's
   bundled `yt-dlp.exe` — apt keeps this one patched automatically).

**Verify:** `yt-dlp --version` exits 0.

---

### `[TOOL: mag_vid_compress]` (slash-command skill, not a `TOOLS/` folder)

**Underlying tool:** `ffmpeg` with a hardware AV1 encoder — `av1_qsv`
(Intel Quick Sync) and/or `av1_nvenc` (NVIDIA NVENC), both confirmed present
on this machine; `av1_vaapi` is the fallback path for AMD GPUs.

1. `ffmpeg` should already be present (`sudo apt install ffmpeg` if not).
2. No other install — this is pure ffmpeg CLI usage, documented as a slash
   command (`.claude/commands/mag_vid_compress.md`) rather than a script.
3. Drop this by deleting `.claude/commands/mag_vid_compress.md` and its
   `TOOLS.md` section — nothing else references it.

**Verify:** `ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "av1_(qsv|nvenc|vaapi)"` returns at least one line.

---

### `[TOOL: browser_captive_portal]`

**Underlying tools:** `iproute2` (`ip route`, standard on any Linux
install), plus one of `xdg-open` / `brave-browser` / `firefox` to actually
open the page.

1. Nothing to install beyond what's already standard — `ip` and `xdg-open`
   ship with any desktop Linux install; a browser is a precondition, not
   installed by this tool.
2. **Decision made here:** ported from PowerShell (`Get-NetRoute`) to bash
   (`ip route show default`), and from `Start-Process chrome.exe` to
   `xdg-open` with an explicit Brave→Firefox fallback chain, since this
   machine has no Chrome.

**Verify:** `bash -n TOOLS/browser_captive_portal/captive_portal.sh` (syntax
only — don't actually launch a browser in an unattended install check).

---

### `[TOOL: utils_findfiles]`

**Underlying tool:** `find` (findutils, always present on Linux).

1. Nothing to install — the tool is a thin bash wrapper, no dependencies of
   its own beyond coreutils/findutils.

**Verify:** create two dummy files, run
`TOOLS/utils_findfiles/find_files.sh -s <substring> -p <tmpdir>`, confirm
only the matching one is listed.

---

### `[TOOL: utils_hydrate_onedrive]` — deliberately NOT installed

**Decision:** not ported. No OneDrive client is installed on this machine,
and the Windows-specific placeholder-hydration problem this tool solved
doesn't have a direct Linux equivalent (the two realistic Linux options —
the `abraunegg/onedrive` client, or an `rclone mount` — have different,
non-analogous file-materialization models). If a future install genuinely
needs OneDrive sync: decide the sync method first, then write a new
tool against *that* method's actual placeholder/caching behavior — don't
resurrect this one speculatively. Full reasoning in
`TOOLS/utils_hydrate_onedrive/README.md`.

---

### `[TOOL: utils_image_tools]` (`classify_images.py`, `make_thumbnails.py`, `tag_image.py`)

**Underlying package:** Pillow (`pillow`, in the shared venv from §3).

**Depends on:** `[GLOBAL] §3 shared venv`.

1. No tool-specific install beyond the shared venv's `pillow`.
2. `classify_images.py` itself needs no third-party deps at all (raw JPEG
   byte manipulation) — it only needs *some* `python3`, not necessarily the
   venv. `make_thumbnails.py` and `tag_image.py` need Pillow.
3. Optional verification-only tool: `exiftool`
   (`sudo apt install libimage-exiftool-perl`) — **not required** to run
   these scripts, only useful to inspect the XMP tags they write
   afterward. Not installed as part of this build (found missing during
   validation, documented as optional, not a blocker).

**Verify:** generate a tiny synthetic JPG/PNG with Pillow, run all three
scripts against it (see `self_health_test/checks/check_utils_image_tools.sh`
for the exact fixture-based check).

---

### `[TOOL: utils_html_to_text]`

**Underlying package:** `beautifulsoup4`.

**Depends on:** `[GLOBAL] §3 shared venv`, OR just
`python3 -m pip install --user beautifulsoup4` / apt's `python3-bs4` if you
want this tool standalone without the shared venv — it's simple enough that
either works, and this was in fact confirmed to run fine with plain system
`python3` during validation (bs4 was already present system-wide here).

**Verify:** run against a small HTML snippet with two `<p>` tags, confirm
both extracted and a `<script>` tag's content is not.

---

### `[TOOL: ai_whisper_transcription]` — hardware-redesigned, not ported

**Underlying package:** `faster-whisper` (CTranslate2), targeting **CUDA**
on this machine's RTX 3060 (fallback: CPU, int8).

**Decision and why (re-verify if installing on different hardware):** the
source repo's Whisper tool used OpenVINO GenAI on an **Intel NPU**. This
machine's CPU (TigerLake, 11th-gen) has no NPU — that pipeline would never
initialize here. This machine does have an unused NVIDIA RTX 3060, so the
tool was rebuilt on `faster-whisper`/CUDA instead of literally translating
NPU-specific code. **If installing on a machine that DOES have an Intel
NPU**, the source repo's original OpenVINO/NPU approach is likely the
better fit — don't assume this CUDA redesign is universally "the Linux way,"
it's specifically the fit for *this* machine's hardware.

**Steps (own venv, deliberately isolated from the shared one — CUDA stack
doesn't need to coexist with OpenVINO's stack):**

1. `cd TOOLS/ai_whisper_transcription && ./setup.sh` — creates `.venv/`,
   installs `faster-whisper`. **This step was deferred during this build**
   (per an explicit scope decision to avoid a large download without being
   asked) — run it now if you want this tool functional.
2. Model download is automatic on first real run (`faster-whisper`
   downloads e.g. `medium`, ~1.5GB, from Hugging Face into
   `~/.cache/huggingface` on first use) — also deferred, happens the first
   time you actually transcribe something.
3. **GPU note:** CUDA acceleration needs cuDNN9 + cuBLAS reachable at
   runtime. If `--device cuda` fails to initialize:
   `pip install nvidia-cudnn-cu12 nvidia-cublas-cu12` and point
   `LD_LIBRARY_PATH` at their lib dirs (see faster-whisper's own README), or
   just use `--device cpu` (slower, zero extra setup, works out of the box).

**Verify (without triggering the deferred download):**
`python3 TOOLS/ai_whisper_transcription/whisper_video_transcriber.py --help`
must succeed using **plain system `python3`, with no deps installed** — the
script's heavy imports are deliberately deferred into `main()`, after
argparse, specifically so this check is meaningful pre-setup. A real
invocation attempt before `setup.sh` should fail with a clear
"MISSING DEPENDENCY: faster-whisper" message, not a raw traceback.

---

### `[TOOL: ai_screenshot_ocr]` — ported as-is (engine kept)

**Underlying package:** `openvino-genai` + `openvino`, targeting **GPU**
(this machine's Intel Iris Xe iGPU via OpenVINO's GPU plugin) — fallback CPU.

**Decision and why:** unlike Whisper, this one's original engine transfers
directly — OpenVINO's GPU plugin runs on Linux, and this machine's Iris Xe
iGPU is exactly the device class the source script's `--device GPU` default
already targeted. Only the setup commands changed (pip/venv instead of
PowerShell), not the logic.

**Steps (own venv, isolated from both the shared one and the Whisper one):**

1. `cd TOOLS/ai_screenshot_ocr && ./setup.sh` — creates `.venv/`, installs
   `openvino-genai openvino huggingface_hub pillow numpy`. **Deferred during
   this build**, same reasoning as Whisper — run it now if you want this
   tool functional.
2. Model download (InternVL2-1B-int8-ov, ~1GB from Hugging Face) is
   automatic on first real run — also deferred.
3. System-level GPU driver dependency: `sudo apt install intel-opencl-icd`
   (Intel's OpenCL runtime — required for OpenVINO's GPU plugin to see the
   iGPU at all; without it, `--device GPU` fails and you must pass
   `--device CPU`).

**Verify (without triggering the deferred download):**
`python3 TOOLS/ai_screenshot_ocr/screenshot_metadata.py --help` must succeed
using plain system `python3` with no deps installed (same deferred-import
pattern as Whisper, applied here during this build specifically to make this
check possible — the source script originally imported at module scope,
which was changed here). A real invocation attempt before `setup.sh` should
fail with the "MISSING DEPENDENCIES DETECTED" message, not a traceback.

---

### `[TOOL: video_image_stacking]`

**Underlying package:** OpenCV (`opencv-python`, or `opencv-python-headless`
from the shared venv — either works, headless just skips the GUI bindings
`--show` needs).

**Depends on:** `[GLOBAL] §3 shared venv` (or its own
`pip install -r TOOLS/video_image_stacking/requirements.txt` if standalone).

1. No install beyond OpenCV/numpy. `--show` needs an X11/Wayland display
   (present on this machine) — drop that flag on a headless box.

**Verify:** run `auto_stack.py` with `--method ORB` against the sample
images in `TOOLS/video_image_stacking/images/` (a few were copied over
specifically as test fixtures), confirm an output image is produced.

---

### `[TOOL: video_ai_upscale]`

**Underlying binary:** `realesrgan-ncnn-vulkan` (Linux build, from the
[xinntao/Real-ESRGAN releases](https://github.com/xinntao/Real-ESRGAN/releases) —
unmaintained since 2022, still the latest available build), running on
**Vulkan** (confirmed present on this machine: instance 1.3.275, via either
GPU).

**Decision:** logic unchanged from the source repo (extract frames → upscale
each → re-encode with original audio) — only the binary differs (no `.exe`).

**Steps (deferred during this build — binary not fetched, no download
performed without being asked):**

1. Download the `realesrgan-ncnn-vulkan-*-ubuntu.zip` asset from the
   releases page above.
2. Extract it; copy the `realesrgan-ncnn-vulkan` binary and the `models/`
   folder into `TOOLS/video_ai_upscale/`.
3. `chmod +x TOOLS/video_ai_upscale/realesrgan-ncnn-vulkan`
4. `ffmpeg`/`ffprobe` already present (used for frame extraction/re-encode).

**Verify (without the binary):**
`python3 TOOLS/video_ai_upscale/upscale_video.py --help` succeeds (pure
argparse, no heavy deps at all for this one — only the binary is external).
A real invocation before the binary is placed should fail with a clear
"binary not found, here's the download link" message, not a raw traceback.

---

### `[TOOL: browser_youtubewl_cleaner]`

**Underlying tool:** none — static, self-contained HTML/JS. No install of
any kind; identical on every OS.

**Verify:** file exists, `grep -qi "<html" FILE`.

---

### `[TOOL: vpn_wireguard]`

**Underlying tools:** `docker` + `docker-compose` (**server-side only** —
runs on the remote UpCloud box, not this machine) and, client-side,
`nmcli` (NetworkManager — already present on this machine) or
`wireguard-tools` (`wg`, `wg-quick`).

1. **Server side** — only if standing up a *new* WireGuard server from this
   machine (not needed for day-to-day reconnect to an existing one):
   `sudo apt-get install docker.io docker-compose-plugin` (prefer the
   plugin form, invoked as `docker compose`, over the older standalone
   `docker-compose` binary the source repo's `vpn_setup.sh` installs — both
   work, the plugin is what modern Debian/Ubuntu ship).
2. **Client side, reconnecting to an existing server:**
   `nmcli connection import type wireguard file peers/peer1/peer1.conf` —
   no extra install needed, NetworkManager already handles WireGuard. Or,
   for `wg-quick` instead: `sudo apt install wireguard-tools`.
3. **Secrets:** the source repo kept a PuTTY-format SSH key
   (`id_rsa.ppk`) out of the tracked tree in `_local_only/wireguard/`.
   PuTTY is Windows-only — on Linux, generate/use a standard OpenSSH key
   instead (`ssh-keygen`, then `ssh root@<server-ip>` needs no conversion).
   If you do add a private key to this machine, mirror the source repo's
   pattern: put it in `_local_only/` (already gitignored here).

**Verify:** `bash -n TOOLS/vpn_wireguard/vpn_setup.sh` (syntax only — don't
actually provision a server or connect as part of an install check).

---

### `[TOOL: browser_obsidian_clip]`

**Underlying packages:** `requests`, `websocket-client`, `beautifulsoup4`,
`markdownify`, `lxml` (all in the shared venv from §3).

**Depends on:** `[GLOBAL] §3 shared venv`. Live-tab mode additionally needs
**Brave** running with `--remote-debugging-port=9223` (CDP only works with
Chromium-family browsers — this machine has Brave, not Chrome; Firefox
can't be used for live-tab mode at all, use `--dir` batch mode for
Firefox-saved pages instead).

1. No install beyond the shared venv.
2. **Decision made here:** Obsidian's config path on Linux is
   `~/.config/obsidian/obsidian.json`, not
   `%AppData%\obsidian\obsidian.json` — the script's `default_vault()`
   lookup was updated accordingly.

**Verify (no browser needed):** run `clip_page.py --dir <dir with a small
synthetic .html file> --out <tmpdir>`, confirm a `.md` file is produced with
the expected body text and frontmatter.

---

### `[TOOL: media_pic_similarity_match]`

**Underlying packages:** Pillow, numpy (shared venv).

**Depends on:** `[GLOBAL] §3 shared venv`.

1. No install beyond Pillow/numpy. Pure algorithm, no OS dependency.

**Verify:** run against 2-3 synthetic solid-color images, confirm the
"Nearest match per image" / "Top similar pairs" output sections appear.

---

### `[TOOL: dewarp_flexible_qr]`

**Underlying packages:** `opencv-python-headless`, `scipy`, `pyzbar`,
`pillow` (shared venv) — plus the system library `libzbar0` (see §3, step 3;
already covers this).

**Depends on:** `[GLOBAL] §3 shared venv` (including its `libzbar0` step).

1. No tool-specific install beyond what §3 already covers.
2. Optional extra decode backend: `pip install zxing-cpp` (not installed
   during this build — pyzbar alone was sufficient for verification).

**Verify:** `--help` works; run the full pipeline against a synthetic
flat-gray image and confirm it reports "segmentation/corner detection
failed" gracefully (expected — no HSV-contrasted panel in a solid-color
image, not a bug). No real wrinkled-QR fixture photo was available to test
a true positive during this build.

---

### `[TOOL: data_btc_nasdaq_correlation]`

**Underlying tool:** none — static HTML + JSON data file. No install.

**Verify:** file exists, JSON parses with stdlib `json.load`.

---

### `[TOOL: ai_session_finder]`

**Underlying tool:** Python 3 stdlib only — `sqlite3` (read-only,
`?mode=ro`), `json`, `re`, `argparse`. No pip installs, no venv.

1. Nothing to install.
2. **Decision made here:** the Windows version's row-click behavior opened
   a new terminal via a custom `magopen://` protocol handler (registry
   install). Not ported — no protocol handler is registered on Linux for
   that, and building one (a `.desktop` file + `xdg-mime` registration) was
   judged not worth it over the existing Copy-to-clipboard button, which
   works with zero setup. Clicking a row now just copies the resume command,
   same as the Copy button.

**Verify:** `python3 TOOLS/ai_session_finder/build_index.py --search <term
guaranteed not to match>` prints "No sessions matched"; a search for a term
known to appear in this machine's real `~/.claude/projects` data returns a
real match.

---

## 5. `[GLOBAL]` Self-health-test harness

**Underlying tool:** bash, plus whatever each individual check needs (the
shared venv for most, system `python3` for the stdlib-only and
deferred-heavy-ML ones).

1. `self_health_test/run_all.sh` iterates every `self_health_test/checks/check_*.sh`,
   each taking the repo root as `$1`, each self-contained (own temp dir,
   cleans up via `trap`), each exiting 0/1.
2. **This harness is exactly as modular as the tools it tests** — if you
   drop a `[TOOL: x]` section above, delete `checks/check_x.sh` too (or
   just leave it; a check for a tool whose files were never created will
   simply fail, which is an accurate signal, not a bug).
3. Run after any change: `./self_health_test/run_all.sh -v`. Full pass at
   the time of this build: **18/18** (see `self_health_test/results.md` for
   the per-tool breakdown and exactly what each check does and doesn't
   prove).

---

## 6. `[GLOBAL]` Documentation validation pass

An independent agent, given only `CLAUDE.md`/`TOOLS.md`/`run-tool.md` and no
other context, drove every tool through the documented `/run-tool` protocol
as a cold-start check that the docs alone are sufficient. Result: all 18
tools behaved exactly as documented. Two gaps it found were fixed
immediately in this build (both now reflected in `TOOLS.md` and this
runbook already):
1. The Whisper/screenshot-OCR "Invoke" blocks in `TOOLS.md` now say
   up front that `setup.sh` must be run first (their `.venv/` doesn't exist
   otherwise) — previously that was only mentioned elsewhere.
2. `utils_image_tools/README.md` now notes `exiftool` is optional and not
   installed by default, rather than implying it's a given.

If re-running this validation after a future reinstall, repeat the same
approach: spawn a fresh, context-free agent, point it at `CLAUDE.md`/
`TOOLS.md` only, and have it try to actually invoke each tool it decides to
keep.

---

## 7. Not done as part of this build — pick up here

- **Git:** repo initialized, nothing committed yet.
- **`ai_whisper_transcription/setup.sh`** — not run (faster-whisper not
  installed, no model downloaded).
- **`ai_screenshot_ocr/setup.sh`** — not run (openvino-genai not installed,
  no model downloaded).
- **`realesrgan-ncnn-vulkan` binary** — not downloaded for
  `video_ai_upscale`.
- **`exiftool`** — not installed (optional, verification-only for
  `utils_image_tools`).
- **Docker** — not installed (only needed if standing up a *new* WireGuard
  server from this machine; not needed to reconnect to the existing one).
- **`python3.12-venv` apt package** — never installed; the `virtualenv` pip
  package was used as a sudo-free fallback instead (see §3). Installing the
  proper apt package later is optional cleanup, not required.
