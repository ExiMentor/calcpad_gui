"""GTK application lifecycle and command-line entrypoint."""
import argparse
import sys
from .bootstrap import Gtk, Gio, GLib
from .config import initialize_paths

initialize_paths(GLib.get_user_config_dir(), GLib.get_user_data_dir())

from .data import APP_ID
from .window import CalcpadWindow
from .doctor import run_doctor

class CalcpadApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE)
        self._win = None
    def do_activate(self):
        if self._win is None: self._win = CalcpadWindow(self)
        self._win.present()
    def do_open(self, files, _n, _hint):
        self.do_activate()
        if files and self._win is not None:
            path = files[0].get_path()
            if path: GLib.idle_add(self._win.open_file_path, path)

def main():
    ap = argparse.ArgumentParser(prog="calcpad-gui",
                                 description="Linux GUI for CalcpadCE")
    ap.add_argument("--doctor", action="store_true",
                    help="Diagnose environment and exit")
    ap.add_argument("file", nargs="?", help="Optional .cpd file to open")
    args = ap.parse_args()
    if args.doctor: return run_doctor()
    app = CalcpadApp()
    argv = [sys.argv[0]]
    if args.file: argv.append(args.file)
    return app.run(argv)
