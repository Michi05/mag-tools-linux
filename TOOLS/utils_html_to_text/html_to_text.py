"""
html_to_text.py — Strip HTML, output plain text.

Usage:
    python html_to_text.py input.html [output.txt]

If output is omitted, prints to stdout.
Requires: pip install beautifulsoup4
"""

import sys
from pathlib import Path
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def main():
    if len(sys.argv) < 2:
        print("Usage: python html_to_text.py input.html [output.txt]")
        sys.exit(1)

    src = Path(sys.argv[1])
    html = src.read_text(encoding="utf-8")
    result = html_to_text(html)

    if len(sys.argv) >= 3:
        out = Path(sys.argv[2])
        out.write_text(result, encoding="utf-8")
        print(f"Saved: {out}")
    else:
        print(result)


if __name__ == "__main__":
    main()
