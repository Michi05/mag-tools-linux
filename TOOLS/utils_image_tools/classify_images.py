#!/usr/bin/env python3
"""Classify photos by reading a markdown classification file.

Usage:
    python3 classify_images.py <markdown_file> [--dry-run] [--workdir <dir>]

Scans the markdown for table rows with "High" confidence, then for each:
  1. Creates a folder named after the category
  2. Moves the original file into it with the proposed filename
  3. Writes category + descriptive terms as JPEG XMP keywords
"""

import re
import os
import sys
import shutil
import argparse
import struct


_HEADER_ALIASES = {
    'orig':       {'original filename', 'original', 'orig filename', 'source'},
    'category':   {'category', 'cat'},
    'proposed':   {'proposed filename', 'proposed', 'new filename'},
    'confidence': {'confidence', 'conf'},
}


def _detect_col_map(cells):
    """Map required field names to column indices from a header row.

    Returns dict {orig, category, proposed, confidence} -> int index,
    or None if not all four fields are found.
    """
    lower = [c.lower() for c in cells]
    col_map = {}
    for field, aliases in _HEADER_ALIASES.items():
        for i, h in enumerate(lower):
            if h in aliases:
                col_map[field] = i
                break
    return col_map if len(col_map) == 4 else None


def _is_separator(cells):
    return all(set(c) <= {'-', ':', ' '} for c in cells)


def parse_classification_md(filepath):
    """Parse the markdown classification file and return list of image entries.

    Each entry: (orig_filename, category, proposed_filename, confidence)
    Handles tables with or without a leading row-number column.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rows = []
    col_map = None

    for line in content.splitlines():
        if not line.startswith('|'):
            col_map = None
            continue

        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c != '']

        if len(cells) < 4:
            continue

        if _is_separator(cells):
            continue

        # Try to detect header row
        detected = _detect_col_map(cells)
        if detected is not None:
            col_map = detected
            continue

        # Data row — need an active col_map
        if col_map is None:
            continue

        max_idx = max(col_map.values())
        if len(cells) <= max_idx:
            continue

        orig       = cells[col_map['orig']]
        category   = cells[col_map['category']]
        proposed   = cells[col_map['proposed']]
        confidence = cells[col_map['confidence']]

        rows.append((orig, category, proposed, confidence))

    return rows


def extract_tags(proposed_filename, category):
    """Generate metadata tags from proposed filename and category.

    Tags = [category] + space/hyphen-separated terms after timestamp prefix.

    Example:
        "20260501_225109_menu-99cheesecake-toppings-bebidas.jpg", "Food"
        -> ["Food", "menu", "99cheesecake", "toppings", "bebidas"]
    """
    name = proposed_filename
    if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov')):
        name = name.rsplit('.', 1)[0]

    parts = name.split('_')
    descriptive = parts[-1] if len(parts) >= 3 else '_'.join(parts[2:]) if len(parts) > 1 else parts[0]

    terms = [t for t in descriptive.replace('-', '_').split('_') if t]

    tags = [category] + terms
    return tags


def build_xmp(keywords):
    """Build XMP XML packet for dc:subject keywords."""
    items = '\n'.join(f'     <rdf:li>{k}</rdf:li>' for k in keywords)

    xmp = f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="mag-tools-linux-classify">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:xmp="http://ns.adobe.com/xap/1.0/">
   <dc:subject>
    <rdf:Bag>
{items}
    </rdf:Bag>
   </dc:subject>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''
    return xmp


def set_jpeg_xmp_keywords(filepath, tags):
    """Inject XMP dc:subject keywords into a JPEG file.

    Inserts the XMP APP1 segment right before the SOS marker
    (standard metadata location). Removes any existing XMP APP1.
    """
    xmp_xml = build_xmp(tags)
    xmp_data = xmp_xml.encode('utf-8')

    app1_id = b'http://ns.adobe.com/xap/1.0/\x00'
    payload = app1_id + xmp_data
    app1_marker = b'\xff\xe1' + struct.pack('>H', len(payload) + 2) + payload

    with open(filepath, 'rb') as f:
        data = f.read()

    if data[:2] != b'\xff\xd8':
        print(f'  ⚠  Not a valid JPEG (no SOI marker): {filepath}')
        return False

    pos = 2
    new_chunks = [data[:2]]
    xmp_inserted = False

    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            break
        marker = data[pos:pos+2]
        mtype = marker[1]

        # End of Image
        if mtype == 0xD9:
            if not xmp_inserted:
                new_chunks.append(app1_marker)
                xmp_inserted = True
            new_chunks.append(data[pos:])
            break

        # Parameter-less markers
        if mtype in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8):
            new_chunks.append(marker)
            pos += 2
            continue

        # SOS — insert XMP right before this
        if mtype == 0xDA:
            if not xmp_inserted:
                new_chunks.append(app1_marker)
                xmp_inserted = True
            new_chunks.append(data[pos:])
            break

        # Segments with length
        if pos + 4 > len(data):
            break
        seg_len = struct.unpack('>H', data[pos+2:pos+4])[0]
        if seg_len < 2:
            break

        seg_end = pos + 2 + seg_len
        seg_data_start = pos + 4

        # Check for existing XMP APP1 — skip it
        is_existing_xmp = (
            mtype == 0xE1
            and seg_len >= len(app1_id) + 2
            and seg_data_start + len(app1_id) <= len(data)
            and data[seg_data_start:seg_data_start + len(app1_id)] == app1_id
        )

        if not is_existing_xmp:
            new_chunks.append(data[pos:seg_end])

        pos = seg_end

    if not xmp_inserted:
        new_chunks.append(app1_marker)
        new_chunks.append(b'\xff\xd9')

    new_data = b''.join(new_chunks)
    with open(filepath, 'wb') as f:
        f.write(new_data)

    return True


def process_image(orig_name, category, proposed_name, dry_run, workdir):
    """Process a single image: move and tag."""
    src = os.path.join(workdir, orig_name)
    cat_dir = os.path.join(workdir, category)
    dst = os.path.join(cat_dir, proposed_name)

    if not os.path.exists(src):
        print(f'  ⚠  Source not found: {src}')
        return False

    tags = extract_tags(proposed_name, category)
    tag_str = '; '.join(tags)

    print(f'  Source: {orig_name}')
    print(f'  Target: {category}/{proposed_name}')
    print(f'  Tags:   {tag_str}')

    if dry_run:
        print(f'  → DRY RUN — skipped')
        return True

    os.makedirs(cat_dir, exist_ok=True)

    if os.path.exists(dst):
        print(f'  ⚠  Target already exists, skipping: {dst}')
        return False

    shutil.move(src, dst)
    print(f'  ✓ Moved')

    if dst.lower().endswith(('.jpg', '.jpeg')):
        ok = set_jpeg_xmp_keywords(dst, tags)
        if ok:
            print(f'  ✓ Tags written to JPEG XMP')
        else:
            print(f'  ⚠  Could not write tags')
    else:
        print(f'  - Skipped metadata (not a JPEG)')

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Classify photos using a markdown classification file')
    parser.add_argument('markdown', nargs='?',
                        default='image_classif.md',
                        help='Path to the classification markdown file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without moving or tagging')
    parser.add_argument('--limit', type=int, default=0,
                        help='Process only first N high-confidence rows')
    parser.add_argument('--workdir', default='.',
                        help='Working directory (default: current dir)')
    args = parser.parse_args()

    md_path = os.path.join(args.workdir, args.markdown)
    if not os.path.exists(md_path):
        print(f'Error: markdown file not found: {md_path}')
        sys.exit(1)

    rows = parse_classification_md(md_path)
    print(f'Found {len(rows)} total rows in {args.markdown}')

    high_rows = [(o, c, p) for o, c, p, conf in rows if conf == 'High']
    total = len(high_rows)
    print(f'Found {total} rows with High confidence\n')

    if args.limit > 0:
        high_rows = high_rows[:args.limit]
        print(f'--limit {args.limit}: processing first {len(high_rows)} rows\n')

    if args.dry_run:
        print('=== DRY RUN — no files will be moved or modified ===\n')

    successes = 0
    errors = 0
    for i, (orig, category, proposed) in enumerate(high_rows, 1):
        print(f'[{i}/{total}] Processing...')
        ok = process_image(orig, category, proposed, args.dry_run, args.workdir)
        if ok:
            successes += 1
        else:
            errors += 1
        print()

    print(f'Done. {successes} succeeded, {errors} errors'
          + (' (dry run)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
