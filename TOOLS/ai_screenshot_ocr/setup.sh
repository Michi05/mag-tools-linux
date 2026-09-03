#!/usr/bin/env bash
# One-time setup: creates a venv and installs the OpenVINO GenAI stack.
# Does NOT download the model — the script downloads InternVL2-1B-int8-ov
# (~1GB) from Hugging Face on first run into this folder.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Setup complete. Run with:"
echo "  .venv/bin/python3 screenshot_metadata.py -i <image_file> [--device GPU|CPU]"
echo
echo "GPU note: --device GPU targets this machine's Intel Iris Xe iGPU via"
echo "OpenVINO's GPU plugin, which needs the Intel compute-runtime OpenCL"
echo "driver installed:"
echo "  sudo apt install intel-opencl-icd"
echo "If that's not installed or GPU init fails, use --device CPU instead."
