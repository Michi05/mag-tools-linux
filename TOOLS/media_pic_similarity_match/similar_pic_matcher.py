"""
similar_pic_matcher.py

Compute a color-based fingerprint for images and estimate similarity between
them, based on color balance (histogram in HSV space + color moments).

Usage:
    python similar_pic_matcher.py <folder> [--count N] [--bins B] [--all]

Examples:
    python similar_pic_matcher.py /path/to/photos              # first 10 images, sorted by name
    python similar_pic_matcher.py /path/to/photos --count 25    # first 25 images
    python similar_pic_matcher.py /path/to/photos --all         # every image in folder

See README.md in this folder for method details, decisions, and distance
thresholds ("same" / "similar" / "none").
"""

import argparse
from pathlib import Path
import numpy as np
from PIL import Image

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def list_images(folder: Path, count: int | None):
    imgs = sorted(p for p in folder.iterdir()
                   if p.suffix.lower() in IMAGE_EXTS and p.is_file())
    return imgs if count is None else imgs[:count]


def fingerprint(path: Path, bins: int):
    im = Image.open(path).convert("RGB")
    im = im.resize((128, 128))  # normalize size, cheap, kills per-pixel noise
    hsv = np.asarray(im.convert("HSV"), dtype=np.float32)

    h, s, v = hsv[..., 0].ravel(), hsv[..., 1].ravel(), hsv[..., 2].ravel()
    hist, _ = np.histogramdd(
        np.stack([h, s, v], axis=1),
        bins=(bins, bins, bins),
        range=((0, 256), (0, 256), (0, 256)),
    )
    hist = hist / hist.sum()  # normalize -> resolution/size independent

    moments = np.array([h.mean(), h.std(), s.mean(), s.std(), v.mean(), v.std()])
    return hist.ravel(), moments


def chi_square(a, b, eps=1e-10):
    return 0.5 * np.sum((a - b) ** 2 / (a + b + eps))


def euclidean(a, b):
    return np.linalg.norm(a - b)


def combined_distance_matrix(hists, moments):
    n = len(hists)
    hist_dist = np.zeros((n, n))
    mom_dist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            hist_dist[i, j] = chi_square(hists[i], hists[j])
            mom_dist[i, j] = euclidean(moments[i], moments[j])

    mom_max = mom_dist.max() if mom_dist.max() > 0 else 1
    hist_max = hist_dist.max() if hist_dist.max() > 0 else 1
    combined = (hist_dist / hist_max) * 0.7 + (mom_dist / mom_max) * 0.3
    return combined


def classify(dist: float) -> str:
    """Rough label based on initial 10-image test. See README for basis."""
    if dist < 0.15:
        return "SAME/near-duplicate"
    if dist < 0.30:
        return "similar"
    return "none"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path, help="Folder containing images")
    ap.add_argument("--count", type=int, default=10, help="Number of images to compare (default 10)")
    ap.add_argument("--all", action="store_true", help="Use all images in folder (overrides --count)")
    ap.add_argument("--bins", type=int, default=8, help="Histogram bins per HSV channel (default 8)")
    args = ap.parse_args()

    count = None if args.all else args.count
    paths = list_images(args.folder, count)
    if len(paths) < 2:
        print("Need at least 2 images to compare.")
        return

    print(f"Comparing {len(paths)} images from {args.folder}:")
    for p in paths:
        print(" -", p.name)
    print()

    hists, moments = [], []
    for p in paths:
        h, m = fingerprint(p, args.bins)
        hists.append(h)
        moments.append(m)

    combined = combined_distance_matrix(hists, moments)
    names = [p.name for p in paths]
    n = len(paths)

    print("=== Nearest match per image ===")
    for i in range(n):
        order = [j for j in np.argsort(combined[i]) if j != i]
        best = order[0]
        d = combined[i, best]
        print(f"{names[i]:35s} -> {names[best]:35s} dist={d:.4f} ({classify(d)})")

    print()
    print("=== Top similar pairs overall ===")
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((combined[i, j], names[i], names[j]))
    pairs.sort()
    top_n = min(10, len(pairs))
    for dist, a, b in pairs[:top_n]:
        print(f"{dist:.4f}  {classify(dist):20s} {a}  <->  {b}")


if __name__ == "__main__":
    main()
