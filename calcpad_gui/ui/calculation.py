"""CalculationActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import GLib
from calcpad_gui.services.cli import run_cli
from pathlib import Path
import os
import threading

class CalculationActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def on_text_changed(self, *_):
        if not self.auto_toggle.get_active(): return
        if self._debounce_id is not None: GLib.source_remove(self._debounce_id)
        self._debounce_id = GLib.timeout_add(700, self._debounced_run)

    def _debounced_run(self):
        self._debounce_id = None; self.on_run(None); return False

    def _run_cli(self, out_format, body_only, source_text=None):
        return run_cli(
            self._cli_cmd, self._cli_hint, out_format, body_only,
            lambda: self._code_with_decimal_places(self._get_text_for_cli()),
            self._wrap_preview, GLib.markup_escape_text, source_text,
        )

    def on_run(self, _btn):
        if self._run_busy or self._closing: return
        self._run_busy = True; self.set_status("Calculating...")
        def worker():
            out,err = self._run_cli("html", body_only=True)
            GLib.idle_add(self._finish_run, out, err)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self, out, err):
        try:
            if self._closing: return False
            if err:
                self.webview.load_html(err, "file:///"); self.set_status("Error - see preview.")
                return False
            try: html = Path(out).read_text(encoding="utf-8")
            except OSError as e: self.set_status(f"Read error: {e}"); return False
            if self.settings.get("decimal_comma", False):
                html = self._apply_decimal_comma_html(html)
            base = f"file://{Path(out).parent}/"
            self._load_preview_preserving_scroll(self._wrap_preview(html), base)
            self.set_status(f"OK - {len(html):,} bytes of output.")
        finally:
            if out:
                try: os.unlink(out)
                except OSError: pass
            self._run_busy = False
        return False
