# ai_session_finder

Searches the local session stores of all three terminal AI coders (Claude
Code, OpenCode, Copilot) to find past sessions by title, first prompt,
folder, or id. `--search <term>` returns plain text for agent ingestion; a
bare run refreshes the visual `sessions.html`.

## What changed from the Windows version

- **Path decoding:** Claude Code encodes a session's working directory into
  its project folder name by replacing path separators with `-`. The
  Windows version reconstructed `C:\Users\...` (drive letter + backslashes);
  this version reconstructs POSIX `/home/...` paths instead — the encoding
  scheme is the same, only the target path shape differs.
- **Row-click behavior:** the Windows version linked each row to a custom
  `magopen://` URI that opened a new Windows Terminal in that session's
  folder (via a one-time registry install, `install_magopen.reg`). There's
  no equivalent protocol handler set up on Linux, and building one (a
  `.desktop` file + `xdg-mime` registration invoking a terminal emulator)
  a small chunk of desktop-integration work with no clear payoff over the
  existing Copy button. So on this port, **clicking a row
  copies the resume command to the clipboard** (same as clicking Copy) —
  paste it into any terminal. `open_folder.cmd`/`open_folder.ps1` and
  `install_magopen.reg` were not ported for the same reason.
- Data source paths (`~/.claude/projects`, `~/.local/share/opencode/opencode.db`,
  `~/.copilot/session-state`) were already POSIX-style in the original and
  needed no change.

## Usage

**Find mode (preferred for agent use):**
```
python3 build_index.py --search <term> [<term> ...]
```
Returns one block per matching session (newest first): tool, title, prompt,
folder, updated, and `id`. All terms must match (case-insensitive, AND).
This mode writes no files.

**Browser / refresh mode:**
```
python3 build_index.py        # refresh / rebuild sessions.html
xdg-open sessions.html
```

## Requirements

Python 3, stdlib only.
