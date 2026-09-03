# utils_html_to_text

Strips HTML down to plain text — concatenates the text content of every `<p>`
tag, double-newline separated. Not a full HTML→text converter (ignores
headings, lists, tables — paragraphs only). Unchanged from the Windows repo;
pure Python, no OS-specific code.

## Usage

```
python3 html_to_text.py input.html [output.txt]
```

## Requirements

```
pip install -r requirements.txt
```
