"""Explicit compatibility facade: all historical callbacks live on this window.

Behavior classes are stateless namespaces sharing this window's GTK state. They
never call super() or define __init__; only this composition root initializes.
"""
from __future__ import annotations
import os
from .bootstrap import Gtk, GLib, Gdk
from .data import APP_TITLE
from .config import load_settings
from .language import ensure_calcpad_language
from .services.cli import discover_cli
from .domain.expressions import ExpressionTransforms
from .domain.numbers import NumberFormatting
from .domain.docx import DocxProcessing
from .preview.html import PreviewRenderer
from .ui.editor import EditorActions
from .ui.autocomplete import AutocompleteActions
from .ui.search import SearchActions
from .ui.chrome import ChromeActions
from .ui.keyboard import KeyboardActions
from .ui.preview import PreviewActions
from .ui.calculation import CalculationActions
from .ui.files import FileActions
from .ui.exports import ExportActions

class CalcpadWindow(
    ExpressionTransforms,
    NumberFormatting,
    DocxProcessing,
    PreviewRenderer,
    EditorActions,
    AutocompleteActions,
    SearchActions,
    ChromeActions,
    KeyboardActions,
    PreviewActions,
    CalculationActions,
    FileActions,
    ExportActions,
    Gtk.ApplicationWindow,
):
    def __init__(self, app):
        super().__init__(application=app, title=APP_TITLE)
        self.set_default_size(1500, 950)
        self.settings = load_settings()
        self.settings.setdefault("decimal_places", 3)
        self.settings.setdefault("keyboard_favorites", [])
        self.settings.setdefault("keyboard_visible", True)
        self.current_file = None
        self._debounce_id = None
        self._run_busy = False
        self._closing = False
        self._cli_cmd, self._cli_hint = discover_cli()
        self._calcpad_lang_ok = ensure_calcpad_language()

        css = Gtk.CssProvider()
        css.load_from_string(
            ".calcpad-editor textview { font-family: monospace; font-size: 11pt; }"
            ".kbd-btn { font-size: 10pt; min-width: 72px; min-height: 30px; padding: 3px 8px; border-radius: 9px; }"
            ".kbd-btn.warn { color: #c43; font-weight: bold; }"
            ".calcpad-keyboard { background: transparent; border-top: none; padding: 6px; }"
            ".status     { padding: 4px 10px; }"
            ".hint       { padding: 0 10px; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build_headerbar()
        self._build_layout()
        self._apply_app_theme()
        self._start_with_empty_document()

        if os.environ.get("CALCPAD_GUI_EMPTY") == "1":
            try:
                self.buffer.set_text("")
                self.buffer.set_modified(False)
                self.current_file = None
            except Exception:
                pass
        self._setup_zoom_controls()
        self._setup_line_navigation_controls()
        self._setup_format_controls()
        self._setup_autocomplete_controls()
        self._install_shortcuts()
        self.buffer.connect("modified-changed", self._on_modified_changed)
        self.buffer.connect("notify::cursor-position", self._on_editor_cursor_position_changed)
        self._setup_editor_highlighting()
        self.connect("close-request", self._on_close_request)
        GLib.timeout_add(400, self._initial_run)
