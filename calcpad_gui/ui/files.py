"""FileActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import GLib
from calcpad_gui.bootstrap import Gio
from calcpad_gui.bootstrap import Gtk
from calcpad_gui.config import save_settings
from calcpad_gui.data import APP_TITLE
from calcpad_gui.data import DEFAULT_SAMPLE
from pathlib import Path
import subprocess
import sys

class FileActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _on_modified_changed(self, _buf): self._refresh_title()

    def _refresh_title(self):
        name = Path(self.current_file).name if self.current_file else "[Untitled]"
        prefix = "• " if self.buffer.get_modified() else ""
        self.set_title(f"{prefix}{name} - {APP_TITLE}")

    def is_dirty(self): return self.buffer.get_modified()

    def _on_close_request(self, _w):
        if self._closing or not self.is_dirty(): return False
        dlg = Gtk.AlertDialog(); dlg.set_modal(True)
        dlg.set_message("Save changes before closing?")
        dlg.set_detail("Your unsaved edits will be lost otherwise.")
        dlg.set_buttons(["Discard","Cancel","Save"])
        dlg.set_cancel_button(1); dlg.set_default_button(2)
        dlg.choose(self, None, self._on_close_response)
        return True

    def _on_close_response(self, dlg, res):
        try: choice = dlg.choose_finish(res)
        except GLib.Error: return
        if choice == 0: self._closing = True; self.close()
        elif choice == 2: self.on_save(None, _on_done=self._close_after_save)

    def _close_after_save(self, ok):
        if ok: self._closing = True; self.close()

    def on_new(self, _btn=None):
        try:
            subprocess.Popen(["gtk-launch", "calcpad-gui"])
            self.set_status("Opened new window.")
        except Exception:
            try:
                subprocess.Popen([sys.executable, "-m", "calcpad_gui"])
                self.set_status("Opened new window.")
            except Exception as e:
                self.set_status(f"Could not open new window: {e}")

    def _do_new(self):
        self.buffer.set_text(DEFAULT_SAMPLE); self.buffer.set_modified(False)
        self.current_file = None; self._refresh_title(); self.on_run(None)

    def _confirm_discard(self, after):
        dlg = Gtk.AlertDialog(); dlg.set_modal(True)
        dlg.set_message("Discard unsaved changes?")
        dlg.set_buttons(["Cancel","Discard"])
        dlg.set_cancel_button(0); dlg.set_default_button(0)
        def done(d,res):
            try: choice = d.choose_finish(res)
            except GLib.Error: choice = 0
            after(choice == 1)
        dlg.choose(self, None, done)

    def on_open(self, _btn):
        if self.is_dirty(): self._confirm_discard(lambda ok: ok and self._show_open_dialog())
        else: self._show_open_dialog()

    def _show_open_dialog(self):
        dlg = Gtk.FileDialog(); dlg.set_title("Open Calcpad worksheet")
        flt = Gtk.FileFilter(); flt.set_name("Calcpad (*.cpd, *.txt)")
        for pat in ("*.cpd","*.CPD","*.txt","*.TXT"): flt.add_pattern(pat)
        store = Gio.ListStore.new(Gtk.FileFilter); store.append(flt)
        dlg.set_filters(store)
        last = self.settings.get("last_dir") or str(Path.home())
        try: dlg.set_initial_folder(Gio.File.new_for_path(last))
        except GLib.Error: pass
        dlg.open(self, None, self._open_done)

    def _open_done(self, dlg, res):
        try: f = dlg.open_finish(res); self._open_path(f.get_path())
        except GLib.Error: pass

    def open_file_path(self, path):
        if self.is_dirty(): self._confirm_discard(lambda ok: ok and self._open_path(path))
        else: self._open_path(path)

    def _open_path(self, path):
        try: self.buffer.set_text(Path(path).read_text(encoding="utf-8"))
        except OSError as e: self.set_status(f"Open failed: {e}"); return
        self.buffer.set_modified(False); self.current_file = path
        self.settings["last_dir"] = str(Path(path).parent)
        self._add_recent(path); self._refresh_title(); self.on_run(None)

    def on_save(self, _btn, _on_done=None):
        if self.current_file:
            try:
                Path(self.current_file).write_text(self._get_buffer_text(), encoding="utf-8")
                self.buffer.set_modified(False)
                self.set_status(f"Saved: {self.current_file}")
                if _on_done: _on_done(True)
            except OSError as e:
                self.set_status(f"Save failed: {e}")
                if _on_done: _on_done(False)
            return
        self._show_save_dialog(_on_done)

    def on_save_as(self, _btn): self._show_save_dialog(None)

    def _show_save_dialog(self, on_done):
        dlg = Gtk.FileDialog(); dlg.set_title("Save worksheet")
        base = Path(self.current_file).stem if self.current_file else "worksheet"
        dlg.set_initial_name(f"{base}.cpd")
        last = self.settings.get("last_dir") or str(Path.home())
        try: dlg.set_initial_folder(Gio.File.new_for_path(last))
        except GLib.Error: pass
        dlg.save(self, None, lambda d,r: self._save_done(d,r,on_done))

    def _save_done(self, dlg, res, on_done):
        try:
            f = dlg.save_finish(res); path = f.get_path()
            Path(path).write_text(self._get_buffer_text(), encoding="utf-8")
            self.buffer.set_modified(False); self.current_file = path
            self.settings["last_dir"] = str(Path(path).parent)
            self._add_recent(path); self._refresh_title()
            self.set_status(f"Saved: {path}")
            if on_done: on_done(True)
        except GLib.Error:
            if on_done: on_done(False)
        except OSError as e:
            self.set_status(f"Save failed: {e}")
            if on_done: on_done(False)

    def _add_recent(self, path):
        rec = self.settings.setdefault("recent", [])
        if path in rec: rec.remove(path)
        rec.insert(0, path); self.settings["recent"] = rec[:10]
        save_settings(self.settings); self._refresh_recent_menu()
