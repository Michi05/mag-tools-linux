You are running a video compression task using FFmpeg with hardware AV1 encoding, optimized for screen recordings.

## Step 1 — Hardware & encoder discovery

Run these two checks before building any command:
```sh
lspci | grep -iE "vga|3d|display"
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "av1_(qsv|vaapi|nvenc)"
```

Based on GPU found:
- Intel iGPU (Gen 9.5+ / Iris Xe / Arc) → use `-c:v av1_qsv`, quality flag is `-global_quality` (this machine: confirmed `av1_qsv` available via the Iris Xe iGPU)
- NVIDIA RTX 40-series+, or RTX 30-series with a recent driver → use `-c:v av1_nvenc`, quality flag is `-cq` (this machine: confirmed `av1_nvenc` available via the RTX 3060)
- AMD RX 7000+ → use `-c:v av1_vaapi` (VAAPI is the Linux path for AMD; there's no `av1_amf` on Linux), quality flag is `-qp`
- No GPU AV1 encoder → use `-c:v libsvtav1` (CPU fallback, warn the user)

Default to `av1_qsv` on this machine (Intel iGPU) unless the user asks for the NVIDIA path — QSV leaves the discrete GPU free for other work (ML inference, etc.) and is the lower-power option for a background compression job.

## Step 2 — Resolve input

The user will provide a file name, file path, or folder. Resolve it:
- Single file: use it directly as `-i`
- Folder: find all `.mp4`, `.mkv`, `.mov`, `.avi` files in that folder and process each in sequence

If no input is provided, ask for it before proceeding.

## Step 3 — Build the command

**Default profile (screen recordings):**
```sh
ffmpeg -y -loglevel error -stats \
  -i "<input>" \
  -vf "fps=15" \
  -c:v av1_qsv \
  -global_quality 20 \
  -preset veryslow \
  -c:a copy \
  "<output>"
```

**Output location (default):** `~/Videos/mag_compressed/<original_name>_AV1.mp4`
Create the output folder if it doesn't exist (`mkdir -p`).

**Adapt the command if the user requests a variation**, e.g.:
- Higher/lower quality → adjust `-global_quality` (1=lossless, 51=lowest; 20 is default)
- Re-encode audio instead of copy → switch `-c:a copy` to `-c:a aac -b:a 64k`
- Different fps → change `-vf "fps=15"`
- Different output folder or filename → override accordingly
- NVIDIA path → swap to `-c:v av1_nvenc -cq 20` (drop `-preset veryslow`, NVENC uses `-preset p1..p7` instead if tuning is needed)
- "Original command" / no fps filter → drop `-vf "fps=15"` and use `-global_quality 35 -c:a aac -b:a 64k`

## Step 4 — Run & report

After each file completes, report:
- Input file and size
- Output file path and size
- Compression ratio achieved

## Notes

- `-c:a copy` (audio passthrough) is the default — it avoids re-encoding artifacts on low-bitrate audio. Only switch to AAC if the user asks or if the source audio is incompatible with the output container.
- If the encoder check fails (neither `av1_qsv` nor `av1_nvenc` found), stop and report — do not silently fall back to `libsvtav1` without telling the user (it's much slower).
- `ffprobe` can be used to inspect source bitrate before encoding if needed: `ffprobe -v error -show_entries format=bitrate,duration -of default=noprint_wrappers=1 "<input>"`
