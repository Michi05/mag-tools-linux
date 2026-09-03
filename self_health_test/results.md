# Self health test — last run

**2026-09-03T13:14:47+02:00** — `./run_all.sh` — **18 passed, 0 failed**

| Tool | Result | What was actually verified |
|---|---|---|
| ai_screenshot_ocr | PASS | `--help` works with zero deps installed (heavy imports deferred into `main()`); real invocation fails with the graceful missing-dependency message, not a traceback. Full VLM inference not exercised — deps/model not installed yet (deferred, see `docs/porting-notes.md`). |
| ai_session_finder | PASS | Stdlib-only search mode: no-match case, and a real match found in this machine's actual `~/.claude/projects` data (this very session). |
| ai_whisper_transcription | PASS | `--help` works with zero deps installed; real invocation fails with the graceful missing-dependency message. Full transcription not exercised — faster-whisper/model not installed yet (deferred). |
| browser_captive_portal | PASS | Script passes `bash -n`; dashboard HTML present; real default gateway (`192.168.8.1`) resolved via `ip route` on this machine. Browser launch itself not exercised (would open a real window). |
| browser_obsidian_clip | PASS | `--dir` batch mode: synthetic HTML → real Markdown file with correct body text and tag in frontmatter. Live-tab CDP mode not exercised (needs Brave running with a debug port). |
| browser_youtubewl_cleaner | PASS | Static HTML file present and well-formed. |
| data_btc_nasdaq_correlation | PASS | HTML present; JSON data file parses. |
| dewarp_flexible_qr | PASS | `--help` works; full pipeline run against a synthetic flat-gray image correctly reports "segmentation/corner detection failed" (expected — no HSV-contrasted panel in a solid-color test image). No real wrinkled-QR fixture photo available to test a true positive. |
| mag_vid_compress | PASS | ffmpeg present; both `av1_qsv` and `av1_nvenc` hardware encoders confirmed available. |
| media_pic_similarity_match | PASS | Real run against 3 synthetic images; correct output structure (nearest-match + top-pairs sections). |
| utils_findfiles | PASS | Real run against synthetic files; correct match/non-match behavior. |
| utils_html_to_text | PASS | Real run against synthetic HTML; both paragraphs extracted, script tag content excluded. |
| utils_hydrate_onedrive | PASS | Not ported by design — README documents why; check confirms that documentation exists. |
| utils_image_tools | PASS | Real runs of all three scripts: thumbnail generated, PNG tagged, dry-run classify moved/tagged 1 of 1 synthetic high-confidence row. |
| video_ai_upscale | PASS | `--help` works; real invocation fails with the graceful "binary not found, here's how to get it" message (binary deliberately not downloaded yet). |
| video_image_stacking | PASS | Real ORB stack of 3 sample photos (`TOOLS/video_image_stacking/images/`) produced a real output image. |
| video_yt_dlp | PASS | System `yt-dlp` binary present, `--version` runs. |
| vpn_wireguard | PASS | Setup script passes `bash -n`; compose file present and references the expected image. |

## Follow-up agent-driven test

See the end of this session's summary for the `/run-tool`-via-agent pass —
an agent given only `CLAUDE.md`/`TOOLS.md` (no prior context on this build)
was asked to pick and actually invoke tools through the `/run-tool` skill,
as a check that the documentation alone is enough to operate this repo.
