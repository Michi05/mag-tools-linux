You are running a video compression task using FFmpeg with hardware encoding, optimized for screen recordings.

## Step 1 — Hardware & encoder discovery

Run this check before building any command (only needed once per session, or if something seems off):
```sh
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "(h264|hevc|av1)_(qsv|vaapi|nvenc)"
```

**Known facts about this machine (confirmed 2026-09-03, see `TOOLS.md` for full detail) — don't re-derive these, just apply them:**
- **AV1 hardware encode does not exist on this machine, on either GPU.** This
  is a genuine silicon limit, not a driver issue — `av1_qsv` (Iris Xe,
  TigerLake) and `av1_nvenc` (RTX 3060, Ampere) are both compiled into ffmpeg
  and both fail at runtime. No config or driver change fixes this. Never
  attempt `av1_qsv`/`av1_nvenc` — go straight to CPU `libsvtav1` for AV1 output.
- **HEVC/H.264 hardware encode works on both GPUs** — `hevc_qsv`/`h264_qsv`
  (Iris Xe) and `hevc_nvenc`/`h264_nvenc` (RTX 3060) are all confirmed
  working. (`hevc_qsv` required installing `intel-media-va-driver-non-free`
  to fix a stripped-down open-source driver — already done on this machine.)
- **`hevc_qsv` requires `-hwaccel qsv` on the input side, always.** Without
  it, ffmpeg still software-decodes on CPU even though the encode is
  hardware — this silently drops throughput from ~1x realtime to ~0.45x
  realtime with no error message. Never build a `hevc_qsv` command without it.
- **`-preset veryslow` is not a real low-power path for `hevc_qsv`** on this
  driver — use `-preset medium` (benchmarked, works well) unless the user
  specifically wants to trade time for quality.

## Step 2 — Resolve input

The user will provide a file name, file path, or folder. Resolve it:
- Single file: use it directly as `-i`
- Folder: find all `.mp4`, `.mkv`, `.mov`, `.avi` files in that folder and process each in sequence

If no input is provided, ask for it before proceeding.

## Step 3 — Build the command

**Default profile — hardware HEVC via Iris Xe (`hevc_qsv`):**
```sh
ffmpeg -y -loglevel error -stats \
  -hwaccel qsv \
  -i "<input>" \
  -vf "fps=15" \
  -c:v hevc_qsv \
  -global_quality 20 \
  -preset medium \
  -c:a copy \
  "<output>"
```
This is the default because it's ~1x realtime, near-zero CPU usage, and
leaves the RTX 3060 free for other work (ML inference, etc.) — all three
paths (`hevc_qsv`, `hevc_nvenc`, CPU `libsvtav1`) are viable on this machine,
but this one is the best default balance of speed/resource use for a
background compression job. Benchmarked (2026-09-03, 4K/142s clip): 0.99x
realtime, 292MB output from a 615MB source (52.5% saved).

**Output location (default):** `~/Videos/mag_compressed/<original_name>_HEVC.mp4`
Create the output folder if it doesn't exist (`mkdir -p`). Adjust the suffix
to match whichever codec actually gets used (`_HEVC` for `hevc_qsv`/`hevc_nvenc`,
`_AV1` for `libsvtav1`).

**Switch paths if the user asks for one of these instead:**

- **NVIDIA HEVC** (comparable speed to the default, uses the RTX 3060 instead
  of the iGPU — pick this if the user wants the Iris Xe free instead, or is
  already using the iGPU for something else):
  ```sh
  ffmpeg -y -loglevel error -stats -i "<input>" -vf "fps=15" -c:v hevc_nvenc -cq 20 -preset p7 -c:a copy "<output>"
  ```
  NVENC preset names are numeric/`p1`-`p7` (`p7` = slowest/best), not the
  x264/QSV-style `veryslow` — passing `veryslow` fails with `Unable to parse
  option value`. Benchmarked: 0.93x realtime, 343MB from 615MB (44.3% saved).

- **Maximum compression (smallest file, CPU-only, slower)** — pick this when
  the user says size matters more than turnaround time:
  ```sh
  ffmpeg -y -loglevel error -stats -i "<input>" -vf "fps=15" -c:v libsvtav1 -crf 28 -preset 10 -svtav1-params lp=8 -c:a copy "<output>"
  ```
  Benchmarked: 0.41x realtime, 76MB from 615MB (87.8% saved) — smallest file
  by a wide margin, but ~2-3x slower than either GPU path and pins all CPU
  cores. `-preset 10` is the practical middle ground (range `-2` slowest/best
  to `13` fastest/worst); only go slower (e.g. `6`) if the user explicitly
  wants maximum quality and accepts a much longer runtime.

**Other adaptations:**
- Higher/lower quality → adjust `-global_quality`/`-cq`/`-crf` per whichever
  codec is in use (lower = higher quality on all three, but scales differ —
  QSV/NVENC quality flags run roughly 1–51, `libsvtav1`'s `-crf` runs 0–63)
- Re-encode audio instead of copy → switch `-c:a copy` to `-c:a aac -b:a 64k`
- Different fps → change `-vf "fps=15"`
- Different output folder or filename → override accordingly
- Non-screen-recording source (e.g. phone video, 30/60fps handheld footage):
  the `fps=15` default is a screen-recording assumption and will visibly hurt
  quality on normal footage — ask the user whether to keep native fps, use
  15fps anyway, or downscale to something in between (e.g. 30fps) before
  proceeding.
- "Original command" / no fps filter → drop `-vf "fps=15"` and raise the
  quality target accordingly (e.g. `-global_quality 35` on the GPU paths)

## Step 4 — Run & report

After each file completes, report:
- Input file and size
- Output file path and size
- Compression ratio achieved

## Notes

- `-c:a copy` (audio passthrough) is the default — it avoids re-encoding artifacts on low-bitrate audio. Only switch to AAC if the user asks or if the source audio is incompatible with the output container.
- If both `hevc_qsv` and `hevc_nvenc` fail (shouldn't happen on this machine per Step 1, but if the driver stack ever regresses), stop and report — do not silently fall back to `libsvtav1` without telling the user (it's much slower and pins the CPU).
- `ffprobe` can be used to inspect source bitrate before encoding if needed: `ffprobe -v error -show_entries format=bitrate,duration -of default=noprint_wrappers=1 "<input>"`
