# ai_screenshot_ocr

Runs a local vision-language model (InternVL2-1B INT8 via OpenVINO GenAI) on
an image to extract context, a short title, and a one-sentence description.
Proposes a structured filename. Exports a `.json` metadata file.

## Why this stayed on OpenVINO (unlike the Whisper tool)

Unlike the Whisper tool, this one did **not** need an engine swap: OpenVINO
GenAI's GPU plugin runs on Linux via Intel's compute-runtime, and this
machine's Intel Iris Xe iGPU (TigerLake-LP) is exactly the kind of device the
original script's `--device GPU` default already targeted. So the logic here
is unchanged from the Windows version — same model, same prompt, same JSON
schema, same OpenVINO GenAI APIs. Only the setup instructions changed
(pip/venv on Linux instead of PowerShell venv activation), and the
troubleshooting note now points at `intel-opencl-icd` (the Linux OpenCL
driver package) instead of a Windows GPU driver update.

The original repo also had this at `TOOLS/AI02_LocalCaptureOCR/` after a
manual rename that its own `TOOLS.md` never caught up with (see the audit of
that repo). This port keeps the original `ai_screenshot_ocr` category-prefixed
name throughout — script, docs, and folder all agree, instead of drifting.

## Usage

```
.venv/bin/python3 screenshot_metadata.py -i <image_file> [options]
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-i` / `--image` | Yes | — | Path to image file (JPG, PNG, BMP) |
| `--model` | No | `InternVL2-1B-int8-ov` | Path to OpenVINO model folder |
| `--device` | No | `GPU` | `GPU` (Intel Iris Xe) or `CPU` |

**Output:** console summary (context, proposed filename, inference time) and
`<image_filename>.json` with the full analysis + timing stats.

## Setup

```
./setup.sh
```
Creates `.venv/`, installs `openvino-genai` + deps. The model (~1GB)
downloads from Hugging Face on first run into this folder — **not done as
part of this repo build**; run it yourself when ready for that download.

**GPU note:** needs the Intel OpenCL driver: `sudo apt install intel-opencl-icd`.
Without it, GPU init fails and you should pass `--device CPU`.
