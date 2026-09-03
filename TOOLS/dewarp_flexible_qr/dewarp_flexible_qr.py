"""
Dewarp a QR/barcode (or any square/rectangular label) printed on a flexible,
wrinkled surface (fabric pouches, soft plastic bags, curved labels) so that
standard decoders (pyzbar, zxing-cpp, cv2.QRCodeDetector) can read it.

Why this exists
----------------
A plain 4-point perspective transform (cv2.getPerspectiveTransform /
cv2.warpPerspective) only corrects *planar* perspective distortion. It does
NOT fix non-planar distortion caused by a bent/wrinkled surface (e.g. a QR
printed on a pet-food pouch that bulges in the middle). In that case the
edges of the code are curved, not straight, and a 4-corner homography still
leaves the code undecodable.

This script instead:
  1. Segments the label/panel the code sits on from its background (by HSV
     saturation contrast — works when the panel is white/gray/silver and the
     background is a saturated color like the yellow pouch in our case).
  2. Extracts the FULL contour of that panel (not just 4 corners) — this
     contour follows the actual (curved) edge of the panel in the photo.
  3. Splits the contour into 4 sides using the 4 dominant corners
     (cv2.approxPolyDP), resamples each side by arc length.
  4. Fits a Thin Plate Spline (TPS) that maps every one of those boundary
     points to its ideal position on a perfect square. TPS is a smooth
     non-rigid warp — unlike a homography it can absorb the local bulges/
     wrinkles instead of just the global 4-corner skew.
  5. Applies the resulting dense per-pixel map with cv2.remap to produce a
     squared-up image, then (optionally) tries to decode it.

Approaches tried and REJECTED before landing on this one (don't re-try them
first — they were all tested against a real wrinkled-pouch QR and failed):
  - cv2.QRCodeDetector().detectAndDecode() directly on the photo / crops /
    upscaled crops / Otsu-thresholded crops.
  - cv2.QRCodeDetectorAruco() (same failure mode).
  - pyzbar.decode() directly on the photo / crops / upscaled crops.
  - zxing-cpp (zxingcpp.read_barcodes) directly on the photo / crops.
  - Plain 4-point perspective correction (cv2.getPerspectiveTransform) using
    the 4 corners reported by cv2.QRCodeDetector — still failed because the
    distortion is non-planar (bag wrinkle), not just perspective skew.
  - Adaptive thresholding / histogram equalization on the above — no effect,
    the problem is geometric, not exposure/contrast.
  => TPS dewarping using the FULL panel contour is what actually worked.

Requirements
------------
    pip install opencv-python-headless scipy pyzbar pillow
    # zxing-cpp is optional, tried as an extra decode backend:
    pip install zxing-cpp
    # pyzbar needs the system libzbar0 shared library on Linux:
    sudo apt install libzbar0

Quick start (CLI)
-----------------
    python dewarp_flexible_qr.py INPUT.jpg --crop 2750,1350,3550,2100 --decode

    python dewarp_flexible_qr.py INPUT.jpg --decode --save-debug out_dir/

Quick start (as a library)
---------------------------
    from dewarp_flexible_qr import dewarp_panel, decode_image
    import cv2

    img = cv2.imread("INPUT.jpg")
    crop = img[1350:2100, 2750:3550]          # optional but recommended: crop
                                                # tightly around the code first,
                                                # segmentation is more reliable
                                                # on a smaller, less cluttered
                                                # region.
    dewarped = dewarp_panel(crop)              # -> np.ndarray (BGR) or None
    if dewarped is not None:
        text = decode_image(dewarped)          # -> str or None

CLI arguments
-------------
    input                   Path to the source photo (any format cv2 can read).
    --crop X1,Y1,X2,Y2      Pixel box (in the ORIGINAL/full image) to crop
                             before processing. Strongly recommended: find
                             the rough box first (eyeball it, or run once
                             without --crop and look at --save-debug output),
                             then re-run with a tight crop for a cleaner
                             segmentation. Default: whole image.
    --sat-thresh N          HSV saturation threshold (0-255) used to separate
                             a low-saturation panel from a saturated
                             background. Default: 90. Lower it if the panel
                             isn't being picked up (mask empty); raise it if
                             background is leaking into the mask. Only
                             works when panel vs. background contrast is a
                             SATURATION difference (e.g. white/gray/silver
                             panel on a colored background). If your
                             panel/background differ by brightness instead,
                             see --channel.
    --channel {sat,gray}    Which channel to threshold on. "sat" = HSV
                             saturation (default, best for colored
                             background + neutral panel). "gray" = plain
                             grayscale brightness (use when panel is
                             darker/lighter than background but similarly
                             saturated).
    --invert                Invert the threshold direction (use if the panel
                             ends up as the background of the mask instead
                             of the foreground — check --save-debug mask.png).
    --output-size N         Side length in pixels of the square output image.
                             Default: 700.
    --n-per-side N          How many points to sample per side of the panel
                             contour for the TPS fit. More points = more
                             faithful to local wrinkles, but slower and more
                             sensitive to contour noise. Default: 60.
    --smoothing F           TPS regularization (scipy RBFInterpolator
                             `smoothing` param). 0 = interpolate exactly
                             through every contour point (can overfit to
                             pixel noise in the contour). Higher = smoother,
                             more forgiving of a noisy contour. Default: 2.0.
                             Try 5-10 if the contour is jittery (JPEG noise,
                             printed text overlapping the panel edge).
    --decode                After dewarping, try to decode a barcode/QR from
                             the result (pyzbar first, then zxing-cpp if
                             installed, then cv2.QRCodeDetector) and print
                             the decoded text to stdout.
    --output PATH            Where to save the dewarped image. Default:
                             "<input_stem>_dewarped.png" next to the input.
    --save-debug DIR         If set, also saves intermediate images to DIR:
                             01_crop.png, 02_mask.png, 03_contour.png,
                             04_dewarped.png. Use this to diagnose why
                             segmentation/decoding isn't working.

Output
------
    A squared-up BGR image (np.ndarray, or written to --output as PNG).
    With --decode, the decoded string is also printed to stdout as
    "DECODED: <text>" (or "DECODED: <none>" if nothing was readable).

Limitations / when this will NOT help
--------------------------------------
    - Needs the panel (the thing that "should be square/rectangular") to be
      distinguishable from its background by color/brightness contrast.
      Pure edge-based fallback isn't implemented — if HSV segmentation can't
      isolate the panel, this approach doesn't apply as-is (would need a
      different segmentation strategy, e.g. edge/line detection).
    - Assumes the panel's TRUE shape is a rectangle/square (the whole point
      is mapping its wrinkled contour back to a perfect square). Don't use
      this for genuinely non-rectangular targets.
    - TPS is a 2D warp of the flattened photo, not a physical 3D unwrap — it
      works because paper/foil labels are close to inextensible (bending,
      not stretching), so equal arc-length spacing along the photographed
      edge is a reasonable proxy for equal spacing on the flat label. Highly
      stretched/deformed material may not dewarp cleanly.
"""

import argparse
import os
import sys

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def segment_panel(image, sat_thresh=90, channel="sat", invert=False):
    """Return a binary mask (uint8, 0/255) isolating the panel from its background."""
    if channel == "sat":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        chan = hsv[:, :, 1]
    else:
        chan = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    thresh_type = cv2.THRESH_BINARY if invert else cv2.THRESH_BINARY_INV
    _, mask = cv2.threshold(chan, sat_thresh, 255, thresh_type)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return mask


def largest_contour(mask):
    """Return the largest external contour in the mask as an (N,2) float64 array, or None."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    return cnt.reshape(-1, 2).astype(np.float64)


def find_quad_corners(cnt, epsilon_frac=0.02):
    """Approximate the contour to 4 corners. Returns (corners(4,2), corner_indices sorted)."""
    peri = cv2.arcLength(cnt.reshape(-1, 1, 2).astype(np.int32), True)
    approx = cv2.approxPolyDP(cnt.reshape(-1, 1, 2).astype(np.int32), epsilon_frac * peri, True)
    approx = approx.reshape(-1, 2)
    if len(approx) != 4:
        return None, None

    def closest_idx(pt):
        d = np.sum((cnt - pt) ** 2, axis=1)
        return int(np.argmin(d))

    corner_idx = sorted(closest_idx(p) for p in approx)
    return approx, corner_idx


def _resample_by_arclength(seg, n):
    d = np.sqrt(((np.diff(seg, axis=0)) ** 2).sum(axis=1))
    cum = np.concatenate([[0], np.cumsum(d)])
    total = cum[-1]
    ts = np.linspace(0, total, n, endpoint=False)
    xs = np.interp(ts, cum, seg[:, 0])
    ys = np.interp(ts, cum, seg[:, 1])
    return np.stack([xs, ys], axis=1)


def _slice_wrap(a, i0, i1):
    return a[i0:i1 + 1] if i0 <= i1 else np.vstack([a[i0:], a[:i1 + 1]])


def build_boundary_correspondences(cnt, corner_idx, output_size, n_per_side=60):
    """
    Walk the 4 sides of the contour (between consecutive corners) and build
    matched (source_pixel, target_square_pixel) point pairs for the TPS fit.
    Target square has corners (0,0) (0,Wt) (Wt,Wt) (Wt,0) in the same winding
    order as the contour's corner sequence.
    """
    sides = [_slice_wrap(cnt, corner_idx[k], corner_idx[(k + 1) % 4]) for k in range(4)]
    Wt = output_size
    src_pts, tgt_pts = [], []
    for k, seg in enumerate(sides):
        rs = _resample_by_arclength(seg, n_per_side)
        for i, (x, y) in enumerate(rs):
            t = i / n_per_side
            if k == 0:
                tx, ty = 0, t * Wt
            elif k == 1:
                tx, ty = t * Wt, Wt
            elif k == 2:
                tx, ty = Wt, (1 - t) * Wt
            else:
                tx, ty = (1 - t) * Wt, 0
            src_pts.append([x, y])
            tgt_pts.append([tx, ty])
    return np.array(src_pts), np.array(tgt_pts)


def tps_dewarp(image, src_pts, tgt_pts, output_size, smoothing=2.0):
    """Fit target->source TPS and remap `image` into an output_size x output_size square."""
    rbf = RBFInterpolator(tgt_pts, src_pts, kernel="thin_plate_spline", smoothing=smoothing)
    Wt = output_size
    gy, gx = np.mgrid[0:Wt, 0:Wt]
    grid_pts = np.stack([gx.ravel(), gy.ravel()], axis=1).astype(np.float64)
    mapped = rbf(grid_pts)
    map_x = mapped[:, 0].reshape(Wt, Wt).astype(np.float32)
    map_y = mapped[:, 1].reshape(Wt, Wt).astype(np.float32)
    return cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def dewarp_panel(image, sat_thresh=90, channel="sat", invert=False,
                  output_size=700, n_per_side=60, smoothing=2.0,
                  epsilon_frac=0.02, debug_dir=None):
    """
    Full pipeline: segment -> contour -> 4-corner split -> TPS -> remap.

    Parameters
    ----------
    image : np.ndarray (BGR)
        Already cropped (recommended) region containing the wrinkled panel.
    sat_thresh, channel, invert : see segment_panel().
    output_size : int
        Side length of the returned square image.
    n_per_side : int
        Points sampled per side for the TPS fit.
    smoothing : float
        TPS regularization, see module docstring.
    epsilon_frac : float
        approxPolyDP epsilon as a fraction of contour perimeter, used to find
        the 4 corners. Increase if approxPolyDP returns != 4 points on a
        noisy contour; decrease if it collapses real corners together.
    debug_dir : str or None
        If given, writes 01_crop.png / 02_mask.png / 03_contour.png /
        04_dewarped.png into this directory.

    Returns
    -------
    np.ndarray (BGR, output_size x output_size) or None if segmentation/
    corner-detection failed.
    """
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, "01_crop.png"), image)

    mask = segment_panel(image, sat_thresh=sat_thresh, channel=channel, invert=invert)
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "02_mask.png"), mask)

    cnt = largest_contour(mask)
    if cnt is None or len(cnt) < 4:
        return None

    corners, corner_idx = find_quad_corners(cnt, epsilon_frac=epsilon_frac)
    if corners is None:
        return None

    if debug_dir:
        vis = image.copy()
        cv2.drawContours(vis, [cnt.astype(np.int32)], -1, (0, 0, 255), 4)
        for (x, y) in corners:
            cv2.circle(vis, (int(x), int(y)), 10, (0, 255, 0), -1)
        cv2.imwrite(os.path.join(debug_dir, "03_contour.png"), vis)

    src_pts, tgt_pts = build_boundary_correspondences(cnt, corner_idx, output_size, n_per_side=n_per_side)
    dewarped = tps_dewarp(image, src_pts, tgt_pts, output_size, smoothing=smoothing)

    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "04_dewarped.png"), dewarped)

    return dewarped


def decode_image(image):
    """
    Try to decode a barcode/QR from `image` (np.ndarray, BGR) using whatever
    decoders are installed, in order of general reliability for this use
    case: pyzbar, zxing-cpp, cv2.QRCodeDetector. Returns the first decoded
    string found, or None.
    """
    try:
        from pyzbar.pyzbar import decode as zbar_decode
        from PIL import Image
        results = zbar_decode(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
        if results:
            return results[0].data.decode("utf-8", errors="replace")
    except ImportError:
        pass

    try:
        import zxingcpp
        from PIL import Image
        results = zxingcpp.read_barcodes(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
        if results:
            return results[0].text
    except ImportError:
        pass

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(image)
    if data:
        return data

    return None


def _parse_crop(s):
    parts = [int(p.strip()) for p in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--crop must be X1,Y1,X2,Y2")
    return parts


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Path to the source photo")
    p.add_argument("--crop", type=_parse_crop, default=None, help="X1,Y1,X2,Y2 region to crop before processing")
    p.add_argument("--sat-thresh", type=int, default=90)
    p.add_argument("--channel", choices=["sat", "gray"], default="sat")
    p.add_argument("--invert", action="store_true")
    p.add_argument("--output-size", type=int, default=700)
    p.add_argument("--n-per-side", type=int, default=60)
    p.add_argument("--smoothing", type=float, default=2.0)
    p.add_argument("--epsilon-frac", type=float, default=0.02)
    p.add_argument("--decode", action="store_true")
    p.add_argument("--output", default=None)
    p.add_argument("--save-debug", default=None)
    args = p.parse_args()

    img = cv2.imread(args.input)
    if img is None:
        print(f"ERROR: could not read image: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.crop:
        x1, y1, x2, y2 = args.crop
        img = img[y1:y2, x1:x2]

    dewarped = dewarp_panel(
        img,
        sat_thresh=args.sat_thresh,
        channel=args.channel,
        invert=args.invert,
        output_size=args.output_size,
        n_per_side=args.n_per_side,
        smoothing=args.smoothing,
        epsilon_frac=args.epsilon_frac,
        debug_dir=args.save_debug,
    )

    if dewarped is None:
        print("ERROR: panel segmentation/corner detection failed. "
              "Try --save-debug to inspect the mask, or tune --sat-thresh/--channel/--invert.",
              file=sys.stderr)
        sys.exit(2)

    out_path = args.output or (os.path.splitext(args.input)[0] + "_dewarped.png")
    cv2.imwrite(out_path, dewarped)
    print(f"Dewarped image written to: {out_path}")

    if args.decode:
        text = decode_image(dewarped)
        print(f"DECODED: {text if text else '<none>'}")


if __name__ == "__main__":
    main()
