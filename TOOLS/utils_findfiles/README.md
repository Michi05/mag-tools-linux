# utils_findfiles

Searches for files whose name contains a given string.

Ported from `FindFilesByName.ps1` (a `Get-ChildItem` wrapper) to a thin bash
wrapper around `find` — `find` already does this natively on Linux, so the
wrapper mainly exists to keep the same CLI shape and "no matches" messaging
as the Windows version, for consistency.

## Usage

```
./find_files.sh -s SEARCH_STRING [-p PATH] [-r]
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `-s` | Yes | — | Substring to match in filename (case-insensitive) |
| `-p` | No | current directory | Directory to search |
| `-r` | No | off | Search all subdirectories |

## Requirements

None beyond standard coreutils/findutils (present on any Linux install).

## Note

For anything beyond simple substring matching, plain `find` or `fd` (if
installed) covers more ground directly — this wrapper exists for parity with
the old tool's exact invocation shape, not because `find` needs wrapping.
