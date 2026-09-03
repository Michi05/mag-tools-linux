# browser_obsidian_clip

Replicates the Obsidian Web Clipper browser extension without the extension —
grabs the active browser tab over the DevTools Protocol (CDP), strips
boilerplate, converts to Markdown, and writes it into an Obsidian vault with
enriched YAML frontmatter. Also batch-converts a folder of already-saved
local HTML files, no live tab needed.

## What changed from the Windows version

- **Browser:** CDP only works with Chromium-family browsers. This machine has
  Brave (not Chrome), so launch Brave with `--remote-debugging-port=9223`
  instead of Chrome. Firefox cannot be used for live-tab mode (no CDP
  support) — use `--dir` batch mode for Firefox-saved pages instead.
- **Obsidian config path:** Linux Obsidian stores `obsidian.json` at
  `~/.config/obsidian/obsidian.json`, not `%AppData%\obsidian\obsidian.json`.
- Everything else (HTML→Markdown conversion, frontmatter schema, image
  extraction, lesson-ordered filenames) is unchanged — pure Python logic, no
  OS dependency.

## Usage

```
python3 clip_page.py [--match TEXT] [--vault PATH] [--out DIR] [--dir DIR] [--tag TAG ...]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--match` | none | Filter open tabs by title/URL substring (live-tab mode) |
| `--vault` | currently-open vault (from `obsidian.json`) | Target vault path |
| `--out` | — | Output directory, overrides `--vault` |
| `--dir` | — | Batch-convert local HTML files in this directory (bypasses CDP) |
| `--tag` | none | Tag to add to frontmatter (repeatable) |

## Requirements

```
pip install -r requirements.txt
```

Live-tab mode needs Brave already running with a debug port:
```
brave-browser --remote-debugging-port=9223 &
```
(Auto-discovers `9223` then `9222`.) `--dir` batch mode needs neither Brave
nor a debug port.

## Known limitations (carried over)

SPA pages capture app-shell scaffolding, not rendered content — no
Readability-style extraction. One live tab per run.
