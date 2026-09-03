# media_pic_similarity_match

Computes HSV color-histogram fingerprints and finds visually similar images by
color palette. Pure Python + Pillow/numpy, unchanged from the Windows repo.

## Usage

```
python3 similar_pic_matcher.py <folder> [--count N] [--bins B] [--all]
```

## Requirements

```
pip install -r requirements.txt
```

## Notes

O(n²) pairwise comparisons — fine for tens of images, slow for thousands.
Distance thresholds ("same" < 0.15, "similar" < 0.30) are calibrated from an
initial 10-image test, not a rigorous benchmark — treat as a rough triage,
not ground truth.
