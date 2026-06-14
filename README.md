# calcpad-gui

A native GTK 4 desktop GUI for [CalcpadCE](https://github.com/imartincei/CalcpadCE),
the open-source engineering worksheet engine.

> Independent frontend: calculations are performed by CalcpadCE CLI (Calcpad.Cli).

## Features
- GtkSourceView editor with Calcpad syntax highlighting
- On-screen keyboard with Greek letters, operators & math functions
- Live HTML preview via WebKitGTK (auto-refresh while typing)
- Light/Dark preview toggle
- Optional decimal-comma display (German/European locale)
- Export to HTML, PDF and DOCX
- Shortcuts (Ctrl+N/O/S, F5, …)

## Requirements
Debian 13 / Ubuntu 24.04 / Linux Mint 22 or newer:
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 \
                 gir1.2-gtksource-5 gir1.2-webkit-6.0 \
                 dotnet-runtime-8.0

