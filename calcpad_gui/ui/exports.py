"""ExportActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import GLib
from calcpad_gui.bootstrap import Gio
from calcpad_gui.bootstrap import Gtk
from calcpad_gui.config import save_settings
from pathlib import Path
import re
import shutil
import subprocess
import threading

class ExportActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _reserve_quick_docx(self):
        documents = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
        folder = Path(documents or str(Path.home() / "Documents")) / "Calcpad Exports"
        folder.mkdir(parents=True, exist_ok=True)
        highest = 0
        for entry in folder.iterdir():
            match = re.fullmatch(r"worksheet_(\d+)\.docx", entry.name)
            if match:
                highest = max(highest, int(match.group(1)))
        index = highest + 1
        while True:
            target = folder / f"worksheet_{index}.docx"
            try:
                # Exclusive reservation prevents overwrites across windows.
                with target.open("xb"):
                    pass
                return target
            except FileExistsError:
                index += 1

    def _open_quick_docx(self, target):
        # Prefer native ONLYOFFICE; otherwise respect the desktop association
        # (also supports installations registered through Flatpak or Snap).
        for name in ("onlyoffice-desktopeditors", "desktopeditors"):
            executable = shutil.which(name)
            if executable:
                subprocess.Popen([executable, str(target)])
                return
        Gio.AppInfo.launch_default_for_uri(target.resolve().as_uri(), None)

    def _quick_export_docx(self):
        if getattr(self, "_quick_docx_busy", False):
            self.set_status("Word export is already running.")
            return
        try:
            # Read GTK state on the main thread, before starting the worker.
            source = self._code_with_decimal_places(self._get_text_for_cli())
            decimal_comma = self.settings.get("decimal_comma", False)
            target = self._reserve_quick_docx()
        except Exception as exc:
            self.set_status(f"Cannot prepare Word export: {exc}")
            return
        self._quick_docx_busy = True
        self.set_status(f"Exporting -> {target.name}...")

        def worker():
            out = None
            error = None
            success = False
            try:
                out, error = self._run_cli("docx", body_only=False, source_text=source)
                if not error:
                    if not out or not Path(out).is_file() or Path(out).stat().st_size == 0:
                        raise OSError("Calcpad did not produce a DOCX file.")
                    self._postprocess_docx(str(out), bool(decimal_comma))
                    shutil.move(str(out), str(target))
                    success = True
            except Exception as exc:
                error = f"Word export failed: {exc}"
            finally:
                if not success:
                    try:
                        target.unlink()
                    except OSError:
                        pass
                if out:
                    try:
                        Path(out).unlink(missing_ok=True)
                    except OSError:
                        pass

            def finish():
                self._quick_docx_busy = False
                if not success:
                    self.set_status(f"Word export failed: {error}")
                    return False
                try:
                    self._open_quick_docx(target)
                    self.set_status(f"Exported and opening -> {target}")
                except Exception as exc:
                    self.set_status(f"Saved -> {target}; could not open: {exc}")
                return False
            GLib.idle_add(finish)

        try:
            threading.Thread(target=worker, daemon=True).start()
        except Exception as exc:
            self._quick_docx_busy = False
            try:
                target.unlink()
            except OSError:
                pass
            self.set_status(f"Could not start Word export: {exc}")

    def _export(self, fmt):
        dlg = Gtk.FileDialog(); dlg.set_title(f"Export as {fmt.upper()}")
        base = Path(self.current_file).stem if self.current_file else "report"
        dlg.set_initial_name(f"{base}.{fmt}")
        last = self.settings.get("last_dir") or str(Path.home())
        try: dlg.set_initial_folder(Gio.File.new_for_path(last))
        except GLib.Error: pass
        dlg.save(self, None, lambda d,r: self._export_done(d,r,fmt))

    def _export_done(self, dlg, res, fmt):
        try: f = dlg.save_finish(res); target = f.get_path()
        except GLib.Error: return
        self.set_status(f"Exporting {fmt.upper()}...")
        def worker():
            out,err = self._run_cli(fmt, body_only=False)
            def finish():
                if err:
                    self.webview.load_html(err, "file:///"); self.set_status("Export error.")
                else:
                    try:
                        shutil.move(out, target)
                        tp = Path(target)
                        ext = tp.suffix.lower()
                        decimal_comma = bool(self.settings.get("decimal_comma", False))
                        if ext == ".docx":
                            self._postprocess_docx(str(tp), decimal_comma)
                        elif decimal_comma and ext in (".html", ".htm"):
                            txt = tp.read_text(encoding="utf-8")
                            tp.write_text(self._apply_decimal_comma_html(txt), encoding="utf-8")
                        self.settings["last_dir"] = str(Path(target).parent)
                        save_settings(self.settings)
                        self.set_status(f"Exported -> {target}")
                    except OSError as e: self.set_status(f"Move failed: {e}")
                return False
            GLib.idle_add(finish)
        threading.Thread(target=worker, daemon=True).start()
