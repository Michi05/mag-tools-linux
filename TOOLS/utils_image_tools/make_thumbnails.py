#!/usr/bin/env python3
"""
make_thumbnails.py
Generates thumbnails for all JPG files in a folder.
Thumbnails are saved to a 'thumbnails/' subfolder with a '_thumb' suffix.

Usage:
    python make_thumbnails.py               # uses folder of this script
    python make_thumbnails.py /some/path    # uses specified folder
"""

import sys
from pathlib import Path
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
MAX_SIDE   = 1024          # longest side in pixels
QUALITY    = 72            # JPEG quality (0-100); 70-75 is a good analysis sweet spot
SUFFIX     = "_thumb"      # appended before the extension
OUT_FOLDER = "thumbnails"  # subfolder name
# ──────────────────────────────────────────────────────────────────────────────

def make_thumbnails(source_dir: Path):
    out_dir = source_dir / OUT_FOLDER
    out_dir.mkdir(exist_ok=True)

    images = sorted(source_dir.glob("*.jpg")) + sorted(source_dir.glob("*.JPG"))
    if not images:
        print("No JPG files found.")
        return

    print(f"Found {len(images)} image(s) → saving to {out_dir}/")

    for img_path in images:
        out_name = img_path.stem + SUFFIX + ".jpg"
        out_path = out_dir / out_name

        with Image.open(img_path) as im:
            im = im.convert("RGB")           # normalise (handles RGBA etc.)
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            im.save(out_path, "JPEG", quality=QUALITY, optimize=True,
                    exif=b"")               # strip EXIF metadata

        print(f"  {img_path.name}  →  {out_name}  ({out_path.stat().st_size // 1024} KB)")

    print("Done.")

if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    make_thumbnails(folder.resolve())
