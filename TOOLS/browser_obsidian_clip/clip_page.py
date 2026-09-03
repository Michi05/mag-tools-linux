"""
Clip the active browser tab to Markdown in an Obsidian vault.

Replicates the core behaviour of the Obsidian Web Clipper browser extension
(right-click "Open Obsidian Clipper" -> save page as Markdown) without needing
the extension itself. Talks directly to the browser over the DevTools
Protocol (CDP), so it works against any Chromium-based browser launched with
--remote-debugging-port (Brave, in this repo's setup — Firefox does not
speak CDP, only Chromium-family browsers do).

Also supports batch-converting already-saved local HTML files (e.g. offline
course exports) to Markdown, bypassing CDP entirely.

Frontmatter follows the enriched P1 schema (ported from the Custom alt version
PoC): page/course/lesson identity scraped from Articulate Rise DOM selectors,
source URL + saved date from the SingleFile HTML comment, an ordered outline
(h2 sections + image captions), and Clips' tags — all values YAML-escaped.
Filenames are lesson-ordered (P2): 'L04 - <lesson title>.md' derived from the
lesson counter, with title-based naming as fallback for pages without one.
Extracted images use hybrid names (P3): '001_<alt-or-caption>_<sha256-8>.ext'.

Usage:
    python clip_page.py                      # single tab open -> clip it
    python clip_page.py --match servicenow    # filter tabs by title/url substring
    python clip_page.py --vault ~/Documents/MyVault
    python clip_page.py --tag training --tag cmdb
    python clip_page.py --dir ~/Downloads/html_export --out ~/Desktop/output
"""

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
import websocket
from bs4 import BeautifulSoup
from markdownify import markdownify as md

DEBUG_PORTS = [9223, 9222]
# Linux Obsidian (Electron) stores its config under ~/.config, not %AppData%.
OBSIDIAN_CONFIG = Path.home() / ".config" / "obsidian" / "obsidian.json"
# Matches any base64 data URI; used to strip inline payloads before parsing
# (SingleFile exports embed MBs of base64 fonts/images in the DOM).
DATA_URI = re.compile(r"data:[a-zA-Z0-9][^\s;,'\"()]*;base64,[A-Za-z0-9+/=]+")
# Articulate Rise DOM selectors for course/lesson metadata (NowLearning exports).
RISE_META_JS = """(() => {
    const flat = (s) => {
        const el = document.querySelector(s);
        return el ? el.textContent.trim().replace(/\\s+/g, ' ') : null;
    };
    const h1 = document.querySelector('h1.lesson-header__title') || document.querySelector('h1');
    return {
        page_title: document.title,
        course_title: flat('a.nav-sidebar-header__title'),
        lesson_counter: flat('.lesson-header__counter'),
        lesson_title: h1 ? h1.textContent.trim().replace(/\\s+/g, ' ') : null,
    };
})()"""
JUNK_SELECTORS = [
    "script", "style", "noscript", "svg", "nav", "header", "footer",
    "[role=banner]", "[role=navigation]", "[role=complementary]",
    "aside", "iframe", "form",
]
IMAGE_EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
ATTACHMENT_HASH_RE = re.compile(r"_([0-9a-f]{8,12})(?:\.[^.]+)$", re.IGNORECASE)


def find_debug_port():
    for port in DEBUG_PORTS:
        try:
            r = requests.get(f"http://localhost:{port}/json/version", timeout=1)
            if r.ok:
                return port
        except requests.RequestException:
            continue
    sys.exit("No browser remote-debugging port found (tried: {}). "
              "Launch Brave with --remote-debugging-port=9223.".format(DEBUG_PORTS))


def default_vault():
    if not OBSIDIAN_CONFIG.exists():
        return None
    data = json.loads(OBSIDIAN_CONFIG.read_text(encoding="utf-8"))
    for info in data.get("vaults", {}).values():
        if info.get("open"):
            return Path(info["path"])
    vaults = list(data.get("vaults", {}).values())
    return Path(vaults[0]["path"]) if vaults else None


def pick_tab(port, match):
    tabs = [t for t in requests.get(f"http://localhost:{port}/json").json() if t.get("type") == "page"]
    if match:
        m = match.lower()
        tabs = [t for t in tabs if m in t.get("title", "").lower() or m in t.get("url", "").lower()]
    if not tabs:
        sys.exit("No matching tab found.")
    if len(tabs) > 1:
        print("Multiple tabs match, re-run with --match to narrow:")
        for t in tabs:
            print(f"  - {t['title']}  ({t['url']})")
        sys.exit(1)
    return tabs[0]


def cdp_eval(ws_url, expression):
    ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        ws.recv()
        ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True},
        }))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 2:
                return msg["result"]["result"]["value"]
    finally:
        ws.close()


def attachment_slug(text, max_len=50):
    """Return a short ASCII slug suitable for an attachment filename."""
    text = (text or "").encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].strip("-")


def image_label(img):
    """Prefer alt text, then a nearby Rise or generic figure caption."""
    alt = img.get("alt", "").strip()
    if alt:
        return alt
    figure = img.find_parent(class_="block-image__figure") or img.find_parent("figure")
    caption = figure.find(class_="block-image__caption") if figure else None
    return caption.get_text(" ", strip=True) if caption else ""


def existing_attachment(assets_dir, digest):
    """Find an existing P3 attachment with this full content hash."""
    short = digest[:8]
    candidates = assets_dir.glob(f"*_{short}.*") if assets_dir.exists() else ()
    for path in candidates:
        match = ATTACHMENT_HASH_RE.search(path.name)
        if match and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            return path.name
    return None


def extract_images(soup, out_dir):
    """Decode inline images to readable, content-addressed filenames.

    The sequence and label make attachments readable; the SHA-256 suffix keeps
    equal image bytes deduplicated and easy to identify across future runs.
    Empty/lazy-load placeholder data URIs are dropped.
    """
    assets_dir = out_dir / "attachments"
    seen = {}
    sequence = 0
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src.startswith("data:image/"):
            if not src or src.startswith("data:"):
                img.decompose()
            continue
        header, _, b64data = src.partition(",")
        mime = header[5:].split(";")[0]
        ext = IMAGE_EXT_BY_MIME.get(mime, ".bin")
        try:
            raw = base64.b64decode(b64data)
        except (base64.binascii.Error, ValueError):
            img.decompose()
            continue

        digest = hashlib.sha256(raw).hexdigest()
        fname = seen.get(digest) or existing_attachment(assets_dir, digest)
        if not fname:
            sequence += 1
            slug = attachment_slug(image_label(img))
            stem = f"{sequence:03d}"
            if slug:
                stem += f"_{slug}"
            fname = f"{stem}_{digest[:8]}{ext}"
            fpath = assets_dir / fname
            if fpath.exists() and hashlib.sha256(fpath.read_bytes()).hexdigest() != digest:
                fname = f"{stem}_{digest[:12]}{ext}"

        fpath = assets_dir / fname
        if not fpath.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(raw)
        seen[digest] = fname
        img["src"] = f"attachments/{fname}"


def html_to_markdown(html, out_dir):
    soup = BeautifulSoup(html, "html.parser")
    for sel in JUNK_SELECTORS:
        for el in soup.select(sel):
            el.decompose()
    # Score by markup length, not get_text(): pages with a <template> tag
    # (declarative shadow DOM) make bs4 mis-tag later text nodes as
    # TemplateString, which get_text() silently excludes by default (its
    # exact-type filter doesn't match subclasses) -> real content reads as 0.
    candidates = soup.find_all(["main", "article"]) or [soup.body or soup]
    main = max(candidates, key=lambda el: len(str(el)))
    extract_images(main, out_dir)
    return md(str(main), heading_style="ATX").strip()


def sanitize_filename(title):
    name = re.sub(r'[\\/:*?"<>|]', "", title).strip()
    return name[:120] or "Untitled Clip"


def lesson_filename_base(meta):
    """'LNN - <lesson title>' when lesson identity is present, else None (P2).

    Parses the lesson number from lesson_counter ('Lesson 4 of 9'), zero-pads
    it to at least 2 digits (wider for courses with 100+ lessons), and pairs
    it with the lesson title so files sort in lesson order. Pages without a
    counter (e.g. the course-overview page) return None and fall back to
    title-based naming.
    """
    m = re.search(r"lesson\s+(\d+)\s+of\s+(\d+)", meta.get("lesson_counter") or "", re.IGNORECASE)
    if not m:
        return None
    num, total = int(m.group(1)), int(m.group(2))
    title = meta.get("lesson_title") or meta.get("page_title") or "Lesson"
    return f"L{num:0{max(2, len(str(total)))}d} - {sanitize_filename(title)}"


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_html(html):
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def extract_metadata(raw, source_path):
    """Course/lesson metadata from SingleFile comment + Articulate Rise DOM.

    Ported from Custom alt version _jul26/extract_html.py (P1). Runs on the raw
    HTML; base64 payloads are stripped before parsing so multi-MB SingleFile
    exports parse fast. All fields are optional — absent ones are omitted.
    """
    meta = {"source_file": str(source_path)}

    comment = re.search(r"<!--([\s\S]*?)-->", raw)
    if comment:
        body = comment.group(1)
        url_m = re.search(r"url:\s*(\S+)", body)
        date_m = re.search(r"saved date:\s*(.+)", body)
        if url_m:
            meta["source_url"] = url_m.group(1).strip()
        if date_m:
            meta["saved_date"] = date_m.group(1).strip()

    title_m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
    if title_m and title_m.group(1).strip():
        meta["page_title"] = title_m.group(1).strip()

    soup = _parse_html(DATA_URI.sub("", raw))
    course_a = soup.select_one("a.nav-sidebar-header__title")
    if course_a:
        meta["course_title"] = _clean(course_a.get_text())
    counter = soup.select_one(".lesson-header__counter")
    if counter:
        meta["lesson_counter"] = _clean(counter.get_text())
    h1 = soup.select_one("h1.lesson-header__title") or soup.find("h1")
    if h1:
        meta["lesson_title"] = _clean(h1.get_text())

    main = soup.find("main") or soup
    outline = []
    for el in main.find_all(True):
        classes = el.get("class") or []
        if el.name == "h2":
            outline.append({"level": 2, "text": _clean(el.get_text())})
        elif "block-image__caption" in classes:
            outline.append({"level": 3, "text": _clean(el.get_text())})
    if outline:
        meta["outline"] = outline

    return meta


def yaml_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_frontmatter(meta, tags):
    """YAML frontmatter: PoC schema (page/course/lesson identity, provenance,
    outline) merged with Clips' tags. Every value quoted+escaped."""
    lines = ["---"]
    for key in ("page_title", "course_title", "lesson_counter", "lesson_title"):
        if meta.get(key):
            lines.append(f"{key}: {yaml_quote(meta[key])}")
    for key in ("source_file", "source_url", "saved_date"):
        if meta.get(key):
            lines.append(f"{key}: {yaml_quote(meta[key])}")
    lines.append(f"created: {yaml_quote(datetime.now().strftime('%Y-%m-%d %H:%M'))}")
    if meta.get("outline"):
        lines.append("outline:")
        for entry in meta["outline"]:
            lines.append(f"  - {{level: {entry['level']}, text: {yaml_quote(entry['text'])}}}")
    if tags:
        lines.append("tags:")
        lines.extend(f"  - {t}" for t in tags)
    lines.append("---\n")
    return "\n".join(lines)


def write_clip(out_dir, meta, tags, body):
    content = build_frontmatter(meta, tags) + body
    base = lesson_filename_base(meta)
    if not base:
        title = meta.get("page_title") or meta.get("lesson_title") or "Untitled Clip"
        base = sanitize_filename(title)
    out_path = out_dir / f"{base}.md"
    n = 2
    while out_path.exists():
        out_path = out_dir / f"{base} ({n}).md"
        n += 1
    out_path.write_text(content, encoding="utf-8")
    return out_path


def clip_local_file(path, out_dir):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    meta = extract_metadata(raw, path)
    meta.setdefault("page_title", path.stem)
    return meta, html_to_markdown(raw, out_dir)


def clip_tab(port, match, out_dir):
    tab = pick_tab(port, match)
    title = cdp_eval(tab["webSocketDebuggerUrl"], "document.title")
    url = cdp_eval(tab["webSocketDebuggerUrl"], "location.href")
    meta = cdp_eval(tab["webSocketDebuggerUrl"], RISE_META_JS) or {}
    meta = {k: v for k, v in meta.items() if v}
    meta["page_title"] = meta.get("page_title") or title
    meta["source_url"] = url
    html = cdp_eval(tab["webSocketDebuggerUrl"], "document.documentElement.outerHTML")
    return meta, html_to_markdown(html, out_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--match", help="Filter tabs by title/url substring (live-tab mode)")
    parser.add_argument("--vault", help="Target Obsidian vault path (defaults to the currently open vault)")
    parser.add_argument("--out", help="Output directory (overrides --vault; used as-is, created if missing)")
    parser.add_argument("--dir", help="Batch-convert local HTML files in this directory instead of a live tab")
    parser.add_argument("--tag", action="append", default=[], help="Tag to add (repeatable)")
    args = parser.parse_args()

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(args.vault) if args.vault else default_vault()
        if not out_dir or not out_dir.exists():
            sys.exit(f"Vault path not found: {out_dir}")

    if args.dir:
        src_dir = Path(args.dir)
        files = sorted(src_dir.glob("*.html")) + sorted(src_dir.glob("*.htm"))
        if not files:
            sys.exit(f"No .html files found in {src_dir}")
        for f in files:
            meta, body = clip_local_file(f, out_dir)
            out_path = write_clip(out_dir, meta, args.tag, body)
            print(f"Saved: {out_path}")
        return

    port = find_debug_port()
    meta, body = clip_tab(port, args.match, out_dir)
    out_path = write_clip(out_dir, meta, args.tag, body)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
