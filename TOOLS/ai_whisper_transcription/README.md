# ai_whisper_transcription

Transcribes video/audio files locally. **Redesigned, not just ported** — see
why below.

## Why this isn't a straight port

The Windows tool ran Whisper via OpenVINO GenAI on an **Intel NPU**
(`ov_genai.WhisperPipeline(model_path, device="NPU")`, with GPU/CPU fallback).
That only makes sense on hardware with an Intel NPU (Meteor Lake and later).

This machine (Linux Mint laptop, 11th-gen Intel Core i7-11370H / TigerLake)
**has no NPU** — NPU support didn't exist until Meteor Lake, several
generations later. Trying to reproduce the NPU pipeline here would just fail
at pipeline init on every run. What it *does* have that the original box
didn't: a discrete **NVIDIA RTX 3060 (6GB VRAM, CUDA 13 driver)**, currently
sitting unused. So this port switches engines entirely: **faster-whisper**
(CTranslate2) on CUDA, falling back to CPU. This is simpler to set up than
OpenVINO GenAI, well-supported on Linux, and actually uses the hardware this
machine has.

Practical fallout of the engine swap (documented in the script's own
docstring too):
- `--device` is now `cuda`/`cpu`, not `NPU`/`GPU`/`CPU`.
- `--beam-size > 1` is NOT degraded on this engine (that was an NPU int8
  quirk specific to OpenVINO's implementation) — real beam search works fine
  on CUDA; default is still 1 for speed.
- `--prompt` (initial prompt) does not crash here (also NPU-specific).
- `--model` takes a faster-whisper model name (`tiny`/`base`/`small`/
  `medium`/`large-v3`) instead of a path to a pre-converted OpenVINO int8
  model folder — faster-whisper downloads and caches it itself.

Everything else — the CLI shape, batching, `md`/`txt`/`srt`/`vtt` output,
ffmpeg audio extraction — is preserved so it's a drop-in replacement for
scripts/skills built against the original.

## Usage

```
.venv/bin/python3 whisper_video_transcriber.py -a <input_file> [options]

# Batch an entire folder (recommended — one model load for all files):
.venv/bin/python3 whisper_video_transcriber.py --folder <folder_of_videos>
```

| Flag | Default | Description |
|------|---------|-------------|
| `-a` / `--audio` | — | Input video/audio file(s), space-separated |
| `--folder` | — | Folder of video/audio files, sorted by name |
| `--model` | `medium` | faster-whisper model name or local CTranslate2 model dir |
| `--device` | `cuda` | Preferred device; auto-falls back cuda→cpu |
| `--lang` | `en` | Language code (`en`, `es`, ...) |
| `--beam-size` | `1` | Beam width — raise for accuracy, costs speed |
| `--repetition-penalty` | `1.3` | Suppresses repeat-phrase hallucination |
| `--prompt` | none | Initial prompt to bias vocabulary |
| `--output-dir` | same folder as input | Where to write outputs |
| `--formats` | `md,txt,srt` | Comma-separated: `md,txt,srt,vtt` |

## Setup

**Prerequisite:** `python3.12-venv` must be installed system-wide first
(`sudo apt install python3.12-venv`) — `setup.sh` calls `python3 -m venv`,
which silently produces a broken venv (missing `pip`) if this package isn't
present. See Troubleshooting below if you hit this.

```
./setup.sh
```
Creates `.venv/`, installs `faster-whisper`. The model itself (e.g. `medium`,
~1.5GB) downloads from Hugging Face on first run, cached under
`~/.cache/huggingface`. **Not done as part of this repo build** — run
`setup.sh` and a first transcription yourself when you're ready to pull that
download.

**GPU note:** CUDA acceleration needs cuDNN 9 + cuBLAS reachable at runtime.
If CUDA fails to load, either install
`nvidia-cudnn-cu12 nvidia-cublas-cu12` via pip into `.venv` and point
`LD_LIBRARY_PATH` at their lib folders (see Troubleshooting below), or just
run with `--device cpu` (int8, slower, zero extra setup — this CPU handles it
fine for short files).

## Troubleshooting

**`setup.sh` fails with "ensurepip is not available"**
`python3 -m venv` needs `python3.12-venv` installed system-wide. Fix:
```
sudo apt install python3.12-venv
```
Then re-run `./setup.sh`.

**`.venv/bin/pip: No such file or directory` (or any `pip install` into
`.venv` fails this way)**
The venv was created before `python3.12-venv` was installed, so it's missing
`pip` (only `python`/`python3`/`python3.12` exist under `.venv/bin/`). A venv
in this state can't be repaired in place — delete and recreate it:
```
rm -rf .venv
./setup.sh
```

**`Error on <file>: Library libcublas.so.12 is not found or cannot be
loaded`**
This shows up *during transcription*, not at startup — the tool's own
cuda→cpu fallback only tests device init (which succeeds), so the error
surfaces per-file once transcription actually starts, and the run reports
`[exited with code 0]` with no output files. cuDNN 9 / cuBLAS aren't on the
system and aren't installed in the venv. Fix — install them via pip and put
their lib dirs on `LD_LIBRARY_PATH` for the run:
```sh
.venv/bin/pip install nvidia-cudnn-cu12 nvidia-cublas-cu12

VENV_SITE="$(.venv/bin/python3 -c "import site; print(site.getsitepackages()[0])")"
export LD_LIBRARY_PATH="$VENV_SITE/nvidia/cudnn/lib:$VENV_SITE/nvidia/cublas/lib:${LD_LIBRARY_PATH:-}"

.venv/bin/python3 whisper_video_transcriber.py -a <input_file> [options]
```
`LD_LIBRARY_PATH` only lasts for the current shell session — export it again
(or add to your shell profile) for future runs, or just use `--device cpu`
to skip CUDA entirely.

**Wrong-language transcription / garbled output**
`--lang` defaults to `en`. If the source audio isn't English, pass the
correct code explicitly (e.g. `--lang es`) — the model won't reliably
auto-detect if forced to the wrong language.
