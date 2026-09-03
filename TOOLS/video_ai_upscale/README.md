# video_ai_upscale

Upscales a video using Real-ESRGAN (ncnn-vulkan build) — GAN-based
super-resolution, sharper than classic Lanczos/bicubic scaling. Runs via
Vulkan on any GPU. This machine's Vulkan 1.3.275 instance was confirmed
present (`vulkaninfo --summary`), backed by either the Intel Iris Xe iGPU or
the NVIDIA RTX 3060.

## What changed from the Windows version

Only the binary: the Windows tool bundled `realesrgan-ncnn-vulkan.exe`. The
same upstream project ships a Linux build too — download it yourself (not
fetched as part of this repo build, per the scope of this port):

```
# From https://github.com/xinntao/Real-ESRGAN/releases — grab the
# realesrgan-ncnn-vulkan-*-ubuntu.zip asset, then:
unzip realesrgan-ncnn-vulkan-*-ubuntu.zip -d /tmp/realesrgan
cp /tmp/realesrgan/realesrgan-ncnn-vulkan /tmp/realesrgan/*.param /tmp/realesrgan/*.bin \
   TOOLS/video_ai_upscale/   # actually: copy the binary + the whole models/ folder, see below
```
Concretely: copy the `realesrgan-ncnn-vulkan` binary and the `models/`
subfolder from the release archive into this tool's folder, then:
```
chmod +x realesrgan-ncnn-vulkan
```
The Python wrapper logic (extract frames → upscale each → re-encode with
original audio) is otherwise unchanged — it was never Windows-specific.

## Usage

```
python3 upscale_video.py <input_video> <output_video> [--scale 2|3|4] [--model realesrgan-x4plus|realesr-animevideov3|realesrgan-x4plus-anime] [--keep-frames]
```

## Requirements

- `ffmpeg`/`ffprobe` on PATH (already installed system-wide on this machine).
- `realesrgan-ncnn-vulkan` binary + `models/` folder in this tool's folder
  (see above — not fetched yet).
- A Vulkan-capable GPU (confirmed present).

Note: extracting/upscaling/re-encoding all frames as lossless PNGs uses
significant temp disk space and time for longer clips (429GB free on this
machine at the time of writing, so headroom isn't the concern — time is).
