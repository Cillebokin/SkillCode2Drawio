# Draw.io CLI Export

Use this reference only when the user asks for PNG, SVG, PDF, or another exported artifact in addition to the native `.drawio` file.

## Preferred Rule

Always keep the source `.drawio` file. Exports are secondary artifacts for viewing, sharing, or embedding.

## Supported Export Formats

| Format | Embed XML | Notes |
| --- | --- | --- |
| `png` | Yes, use `-e` | Viewable everywhere; editable in draw.io when embedded |
| `svg` | Yes, use `-e` | Scalable; editable in draw.io when embedded |
| `pdf` | Yes, use `-e` | Printable; editable in draw.io when embedded |
| `jpg` | No | Lossy; avoid unless explicitly requested |

## Command

```powershell
drawio -x -f <format> -e -b 10 -o <output> <input.drawio>
```

Useful flags:

- `-x` / `--export`: export mode.
- `-f` / `--format`: output format.
- `-e` / `--embed-diagram`: embed editable diagram XML. Use for PNG, SVG, PDF.
- `-o` / `--output`: output path.
- `-b` / `--border`: border width around the diagram.
- `-t` / `--transparent`: transparent PNG background.
- `-s` / `--scale`: scale output.
- `--width` / `--height`: fit output to size while preserving aspect ratio.
- `-a` / `--all-pages`: export all pages for PDF.
- `-p` / `--page-index`: export a specific 1-based page.

## Windows CLI Lookup

Try PATH first:

```powershell
Get-Command drawio -ErrorAction SilentlyContinue
Get-Command draw.io -ErrorAction SilentlyContinue
```

Then common locations:

```text
C:\Program Files\draw.io\draw.io.exe
C:\Program Files (x86)\draw.io\draw.io.exe
%LOCALAPPDATA%\Programs\draw.io\draw.io.exe
%USERPROFILE%\AppData\Local\Programs\draw.io\draw.io.exe
```

If draw.io Desktop was installed as a portable app or extracted manually, ask the user for the executable path and use that absolute path for the export command. Do not assume a machine-specific tools directory.

When using a full path with spaces, call it with PowerShell's invocation operator:

```powershell
$drawio = 'C:\Path\To\draw.io.exe'
& $drawio -x -f png -e -b 10 -o output.drawio.png input.drawio
```

## Naming

Use double extensions for exports:

```text
login-flow.drawio
login-flow.drawio.png
login-flow.drawio.svg
login-flow.drawio.pdf
```

This keeps the editable source and exported artifacts visually grouped.

