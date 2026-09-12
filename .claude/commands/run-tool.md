---
description: Run a tool from the MAG Tools collection (resolves via $MAG_TOOLS_DIR, works from any directory)
disable-model-invocation: true
---

Resolve the tools folder first — run `echo $MAG_TOOLS_DIR` (do not assume the current working directory). If it's empty, stop and tell the user to set `MAG_TOOLS_DIR` in `~/.claude/settings.json`'s `env` block to the absolute path of this repo on this machine, then start a fresh session.

Read `$MAG_TOOLS_DIR/TOOLS.md` to load the full tool reference. Every tool path in that file is written relative to the repo root, so run tool commands with `$MAG_TOOLS_DIR` as the working directory (e.g. `cd "$MAG_TOOLS_DIR" && <command>`), regardless of where this session was launched. Then act as a tool-runner assistant:

1. Parse the user's request and identify which tool from TOOLS.md best matches the intent.
   - If no tool matches the request closely, say so explicitly and suggest alternatives (other tools in TOOLS.md, or PATH utilities). Do not force an ill-fitting tool.

2. Before constructing the final command, run `<tool> --help` (or the equivalent) to confirm available flags — unless the exact parameters needed are already fully specified in TOOLS.md.

3. Construct the exact command based on confirmed parameters. If required arguments are still missing (file path, URL, search term, etc.), ask for them before proceeding. Do not guess.

4. Run the command, then report concisely: what ran, key output, any files produced.

5. If the tool processed video (download, compress, transcribe, stack, or any other video/audio conversion — e.g. yt-dlp, mag_vid_compress, whisper transcription, image stacking on video frames), append one row to `$MAG_TOOLS_DIR/video_processing_log.md` (not the launch directory — this keeps one canonical log across all invocations regardless of where `/run-tool` was run from). Create the file with a header row if it doesn't exist yet:

   ```
   | Timestamp | Tool | Source | Destination | Status | Details |
   |---|---|---|---|---|---|
   ```

   - Timestamp: ISO 8601, local time, at completion.
   - Tool: tool folder name (e.g. `video_yt_dlp`).
   - Source: input file/URL path.
   - Destination: output file path (or `—` if failed before output).
   - Status: `success`, `failed`, or `partial`.
   - Details: one line — key params used (codec, resolution, model, etc.), and error summary if failed.

   This log is append-only and exists so another tool can review, undo, or clean up past runs — do not rewrite or delete prior rows.

6. If the tool fails, read the error, cross-reference the requirements in TOOLS.md, and suggest the most likely fix.
