# video_image_stacking

Aligns and stacks multiple photos of the same scene to produce a single
low-noise image. Pure Python + OpenCV, unchanged from the Windows repo — no
OS-specific code (`cv2.imshow`/`--show` needs an X11/Wayland display, which
this machine has).

## Usage

```
python3 auto_stack.py <input_dir> <output.jpg> --method ORB|ECC|FLOW [--blend mean|median] [--show]
```

- **ORB** — fast, keypoint-based, handles large misalignments well.
- **ECC** — slower, more precise for subtle alignment, one global homography.
- **FLOW** — dense optical flow, corrects local/non-rigid motion (e.g. an
  animal's fur/breathing) that ORB/ECC's single global transform can't.

## Requirements

```
pip install -r requirements.txt
```
