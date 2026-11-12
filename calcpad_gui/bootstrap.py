"""Single GI version gate. Import only from desktop-facing modules."""
import sys
import textwrap
import gi

_REQUIRED = [("Gtk","4.0"), ("GtkSource","5"), ("WebKit","6.0")]
for ns,ver in _REQUIRED:
    try: gi.require_version(ns, ver)
    except ValueError as e:
        sys.exit(textwrap.dedent(f"""\
            ERROR: Required GI namespace {ns} {ver} not available.
            Install on Linux Mint 22 / Ubuntu 24.04 / Debian 13:
              sudo apt install python3-gi gir1.2-gtk-4.0 \\
                               gir1.2-gtksource-5 gir1.2-webkit-6.0
            Details: {e}
            """))

from gi.repository import Gtk, GtkSource, WebKit, Gio, GLib, Gdk  # noqa

_MIN_GTK = (4, 10)
_have = (Gtk.get_major_version(), Gtk.get_minor_version())
if _have < _MIN_GTK:
    sys.exit(f"ERROR: GTK {_MIN_GTK[0]}.{_MIN_GTK[1]}+ required, found "
             f"{_have[0]}.{_have[1]}. Please upgrade your distribution.")

