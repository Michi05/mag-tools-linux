#!/usr/bin/env python3
"""
Whisper transcription — video/audio input, CUDA-accelerated (faster-whisper).

Linux/GPU redesign of the Windows tool, not a straight port: the Windows
version targeted an Intel NPU via OpenVINO GenAI (openvino_genai.WhisperPipeline),
because that machine has an Intel NPU (Meteor Lake+) and no discrete GPU. This
machine is different hardware — an 11th-gen Intel CPU with NO NPU (NPU support
only shipped from Meteor Lake onward), but it DOES have a discrete NVIDIA RTX
3060 (6GB VRAM, CUDA 13 driver). So instead of reimplementing an NPU pipeline
that has no NPU to run on, this uses faster-whisper (CTranslate2) on CUDA —
simpler, well-supported on Linux, and a better fit for the hardware actually
here. CPU is the fallback device, same auto-fallback spirit as the original.

Preserves the same CLI shape and output formats (md/txt/srt/vtt) as the
Windows version so it's a drop-in replacement in scripts/skills that call it.

Differences worth knowing about:
  - --device now means cuda|cpu (no "NPU"/"GPU" OpenVINO device strings).
  - --beam-size > 1 is NOT degraded here (that was an NPU int8-model quirk) —
    CUDA handles real beam search fine; still defaults to 1 for speed.
  - --prompt (initial_prompt) does NOT crash here (that was NPU-specific) —
    freely usable.
  - --model takes a faster-whisper model name (tiny/base/small/medium/
    large-v3, or a local CTranslate2 model directory), not an OpenVINO
    int8 folder path.
"""

import subprocess
import tempfile
import time
import os
import sys
import argparse
from pathlib import Path

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.mts', '.m2ts'}
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}


def extract_audio_ffmpeg(input_path: Path) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", "-vn", tmp.name]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        os.unlink(tmp.name)
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    return Path(tmp.name)


def fmt_ts_srt(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds // 60) % 60
    h = int(seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_ts_vtt(seconds: float) -> str:
    return fmt_ts_srt(seconds).replace(",", ".")


def write_srt(segments, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{fmt_ts_srt(seg.start)} --> {fmt_ts_srt(seg.end)}\n{seg.text.strip()}\n\n")


def write_vtt(segments, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            f.write(f"{fmt_ts_vtt(seg.start)} --> {fmt_ts_vtt(seg.end)}\n{seg.text.strip()}\n\n")


def init_model(model_name: str, preferred: str):
    """Load a faster-whisper model, auto-falling back cuda -> cpu on failure."""
    from faster_whisper import WhisperModel

    chain = [preferred.lower()] + [d for d in ("cuda", "cpu") if d != preferred.lower()]
    for device in chain:
        compute_type = "float16" if device == "cuda" else "int8"
        try:
            print(f"Trying {device} ({compute_type})...")
            t0 = time.time()
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            print(f"Ready on {device} in {time.time() - t0:.2f}s")
            return model, device
        except Exception as e:
            print(f"{device} failed: {e}")
    raise RuntimeError("All devices failed.")


def transcribe_file(input_path: Path, model, used_device: str, args, formats: set):
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem

    print(f"\n--- {input_path.name} ---")
    temp_wav = None
    try:
        needs_extraction = input_path.suffix.lower() not in {".wav"}
        if needs_extraction:
            print("Extracting audio...")
            t0 = time.time()
            temp_wav = extract_audio_ffmpeg(input_path)
            print(f"Extracted in {time.time() - t0:.2f}s")
            audio_path = temp_wav
        else:
            audio_path = input_path

        print("Transcribing...")
        t0 = time.time()
        lang = args.lang.strip("<|>") or None  # accept both "en" and the old "<|en|>" token form
        segments_gen, info = model.transcribe(
            str(audio_path),
            language=lang,
            task="transcribe",
            beam_size=args.beam_size,
            repetition_penalty=args.repetition_penalty,
            initial_prompt=args.prompt,
        )
        segments = list(segments_gen)
        transcribe_time = time.time() - t0

        text = "".join(seg.text for seg in segments).strip()

        print(f"Done in {transcribe_time:.2f}s on {used_device} (detected language: {info.language})")

        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        if "txt" in formats:
            p = output_dir / f"{stem}.txt"
            p.write_text(text, encoding="utf-8")
            print(f"Saved: {p}")

        if "md" in formats:
            p = output_dir / f"{stem}.md"
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"# Transcription: {input_path.name}\n\n")
                f.write(f"| Field | Value |\n|---|---|\n")
                f.write(f"| Date | {ts} |\n")
                f.write(f"| Device | {used_device} |\n")
                f.write(f"| Model | {args.model} |\n")
                f.write(f"| Language | {info.language} |\n")
                f.write(f"| Beam size | {args.beam_size} |\n")
                f.write(f"| Repetition penalty | {args.repetition_penalty} |\n")
                if args.prompt:
                    f.write(f"| Initial prompt | {args.prompt} |\n")
                f.write(f"| Processing time | {transcribe_time:.2f}s |\n\n")
                f.write("## Text\n\n")
                f.write(text)
                if segments:
                    f.write("\n\n## Segments\n\n")
                    for seg in segments:
                        f.write(f"- `{fmt_ts_srt(seg.start).split(',')[0]}` {seg.text.strip()}\n")
            print(f"Saved: {p}")

        if "srt" in formats:
            if segments:
                p = output_dir / f"{stem}.srt"
                write_srt(segments, p)
                print(f"Saved: {p}")
            else:
                print("SRT skipped: no segments.")

        if "vtt" in formats:
            if segments:
                p = output_dir / f"{stem}.vtt"
                write_vtt(segments, p)
                print(f"Saved: {p}")
            else:
                print("VTT skipped: no segments.")

    except Exception as e:
        print(f"Error on {input_path.name}: {e}")
    finally:
        if temp_wav and temp_wav.exists():
            temp_wav.unlink()


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Whisper transcription — video/audio input, CUDA-accelerated (faster-whisper)")
    parser.add_argument("-a", "--audio", nargs="+", help="Input video or audio file(s)")
    parser.add_argument("--folder", help="Folder of video files to transcribe (sorted by name)")
    parser.add_argument("--model", default="medium", help="faster-whisper model name (tiny/base/small/medium/large-v3) or local CTranslate2 model dir")
    parser.add_argument("--device", default="cuda", help="Preferred device: cuda, cpu (auto-fallback cuda->cpu)")
    parser.add_argument("--lang", default="en", help="Language code, e.g. en, es (also accepts old <|en|> token form)")
    parser.add_argument("--beam-size", type=int, default=1, help="Beam search width (1=greedy/fast, 5=more accurate/slower)")
    parser.add_argument("--repetition-penalty", type=float, default=1.3, help="Penalty for repeated phrases (1.0=off, higher=stronger)")
    parser.add_argument("--prompt", default=None, help="Initial prompt to bias vocabulary (e.g. domain terms)")
    parser.add_argument("--output-dir", default=None, help="Output dir (default: same as each input file)")
    parser.add_argument("--formats", default="md,txt,srt", help="Output formats: md,txt,srt,vtt (comma-separated)")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        print("\n" + "!" * 60)
        print("MISSING DEPENDENCY: faster-whisper")
        print("!" * 60)
        print("\nRun setup.sh in this folder, or manually:")
        print("  python3 -m venv .venv")
        print("  source .venv/bin/activate")
        print("  pip install -r requirements.txt")
        print("\nSee README.md for CUDA/cuDNN notes (needed for --device cuda).")
        print("!" * 60 + "\n")
        sys.exit(1)

    # Build file list
    files = []
    if args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"Error: '{folder}' is not a directory.")
            sys.exit(1)
        files = sorted([f for f in folder.iterdir() if f.suffix.lower() in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS])
        if not files:
            print(f"No video/audio files found in '{folder}'.")
            sys.exit(1)
    elif args.audio:
        for a in args.audio:
            p = Path(a)
            if not p.exists():
                print(f"Error: '{p}' not found.")
                sys.exit(1)
            files.append(p)
    else:
        parser.error("Provide -a FILE [FILE ...] or --folder DIR")

    formats = {f.strip().lower() for f in args.formats.split(",")}

    print(f"--- Config ---")
    print(f"Files:    {len(files)}")
    print(f"Device:   {args.device} (fallback: cuda>cpu)")
    print(f"Model:    {args.model}")
    print(f"Language: {args.lang}")
    print(f"Beam size: {args.beam_size}")
    print(f"Rep. penalty: {args.repetition_penalty}")
    if args.prompt:
        print(f"Prompt:   {args.prompt}")
    print(f"Formats:  {', '.join(sorted(formats))}")
    print("-" * 14)

    # Load model once — GPU load happens here, not per file
    model, used_device = init_model(args.model, args.device)

    t_batch = time.time()
    for i, f in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}]", end="")
        transcribe_file(f, model, used_device, args, formats)

    if len(files) > 1:
        print(f"\n=== Batch done: {len(files)} files in {time.time() - t_batch:.0f}s ===")


if __name__ == "__main__":
    main()
