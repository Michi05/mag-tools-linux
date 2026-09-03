#!/usr/bin/env python3
"""AI-upscale a video with Real-ESRGAN (ncnn-vulkan), Linux build.

The ncnn-vulkan binary only works on still images, so this wrapper extracts
frames with ffmpeg, upscales each frame, then re-encodes back to video at the
original fps with the original audio muxed back in. Same approach as the
Windows tool; the only real difference is the binary name (no .exe) and that
it runs over the same Vulkan API either way — this machine's Vulkan 1.3
instance (Intel Iris Xe + NVIDIA RTX 3060, either can run this) was confirmed
present.
"""

import argparse
import os
import shutil
import subprocess
import sys
from time import time

# Folder this script lives in (holds the ncnn-vulkan binary + models/)
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
UPSCALER_BIN = os.path.join(TOOL_DIR, "realesrgan-ncnn-vulkan")
MODELS_DIR = os.path.join(TOOL_DIR, "models")


def check_binary():
    if not os.path.exists(UPSCALER_BIN):
        print(f"ERROR: {UPSCALER_BIN} not found.")
        print("Download the Linux build from:")
        print("  https://github.com/xinntao/Real-ESRGAN/releases")
        print(f"  (look for realesrgan-ncnn-vulkan-*-ubuntu.zip), extract the")
        print(f"  'realesrgan-ncnn-vulkan' binary and its 'models/' folder into:")
        print(f"  {TOOL_DIR}/")
        print("Then: chmod +x realesrgan-ncnn-vulkan")
        sys.exit(1)
    if not os.access(UPSCALER_BIN, os.X_OK):
        print(f"ERROR: {UPSCALER_BIN} is not executable. Run: chmod +x {UPSCALER_BIN}")
        sys.exit(1)


def get_fps(input_video):
    # Ask ffprobe for the exact input frame rate (as a fraction string, e.g. "30000/1001")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", input_video],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def extract_frames(input_video, frames_dir):
    os.makedirs(frames_dir, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_video, "-q:v", "1",
         os.path.join(frames_dir, "frame_%08d.png")],
        check=True,
    )


def upscale_frames(frames_dir, upscaled_dir, model, scale):
    os.makedirs(upscaled_dir, exist_ok=True)
    subprocess.run(
        [UPSCALER_BIN,
         "-i", frames_dir,
         "-o", upscaled_dir,
         "-s", str(scale),
         "-n", model,
         "-m", MODELS_DIR,
         "-f", "png"],
        check=True,
    )


def encode_video(upscaled_dir, input_video, output_video, fps):
    subprocess.run(
        ["ffmpeg", "-y",
         "-framerate", fps,
         "-i", os.path.join(upscaled_dir, "frame_%08d.png"),
         "-i", input_video,
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
         "-c:a", "copy",
         output_video],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-upscale a video with Real-ESRGAN (ncnn-vulkan)")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("output_video", help="Output video file")
    parser.add_argument("--scale", type=int, default=2, choices=[2, 3, 4],
                         help="Upscale factor (default=2; 4x on already-1080p+ sources is usually overkill/slow)")
    parser.add_argument("--model", default="realesrgan-x4plus",
                         choices=["realesrgan-x4plus", "realesr-animevideov3", "realesrgan-x4plus-anime"],
                         help="Model: realesrgan-x4plus (general/realistic, default) or "
                              "realesr-animevideov3 (animation, faster)")
    parser.add_argument("--keep-frames", action="store_true", help="Don't delete temp frame folders when done")
    args = parser.parse_args()

    check_binary()

    if not os.path.exists(args.input_video):
        print(f"ERROR: {args.input_video} not found!")
        sys.exit(1)

    work_dir = os.path.join(os.path.dirname(os.path.abspath(args.output_video)), "_upscale_tmp")
    frames_dir = os.path.join(work_dir, "frames")
    upscaled_dir = os.path.join(work_dir, "upscaled")

    tic = time()

    print("Reading source frame rate...")
    fps = get_fps(args.input_video)
    print(f"  fps = {fps}")

    print("Extracting frames...")
    extract_frames(args.input_video, frames_dir)

    print(f"Upscaling frames with {args.model} (scale={args.scale}x)...")
    upscale_frames(frames_dir, upscaled_dir, args.model, args.scale)

    print("Re-encoding video (muxing original audio back in)...")
    encode_video(upscaled_dir, args.input_video, args.output_video, fps)

    if not args.keep_frames:
        print("Cleaning up temp frames...")
        shutil.rmtree(work_dir, ignore_errors=True)

    print(f"Done in {time() - tic:.1f}s. Saved {args.output_video}")
