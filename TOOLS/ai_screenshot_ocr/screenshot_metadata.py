from pathlib import Path
import datetime
import os
import argparse
import json
import sys
import time

# Heavy deps (openvino-genai etc.) are imported lazily inside main(), after
# argument parsing — so `--help` and argparse errors work even before
# setup.sh has been run, giving a meaningful basic health check.

# Configuration
# InternVL2-1B is a specialized "OCR Beast" model in INT8 format
DEFAULT_MODEL_ID = "OpenVINO/InternVL2-1B-int8-ov"
DEFAULT_MODEL_DIR = "InternVL2-1B-int8-ov"

def download_model(model_id, model_dir):
    path = Path(model_dir)
    if not path.exists():
        print(f"Downloading model {model_id} (Specialized INT8 VLM)...")
        snapshot_download(repo_id=model_id, local_dir=path)
        print("Download complete.")
    return str(path)

def load_image(path):
    # Standard image loading for OpenVINO GenAI
    pic = Image.open(path).convert("RGB")
    image_data = np.array(pic)
    return ov.Tensor(image_data)

def main():
    parser = argparse.ArgumentParser(description="Image Metadata Extraction using InternVL2 (OpenVINO INT8)")

    parser.add_argument(
        "-i", "--image",
        type=str,
        required=True,
        help="Path to the image file (Mandatory)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_DIR,
        help=f"Path to the OpenVINO model folder. Default: {DEFAULT_MODEL_DIR}"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="GPU",
        help="Device to run inference on (GPU or CPU). Default is GPU (targets the Intel iGPU on this machine)."
    )

    args = parser.parse_args()

    global ov_genai, ov, np, Image, snapshot_download
    try:
        import openvino_genai as ov_genai
        import openvino as ov
        import numpy as np
        from PIL import Image
        from huggingface_hub import snapshot_download
    except ImportError:
        print("\n" + "!" * 60)
        print("MISSING DEPENDENCIES DETECTED")
        print("!" * 60)
        print("\nThis script requires a specific OpenVINO GenAI environment.")
        print("\nEXPECTED SETUP:")
        print("1. Python 3.10 - 3.12")
        print("2. Virtual Environment (.venv)")
        print("3. Required Libraries: openvino-genai, openvino, pillow, numpy, huggingface_hub")
        print("\nQUICK FIX:")
        print("  ./setup.sh")
        print("  # or manually:")
        print("  python3 -m venv .venv")
        print("  source .venv/bin/activate")
        print("  pip install openvino-genai openvino huggingface_hub pillow numpy")
        print("\n" + "!" * 60 + "\n")
        sys.exit(1)

    # Ensure model is present
    model_path = download_model(DEFAULT_MODEL_ID, args.model)

    if not os.path.exists(args.image):
        print(f"Error: Image file '{args.image}' not found.")
        return

    print(f"--- Configuration ---")
    print(f"Device: {args.device}")
    print(f"Image:  {args.image}")
    print("-" * 22)

    try:
        print(f"Initializing InternVL2 Pipeline on {args.device}...")
        start_init = time.time()
        pipe = ov_genai.VLMPipeline(model_path, args.device)
        end_init = time.time()
        init_time = end_init - start_init

        # Load image as OpenVINO Tensor
        ov_image = load_image(args.image)

        # Unified prompt for context and relevance using InternVL2 tags
        prompt = (
            "<|user|>\n<image>\n"
            "Analyze this screenshot. Provide the following in JSON format:\n"
            "1. context: (App type, e.g. 'Web Browser', 'Terminal', 'Spreadsheet')\n"
            "2. relevance: (The most unique and relevant readable title or heading, max 5 words)\n"
            "3. description: (A brief 1-sentence summary)\n"
            "Strictly return only the JSON block."
            "<|end|>\n<|assistant|>\n"
        )

        print("Generating metadata (Inference)...")
        start_inference = time.time()
        result = pipe.generate(prompt, image=ov_image, max_new_tokens=200)
        end_inference = time.time()
        inference_time = end_inference - start_inference

        # Parse AI output
        output_text = result.texts[0].strip()
        json_str = output_text.replace("```json", "").replace("```", "").strip()

        try:
            ai_meta = json.loads(json_str)
        except Exception:
            print("Warning: Model output was not valid JSON. Using fallback parsing.")
            ai_meta = {
                "context": "Screenshot",
                "relevance": "Analysis",
                "description": output_text[:100]
            }

        # Date Logic (YYMMDD)
        creation_time = os.path.getctime(args.image)
        date_str = datetime.datetime.fromtimestamp(creation_time).strftime("%y%m%d")

        # Assemble Proposed Name
        proposed_name = f"{ai_meta.get('context', 'Context')} - {ai_meta.get('relevance', 'Relevance')} _ {date_str}"

        # Metadata Object
        metadata = {
            "original_filename": Path(args.image).name,
            "proposed_filename": proposed_name,
            "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ai_analysis": ai_meta,
            "file_date_tag": date_str,
            "device_used": args.device,
            "performance": {
                "init_time_seconds": round(init_time, 2),
                "inference_time_seconds": round(inference_time, 2),
                "total_time_seconds": round(init_time + inference_time, 2)
            }
        }

        # Export to JSON
        output_path = Path(args.image).with_suffix(".json")
        print(f"Exporting metadata to: {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        print("\n--- Summary ---")
        print(f"Context:       {ai_meta.get('context')}")
        print(f"Proposed Name: {proposed_name}")
        print(f"Inference Time: {inference_time:.2f}s")
        print("Done!")

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
