# video_yt_dlp

Downloads video/audio from YouTube and 1000+ other sites.

On the Windows repo this shipped a bundled `yt-dlp.exe` binary. On Linux,
`yt-dlp` is already installed system-wide via apt (`/usr/bin/yt-dlp`) — no
bundled binary needed, and apt keeps it updated. If it's ever missing:

```
sudo apt install yt-dlp
# or, for a newer release than Debian/Ubuntu ships:
python3 -m pip install --user -U yt-dlp
```

## Usage

```
yt-dlp <URL> -o "$HOME/Downloads/%(title)s.%(ext)s" --merge-output-format mkv [options]
```

## Key options

| Flag | Description |
|------|-------------|
| `-x` | Extract audio only |
| `--audio-format mp3\|wav\|m4a\|...` | Audio format (use with `-x`) |
| `-f <format>` | Select specific quality/format code |
| `-F` | List all available formats for a URL |
| `-o <template>` | Output filename template |
| `--write-subs` | Download subtitles |
| `--sub-lang en` | Select subtitle language |
| `--playlist-start N` / `--playlist-end N` | Partial playlist download |
| `--cookies-from-browser brave` | Use Brave cookies (age-gated/private content) |

## Requirements

`yt-dlp` on PATH (apt package, confirmed present at `/usr/bin/yt-dlp`).
