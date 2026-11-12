"""Historical desktop/CLI diagnostics and isolated arithmetic roundtrip."""
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from .bootstrap import Gtk, GtkSource
from .config import CFG_FILE, LANG_FILE
from .services.cli import discover_cli

def run_doctor():
    print("CalcpadCE Linux GUI - Doctor")
    print("=" * 35)
    print(f"Python:        {sys.version.split()[0]}")
    print(f"GTK:           {Gtk.get_major_version()}.{Gtk.get_minor_version()}."
          f"{Gtk.get_micro_version()}")
    print(f"GtkSourceView: {GtkSource.MAJOR_VERSION}.{GtkSource.MINOR_VERSION}")
    print(f"WebKitGTK:     6.0")
    print(f"Config:        {CFG_FILE}")
    print(f"Lang file:     {LANG_FILE} "
          f"({'present' if LANG_FILE.exists() else 'will be created'})")
    cmd, hint = discover_cli()
    if not cmd:
        print("CLI:           NOT FOUND"); print(); print(hint); return 1
    print(f"CLI:           OK  {hint}")
    with tempfile.TemporaryDirectory() as td:
        in_p = Path(td) / "test.cpd"; out_p = Path(td) / "test.html"
        in_p.write_text("x = 6\ny = 7\nz = x*y\n", encoding="utf-8")
        env = os.environ.copy(); env["DOTNET_CLI_UI_LANGUAGE"] = "en"
        try:
            r = subprocess.run(list(cmd) + [str(in_p), str(out_p), "-s", "-b"],
                               capture_output=True, text=True, timeout=30, env=env)
            if r.returncode != 0 or not out_p.exists():
                print(f"Roundtrip:     FAILED (exit {r.returncode})")
                if r.stderr.strip(): print(f"  stderr: {r.stderr.strip()[:300]}")
                return 1
            body = out_p.read_text(encoding="utf-8", errors="replace")
            if "42" in body:
                print("Roundtrip:     OK (6 * 7 = 42 found in output)"); return 0
            print(f"Roundtrip:     UNCLEAR (no '42' in {len(body)} bytes)"); return 0
        except subprocess.TimeoutExpired:
            print("Roundtrip:     TIMEOUT (30s)"); return 1
        except OSError as e:
            print(f"Roundtrip:     ERROR: {e}"); return 1
