# utils_image_tools

Three independent, pure-Python image utilities. Fully portable — no OS-specific
code (ported unchanged from the Windows repo, minus a Windows-console
`sys.stdout.reconfigure` call that Linux's UTF-8 locale doesn't need).

- `classify_images.py` — bulk-sorts a folder of photos using a markdown
  classification table (Original / Category / Proposed / Confidence columns).
  Moves each "High" confidence row's image into a category folder, renames it,
  and (for JPEGs) writes category + filename terms as XMP `dc:subject` keywords.
- `make_thumbnails.py` — downscales every `.jpg`/`.JPG` in a folder to a
  1024px-longest-side, quality-72 thumbnail in `thumbnails/`.
- `tag_image.py` — writes XMP `dc:subject` (+ optional title/description) tags
  into a single PNG.

## Usage

```
python3 classify_images.py [markdown_file] [--dry-run] [--limit N] [--workdir DIR]
python3 make_thumbnails.py [folder]
python3 tag_image.py IMAGE.png TAG [TAG ...] [--title T] [--description D]
```

## Requirements

```
pip install -r requirements.txt
```
`classify_images.py` needs no third-party deps (raw JPEG byte manipulation).
`make_thumbnails.py` and `tag_image.py` need Pillow.

## Notes

XMP tags written here are read by any XMP-aware tool (`exiftool`, GNOME Files
with the right extension, digiKam, etc.) — Linux file managers don't surface a
"Tags" column by default the way Windows Explorer does, so verify with:
```
exiftool -XMP:Subject IMAGE.png
```
`exiftool` is **not** installed on this machine by default — it's an optional
verification step, not a requirement for `tag_image.py`/`classify_images.py`
themselves. Install with `sudo apt install libimage-exiftool-perl` if you
want to use it to check tags.
