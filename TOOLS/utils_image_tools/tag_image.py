r"""Write XMP classification tags to PNG images (shows as Tags in file managers
that read XMP — Nautilus/Dolphin/exiftool-based tools; Windows Explorer too).

Usage:
    python tag_image.py IMAGE TAG [TAG ...] [--title TITLE] [--description DESC]

Requires Pillow.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image
import PIL.PngImagePlugin


def _build_xmp(tags: list[str], title: str, description: str) -> str:
    tag_items = "".join(f"        <rdf:li>{t}</rdf:li>\n" for t in tags)
    title_el = (
        f'      <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}'
        f"</rdf:li></rdf:Alt></dc:title>\n"
        if title else ""
    )
    desc_el = (
        f'      <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{description}'
        f"</rdf:li></rdf:Alt></dc:description>\n"
        if description else ""
    )
    return (
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core">\n'
        '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '    <rdf:Description rdf:about=""\n'
        '        xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"{title_el}"
        f"{desc_el}"
        "      <dc:subject>\n"
        "        <rdf:Bag>\n"
        f"{tag_items}"
        "        </rdf:Bag>\n"
        "      </dc:subject>\n"
        "    </rdf:Description>\n"
        "  </rdf:RDF>\n"
        "</x:xmpmeta>\n"
        '<?xpacket end="w"?>'
    )


def tag_png(path: Path, tags: list[str], title: str, description: str) -> None:
    img = Image.open(path)
    meta = PIL.PngImagePlugin.PngInfo()
    if hasattr(img, "text"):
        for k, v in img.text.items():
            if k != "XML:com.adobe.xmp":
                meta.add_text(k, v)
    meta.add_itxt("XML:com.adobe.xmp", _build_xmp(tags, title, description), lang="", tkey="")
    img.save(path, pnginfo=meta)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write XMP tags to a PNG (dc:subject keywords)."
    )
    parser.add_argument("image", type=Path, help="Target PNG file")
    parser.add_argument("tags", nargs="+", help="One or more tags")
    parser.add_argument("--title", default="", help="XMP title")
    parser.add_argument("--description", default="", help="XMP description")
    args = parser.parse_args()

    if not args.image.exists():
        print(f"error: file not found: {args.image}", file=sys.stderr)
        sys.exit(1)
    if args.image.suffix.lower() != ".png":
        print(f"error: only PNG supported (got {args.image.suffix})", file=sys.stderr)
        sys.exit(1)

    tag_png(args.image, args.tags, args.title, args.description)

    print(f"tagged : {args.image.name}")
    print(f"tags   : {', '.join(args.tags)}")
    if args.title:
        print(f"title  : {args.title}")
    if args.description:
        print(f"desc   : {args.description}")


if __name__ == "__main__":
    main()
