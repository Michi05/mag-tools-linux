#!/usr/bin/env bash
# One-time setup: creates a venv and installs faster-whisper (CTranslate2).
# Does NOT download a model — faster-whisper downloads the chosen model
# (e.g. "medium", ~1.5GB) from Hugging Face on first run and caches it under
# ~/.cache/huggingface.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Setup complete. Run with:"
echo "  .venv/bin/python3 whisper_video_transcriber.py -a <file> [options]"
echo
echo "GPU (CUDA) note: faster-whisper needs cuDNN 9 + cuBLAS libraries findable"
echo "at runtime. If '--device cuda' fails to load, either:"
echo "  pip install nvidia-cudnn-cu12 nvidia-cublas-cu12"
echo "  (then add their lib dirs to LD_LIBRARY_PATH — see faster-whisper README)"
echo "or just use --device cpu (int8, slower but zero extra setup)."
