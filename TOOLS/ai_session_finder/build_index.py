#!/usr/bin/env python3
"""Build a searchable HTML index of claude / opencode / copilot sessions.

Scans the local session stores of the three terminal AI coders and writes a
self-contained HTML file (sessions.html) with, for each session:
    - tool (claude | opencode | copilot)
    - title / name
    - first user prompt (searchable description)
    - folder (cwd / directory)
    - last-updated timestamp
    - session id (for future direct-resume)
    - agent/model where available
    - a resume command (cd into the folder + run the session) with a copy button

Click a row (or its Copy button) to copy the full resume command to the
clipboard, then paste it into a terminal. Nothing leaves the machine.

With `--search <term> [...]` it prints matching sessions as plain text instead
of writing HTML, so an agent or the user can ingest/filter the index directly
from the command line.

Usage:
    python build_index.py                 # writes sessions.html next to this script
    python build_index.py -o out.html     # custom output path
    python build_index.py -o out.html -f  # regenerate even if unchanged
    python build_index.py --search servicenow cmdb   # print matching sessions as text
"""

import argparse
import html
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

HOME = os.path.expanduser("~")

CLAUDE_PROJECTS = os.path.join(HOME, ".claude", "projects")
OPENCODE_DB = os.path.join(HOME, ".local", "share", "opencode", "opencode.db")
COPILOT_STATE = os.path.join(HOME, ".copilot", "session-state")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_ts(ms_or_none):
    """Format epoch-milliseconds (opencode) or ISO string (claude/copilot) to a
    compact sortable string; returns (sortable, display). Nanoseconds to ms."""
    if ms_or_none is None:
        return ("", "")
    if isinstance(ms_or_none, (int, float)):
        try:
            dt = datetime.fromtimestamp(ms_or_none / 1000, tz=timezone.utc)
        except (ValueError, OSError):
            return ("", "")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), dt.strftime("%Y-%m-%d %H:%M")
    s = str(ms_or_none)
    try:
        if len(s) > 19:
            dt = datetime.fromisoformat(s[:19] + ("+00:00" if s.endswith("Z") else ""))
        else:
            dt = datetime.fromisoformat(s)
    except ValueError:
        return (s, s)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), dt.strftime("%Y-%m-%d %H:%M")


def decode_claude_project(proj_name):
    """Best-effort decode of a claude project folder name back to a cwd.

    Claude encodes the working dir by turning every path separator into '-',
    which is lossy. We reconstruct with POSIX '/' separators (Linux paths,
    unlike the Windows drive-letter form this originally handled), then keep
    only the result if it actually exists on disk; otherwise return '' so the
    caller falls back to 'unknown'."""
    if not proj_name.startswith("-"):
        return ""
    parts = proj_name.strip("-").split("-")
    coarse = "/" + "/".join(parts)
    if os.path.isdir(coarse):
        return coarse
    return ""


def scan_claude(sessions):
    if not os.path.isdir(CLAUDE_PROJECTS):
        return
    for proj_name in os.listdir(CLAUDE_PROJECTS):
        proj_dir = os.path.join(CLAUDE_PROJECTS, proj_name)
        if not os.path.isdir(proj_dir):
            continue
        for fn in os.listdir(proj_dir):
            if not fn.endswith(".jsonl"):
                continue
            path = os.path.join(proj_dir, fn)
            session_id = fn[:-len(".jsonl")]
            title = ""
            cwd = ""
            prompt = ""
            mtime = os.path.getmtime(path) * 1000
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if not line.strip():
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        t = rec.get("type")
                        if t == "ai-title":
                            ttl = rec.get("aiTitle")
                            if ttl:
                                title = ttl.strip()
                        elif t == "user" and not prompt:
                            c = rec.get("message", {}).get("content")
                            if isinstance(c, str):
                                prompt = c.strip()
                            elif isinstance(c, list):
                                prompt = " ".join(
                                    item.get("text", "") for item in c
                                    if isinstance(item, dict) and item.get("text")
                                ).strip()
                        elif t in ("user", "assistant") and not cwd:
                            cwd = rec.get("cwd") or ""
                        if t == "user" and not cwd:
                            cwd = rec.get("cwd") or ""
            except OSError:
                continue
            if not cwd:
                cwd = decode_claude_project(proj_name)
            ts_s, ts_d = fmt_ts(mtime)
            sessions.append({
                "tool": "claude",
                "title": title or "(untitled session)",
                "folder": cwd or "unknown",
                "prompt": prompt,
                "session_id": session_id,
                "stamp": ts_s,
                "stamp_display": ts_d,
                "agent": "",
                "model": "",
                "reopen": f"claude --resume {session_id}" if title else "",
            })


def scan_opencode(sessions):
    if not os.path.isfile(OPENCODE_DB):
        return
    try:
        con = sqlite3.connect("file:" + OPENCODE_DB + "?mode=ro", uri=True)
    except sqlite3.Error as e:
        print(f"[warn] opencode db unreadable: {e}", file=sys.stderr)
        return
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT id, directory, title, time_updated, agent, model FROM session "
            "WHERE directory IS NOT NULL AND time_updated IS NOT NULL "
            "ORDER BY time_updated"
        )
        seen = set()
        for row in cur.fetchall():
            sid, directory, title, updated, agent, model = row
            if sid in seen:
                continue
            seen.add(sid)
            ts_s, ts_d = fmt_ts(updated)
            model_id = ""
            if model:
                try:
                    parsed = json.loads(model)
                    model_id = parsed.get("id", "")
                except (ValueError, AttributeError):
                    model_id = model
            sessions.append({
                "tool": "opencode",
                "title": title or "(untitled session)",
                "folder": directory or "unknown",
                "prompt": "",
                "session_id": sid,
                "stamp": ts_s,
                "stamp_display": ts_d,
                "agent": agent or "",
                "model": model_id,
                "reopen": f"opencode --continue",
            })
    finally:
        con.close()


def scan_copilot(sessions):
    if not os.path.isdir(COPILOT_STATE):
        return
    for sid in os.listdir(COPILOT_STATE):
        sdir = os.path.join(COPILOT_STATE, sid)
        if not os.path.isdir(sdir):
            continue
        wy = os.path.join(sdir, "workspace.yaml")
        if not os.path.isfile(wy):
            continue
        name = ""
        cwd = ""
        repo = ""
        updated = ""
        try:
            with open(wy, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = re.match(r"^(\w+):\s*(.*)$", line.strip())
                    if not m:
                        continue
                    key, val = m.group(1), m.group(2).strip().strip("'\"")
                    if key == "name" and not name:
                        name = val
                    elif key == "cwd" and not cwd:
                        cwd = val
                    elif key == "repository" and not repo:
                        repo = val
                    elif key == "updated_at":
                        updated = val
        except OSError:
            continue
        ts_s, ts_d = fmt_ts(updated)
        if name.lower() in ("false", "none", "null", ""):
            name = "(untitled session)"
        sessions.append({
            "tool": "copilot",
            "title": name,
            "folder": cwd or repo or "unknown",
            "prompt": "",
            "session_id": sid,
            "stamp": ts_s,
            "stamp_display": ts_d,
            "agent": "",
            "model": "",
            "reopen": f"copilot --session {sid}",
        })


def resume_cmd(s):
    """Full command to open the session's folder and resume it."""
    folder = s["folder"]
    reopen = s["reopen"]
    if folder and folder != "unknown":
        return f'cd "{folder}" && {reopen}'
    return reopen


def build_html(sessions, generated_at):
    rows_sorted = sorted(sessions, key=lambda s: s["stamp"], reverse=True)
    rows = []
    for s in rows_sorted:
        folder = html.escape(s["folder"])
        title = html.escape(s["title"])
        prompt = html.escape(s["prompt"]) or ""
        # description combines title + prompt + folder for full-text search
        searchtext = html.escape(" ".join(p for p in
                                          [s["title"], s["prompt"], s["folder"],
                                           s["session_id"], s["agent"], s["model"]]
                                          if p)).lower()
        stamp = html.escape(s["stamp_display"] or "")
        tool = html.escape(s["tool"])
        sid = html.escape(s["session_id"])
        agent = html.escape(s["agent"])
        model = html.escape(s["model"])
        cmd = html.escape(resume_cmd(s))
        prompt_short = prompt if len(prompt) <= 200 else prompt[:197] + "&#8230;"
        meta = (agent + (" " + model if agent else model)).strip()
        rows.append(
            "<tr class='row' data-search='" + searchtext + "'>"
                "<td class='tool tool-" + tool + "'>" + tool + "</td>"
                "<td class='title'><span class='openlink' title='" + folder + "'>" + title + "</span></td>"
                "<td class='prompt'>" + (prompt_short or "<span class='muted'>no prompt text</span>") + "</td>"
                "<td class='folder'>" + folder + "</td>"
                "<td class='stamp'>" + stamp + "</td>"
                "<td class='meta'>" + meta + "</td>"
                "<td class='sid'>" + sid + "</td>"
                "<td class='resume'>"
                    "<div class='cmdbox'>"
                        "<input class='cmd' type='text' readonly spellcheck='false' "
                            "value='" + cmd + "' title='" + cmd + "'>"
                        "<button class='copy' type='button'>Copy</button>"
                    "</div>"
                "</td>"
                "</tr>\n"
            )
    rows_html = "\n".join(rows)
    counts = {t: sum(1 for x in sessions if x["tool"] == t)
              for t in ("claude", "opencode", "copilot")}
    tpl = TEMPLATE
    return (tpl
            .replace("__GENERATED_AT__", html.escape(generated_at))
            .replace("__ROWS__", rows_html)
            .replace("__TOTAL__", str(len(sessions)))
            .replace("__CLAUDE__", str(counts["claude"]))
            .replace("__OPENCODE__", str(counts["opencode"]))
            .replace("__COPILOT__", str(counts["copilot"])))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Session Finder</title>
<style>
  :root { --bg:#0b1020; --panel:#121a2e; --panel-2:#18233d; --text:#edf3ff; --muted:#a6b3cb; --line:#2a3858; --accent:#62d9c4; --accent-2:#8ea7ff; --shadow:0 16px 50px rgba(0,0,0,.22); }
  * { box-sizing:border-box; }
  body { margin:0; color:var(--text); background:radial-gradient(circle at 10% 0%, #1b2a4b 0, transparent 34rem), var(--bg); font:15px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  .wrap { width:min(1500px, calc(100% - 32px)); margin:0 auto; }
  header { padding:48px 0 26px; }
  .eyebrow { color:var(--accent); font-weight:700; letter-spacing:.12em; text-transform:uppercase; font-size:12px; }
  h1 { margin:8px 0 10px; font-size:clamp(1.9rem, 4vw, 3.4rem); line-height:.98; letter-spacing:-.05em; max-width:820px; }
  .intro { color:var(--muted); max-width:780px; font-size:16px; }
  .snapshot { background:rgba(18,26,46,.9); border:1px solid var(--line); box-shadow:var(--shadow); border-radius:18px; padding:18px; display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:22px; }
  .stat { background:var(--panel-2); border-radius:12px; padding:12px; }
  .stat strong { display:block; font-size:18px; color:var(--accent); }
  .stat span { color:var(--muted); font-size:12px; }
  .toolbar { background:rgba(18,26,46,.9); border:1px solid var(--line); box-shadow:var(--shadow); border-radius:14px; padding:12px; margin-bottom:22px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  #q { flex:1 1 300px; min-width:210px; padding:10px 13px; font-size:14px; border:1px solid var(--line); border-radius:9px; background:#0c1428; color:var(--text); outline:none; font:inherit; }
  #q:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(98,217,196,.12); }
  .filters { display:flex; gap:8px; flex-wrap:wrap; }
  .filters button { padding:6px 13px; border:1px solid var(--line); border-radius:99px; background:var(--panel-2); color:var(--muted); cursor:pointer; font-size:13px; }
  .filters button.active { border-color:var(--accent); color:var(--accent); }
  #count { color:var(--muted); font-size:13px; white-space:nowrap; margin-left:auto; }
  .tablecard { background:rgba(18,26,46,.9); border:1px solid var(--line); box-shadow:var(--shadow); border-radius:18px; padding:6px 8px 8px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  thead th { text-align:left; color:var(--muted); font-weight:500; font-size:11px; text-transform:uppercase; letter-spacing:.04em; padding:10px; border-bottom:1px solid var(--line); }
  td { padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
  tr.row { cursor:pointer; }
  tr.row:hover { background:#18233d; }
  td.tool { text-transform:capitalize; font-weight:600; white-space:nowrap; }
  td.title { font-weight:500; min-width:220px; }
  td.prompt { color:var(--muted); min-width:260px; }
  td.folder { font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12px; color:#8fc7ff; min-width:220px; }
  td.stamp { white-space:nowrap; color:var(--muted); }
  td.meta { color:var(--muted); max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  td.sid { color:var(--muted); font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:11px; }
  td.resume { min-width:340px; }
  .tool-claude { color:#e08a5a; } .tool-opencode { color:#62d9c4; } .tool-copilot { color:#4da3ff; }
  .muted { color:var(--muted); }
  .openlink { color:var(--accent); }
  .cmdbox { display:flex; gap:6px; }
  .cmd { flex:1; min-width:0; border:1px solid var(--line); border-radius:6px; background:#0c1428; color:var(--accent); padding:6px 9px; font:12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; outline:none; }
  .copy { border:1px solid var(--line); border-radius:6px; background:var(--panel-2); color:var(--text); padding:0 12px; cursor:pointer; font-size:12px; white-space:nowrap; }
  .copy:hover { border-color:var(--accent); }
  .note { color:var(--muted); font-size:12px; padding:10px 4px 0; }
  footer { color:var(--muted); padding:26px 0 55px; font-size:13px; }
  footer code { color:var(--accent); font:.92em ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  @media (max-width:720px) {
    .wrap { width:min(100% - 20px, 1500px); }
    header { padding-top:32px; }
    .snapshot { grid-template-columns:repeat(2,1fr); }
    .toolbar { align-items:stretch; }
    #count { margin-left:0; }
  }
</style>
</head>
<body>
  <header class="wrap">
    <div class="eyebrow">MAG Tools (Linux) &middot; local session index &middot; nothing leaves this machine</div>
    <h1>AI Session Finder</h1>
    <p class="intro">Past conversations from all three terminal AI coders &mdash; Claude Code, OpenCode, and Copilot &mdash; indexed from your local stores. Search, then copy a resume command to reopen the folder and run the session.</p>
  </header>

  <main class="wrap">
    <section class="snapshot" aria-label="Index snapshot">
      <div class="stat"><strong>__TOTAL__</strong><span>sessions indexed</span></div>
      <div class="stat"><strong>__CLAUDE__</strong><span>claude sessions</span></div>
      <div class="stat"><strong>__OPENCODE__</strong><span>opencode sessions</span></div>
      <div class="stat"><strong>__COPILOT__</strong><span>copilot sessions</span></div>
    </section>

    <div class="toolbar">
      <input id="q" type="text" placeholder="Search name, prompt, folder, id, agent..." autofocus>
      <div class="filters" id="filters">
        <button data-tool="all" class="active">All</button>
        <button data-tool="claude">Claude</button>
        <button data-tool="opencode">OpenCode</button>
        <button data-tool="copilot">Copilot</button>
      </div>
      <span id="count"></span>
    </div>

    <div class="tablecard">
    <table>
      <thead><tr>
        <th>Tool</th><th>Title</th><th>First prompt</th><th>Folder</th><th>Updated</th><th>Agent/Model</th><th>ID</th><th>Resume command</th>
      </tr></thead>
      <tbody id="rows">
__ROWS__
      </tbody>
    </table>
    <p class="note">Click a row (or its <b>Copy</b> button) to copy the full resume command to your clipboard, then paste it into a terminal.</p>
    </div>
  </main>

  <footer class="wrap">Generated __GENERATED_AT__ &middot; click a row or copy a resume command to reopen and run that session.</footer>
<script>
  var rows = Array.prototype.slice.call(document.querySelectorAll('#rows tr.row'));
  var q = document.getElementById('q');
  var count = document.getElementById('count');
  var activeTool = 'all';

  function filter() {
    var term = q.value.trim().toLowerCase();
    var visible = 0;
    rows.forEach(function (r) {
      var ok = true;
      var tool = r.querySelector('.tool').textContent;
      if (activeTool !== 'all' && tool !== activeTool) ok = false;
      if (ok && term && r.dataset.search.indexOf(term) === -1) ok = false;
      r.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    count.textContent = visible + ' / ' + rows.length;
  }

  document.getElementById('filters').addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    Array.prototype.forEach.call(this.children, function (x) { x.classList.remove('active'); });
    b.classList.add('active');
    activeTool = b.dataset.tool;
    filter();
  });
  q.addEventListener('input', filter);

  function copyCmd(input, btn) {
    input.select();
    var done = function () {
      if (!btn) return;
      var old = btn.textContent;
      btn.textContent = 'Copied';
      setTimeout(function () { btn.textContent = old; }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(input.value).then(done, function () { done(); });
    } else {
      document.execCommand('copy');
      done();
    }
  }

  rows.forEach(function (r) {
    r.addEventListener('click', function (e) {
      if (e.target.classList && (e.target.classList.contains('copy') || e.target.classList.contains('cmd'))) return;
      copyCmd(r.querySelector('.cmd'), null);
    });
  });

  document.querySelectorAll('.copy').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      copyCmd(btn.parentNode.querySelector('.cmd'), btn);
    });
  });
</script>
</body>
</html>
"""


def search_and_print(sessions, terms):
    """Filter sessions by ALL terms (case-insensitive, matched against title,
    prompt, folder, session id, agent and model) and print them as readable
    plain-text rows an agent can ingest and quote back."""
    terms = [t.lower() for t in terms if t.strip()]
    matches = []
    for s in sorted(sessions, key=lambda x: x["stamp"], reverse=True):
        blob = " ".join(p for p in
                        [s["title"], s["prompt"], s["folder"],
                         s["session_id"], s["agent"], s["model"]] if p).lower()
        if all(t in blob for t in terms):
            matches.append(s)
    if not terms:
        matches = sorted(sessions, key=lambda x: x["stamp"], reverse=True)
    if not matches:
        print("No sessions matched the given terms.")
        return
    for s in matches:
        title = s["title"].replace("\n", " ").strip()
        prompt = " ".join(s["prompt"].split())
        if len(prompt) > 160:
            prompt = prompt[:157] + "..."
        print(f"[{s['tool']}] {title}")
        if prompt:
            print(f"    prompt: {prompt}")
        print(f"    folder: {s['folder']}")
        print(f"    updated: {s['stamp_display']}   id: {s['session_id']}")
    print(f"\n{len(matches)} match(es)")


def main():
    ap = argparse.ArgumentParser(
        description="Build the MAG session index. With --search, prints matching "
                    "sessions as plain text instead of writing HTML.")
    ap.add_argument("-o", "--output", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.html"))
    ap.add_argument("-f", "--force", action="store_true", help="always rewrite the output file")
    ap.add_argument("-s", "--search", nargs="+", metavar="TERM",
                    help="search mode: print sessions matching ALL terms as text")
    args = ap.parse_args()

    sessions = []
    scan_claude(sessions)
    scan_opencode(sessions)
    scan_copilot(sessions)

    if args.search is not None:
        search_and_print(sessions, args.search)
        return

    generated_at = now_iso()
    # skip write if unchanged and not forced
    out = args.output
    html_out = build_html(sessions, generated_at)
    if not args.force and os.path.isfile(out):
        try:
            with open(out, "r", encoding="utf-8") as fh:
                if fh.read().split("</body>")[0] == html_out.split("</body>")[0]:
                    print(f"No changes — {out} already up to date.")
                    return
        except OSError:
            pass
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_out)
    print(f"Wrote {len(sessions)} sessions to {out}")


if __name__ == "__main__":
    main()
