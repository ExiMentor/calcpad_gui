"""EditorActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import GLib
from calcpad_gui.bootstrap import Gdk
from calcpad_gui.bootstrap import Gtk
from calcpad_gui.bootstrap import GtkSource
from calcpad_gui.data import DEFAULT_SAMPLE
import re

class EditorActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _setup_editor_highlighting(self):
        self._editor_highlight_source_id = 0

        try:
            self.buffer.set_highlight_syntax(False)
        except Exception:
            pass

        self._hl_tags = {
            "var": self.buffer.create_tag("calc-var", foreground="#0066dd"),
            "unit": self.buffer.create_tag("calc-unit", foreground="#119911"),
            "func": self.buffer.create_tag("calc-func", foreground="#7a3db8"),
            "number": self.buffer.create_tag("calc-number", foreground="#cc0088"),
            "bracket": self.buffer.create_tag("calc-bracket", foreground="#cc0088"),
            "op": self.buffer.create_tag("calc-op", foreground="#c08030"),
            "keyword": self.buffer.create_tag("calc-keyword", foreground="#cc0088"),
            "text": self.buffer.create_tag("calc-text", foreground="#006400"),
        }

        self.buffer.connect("changed", self._schedule_editor_highlighting)
        GLib.idle_add(self._apply_editor_highlighting)

    def _schedule_editor_highlighting(self, *_args):
        if getattr(self, "_editor_highlight_source_id", 0):
            GLib.source_remove(self._editor_highlight_source_id)

        self._editor_highlight_source_id = GLib.timeout_add(
            120, self._apply_editor_highlighting
        )

    def _apply_editor_highlighting(self):
        self._editor_highlight_source_id = 0

        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        text = self.buffer.get_text(start, end, False)

        for tag in self._hl_tags.values():
            self.buffer.remove_tag(tag, start, end)

        def apply_range(tag_name, a_off, b_off):
            if b_off <= a_off:
                return
            a = self.buffer.get_iter_at_offset(a_off)
            b = self.buffer.get_iter_at_offset(b_off)
            self.buffer.apply_tag(self._hl_tags[tag_name], a, b)

        def apply_regex(tag_name, pattern, flags=0):
            for m in re.finditer(pattern, text, flags):
                apply_range(tag_name, m.start(), m.end())

        comment_ranges = []
        for m in re.finditer(r"(?m)^[ \t]*[\"'“‘].*$", text):
            comment_ranges.append((m.start(), m.end()))

        def in_comment(pos):
            return any(a <= pos < b for a, b in comment_ranges)

        for m in re.finditer(r"(?m)^[ \t]*([A-Za-z_Α-Ωα-ωµμ][A-Za-z0-9_Α-Ωα-ωµμ]*)[ \t]*=", text):
            if not in_comment(m.start(1)):
                apply_range("var", m.start(1), m.end(1))

        for m in re.finditer(
            r"\b(?:sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|sqrt|root|root2|ln|log|exp|abs|min|max|round|trunc|floor|ceiling|random|sign|conj|re|im|phase|area|slope|sup|inf)\b(?=\s*\()",
            text,
            re.IGNORECASE
        ):
            if not in_comment(m.start()):
                apply_range("func", m.start(), m.end())

        unit_pattern = r"(?<![A-Za-z_])(?:MΩ|kΩ|Ω|µF|μF|uF|mF|nF|pF|µH|μH|uH|mH|nH|µV|μV|uV|mV|kV|V|µA|μA|uA|mA|A|mW|kW|W|MHz|kHz|Hz|MPa|kPa|Pa|mm|cm|km|ms|°C|K|m|s)(?![A-Za-z_])"
        for m in re.finditer(unit_pattern, text):
            if not in_comment(m.start()):
                apply_range("unit", m.start(), m.end())

        for m in re.finditer(r"\|\||[+\-*/^=<>≤≥≠%∑∏√·×]", text):
            if not in_comment(m.start()):
                apply_range("op", m.start(), m.end())

        for m in re.finditer(r"[()\[\]{}]", text):
            if not in_comment(m.start()):
                apply_range("bracket", m.start(), m.end())

        for m in re.finditer(
            r"(?m)^\s*#(?:if|else|end\s+if|for|repeat|loop|break|include|hide|show|pre|post)\b",
            text,
            re.IGNORECASE
        ):
            if not in_comment(m.start()):
                apply_range("keyword", m.start(), m.end())

        for a, b in comment_ranges:
            apply_range("text", a, b)

        return False

    def _setup_zoom_controls(self):
        self._editor_zoom = 1.0
        self._preview_zoom = 1.0
        self._editor_css_provider = Gtk.CssProvider()

        try:
            self.editor.add_css_class("calcpad-editor")
        except Exception:
            pass

        self._apply_editor_zoom()
        self._apply_preview_zoom()

        editor_scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        editor_scroll.connect("scroll", self._on_editor_ctrl_scroll_zoom)
        self.editor.add_controller(editor_scroll)

        preview_scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        preview_scroll.connect("scroll", self._on_preview_ctrl_scroll_zoom)
        self.webview.add_controller(preview_scroll)

    def _zoom_from_scroll(self, current_zoom, controller, dy):
        try:
            state = controller.get_current_event_state()
        except Exception:
            state = 0

        if not (state & Gdk.ModifierType.CONTROL_MASK):
            return current_zoom, False

        if dy < 0:
            current_zoom += 0.1
        elif dy > 0:
            current_zoom -= 0.1
        else:
            return current_zoom, True

        return max(0.7, min(2.2, current_zoom)), True

    def _on_editor_ctrl_scroll_zoom(self, controller, dx, dy):
        zoom, handled = self._zoom_from_scroll(getattr(self, "_editor_zoom", 1.0), controller, dy)
        if not handled:
            return False

        self._editor_zoom = zoom
        self._apply_editor_zoom()
        return True

    def _on_preview_ctrl_scroll_zoom(self, controller, dx, dy):
        zoom, handled = self._zoom_from_scroll(getattr(self, "_preview_zoom", 1.0), controller, dy)
        if not handled:
            return False

        self._preview_zoom = zoom
        self._apply_preview_zoom()
        return True

    def _apply_editor_zoom(self):
        zoom = getattr(self, "_editor_zoom", 1.0)
        font_px = int(15 * zoom)

        css = f"""
        #calcpad-editor,
        #calcpad-editor text,
        textview#calcpad-editor,
        textview#calcpad-editor text {{
            font-family: "DejaVu Sans Mono", "Liberation Mono", "Monospace", monospace;
            font-size: {font_px}px;
            line-height: 1.45;
        }}
        """

        try:
            self._editor_css_provider.load_from_data(css.encode("utf-8"))
        except TypeError:
            self._editor_css_provider.load_from_data(css)

        try:
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                self._editor_css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception:
            pass

        try:
            self.set_status(f"Editor zoom: {int(zoom * 100)}%")
        except Exception:
            pass

    def _apply_preview_zoom(self):
        zoom = getattr(self, "_preview_zoom", 1.0)

        try:
            self.webview.set_zoom_level(zoom)
        except Exception:
            pass

        try:
            self.set_status(f"Preview zoom: {int(zoom * 100)}%")
        except Exception:
            pass

    def _setup_line_navigation_controls(self):
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_editor_gutter_click)
        self.editor.add_controller(click)

    def _on_editor_gutter_click(self, gesture, n_press, x, y):
        return

    def _on_editor_cursor_position_changed(self, *_args):
        if getattr(self, "_editor_line_jump_blocked", False):
            return

        try:
            it = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            line_no = it.get_line() + 1

            if line_no == getattr(self, "_last_editor_line_jump", None):
                return

            self._last_editor_line_jump = line_no
            self._scroll_output_to_line(line_no)

        except Exception as exc:
            print("editor to output line sync failed:", exc)

    def _scroll_output_to_line(self, line_no):
        js = f"""
        (function () {{
            const line = document.querySelector('[data-cp-line="{int(line_no)}"]');
            if (!line) return;
            line.scrollIntoView({{block: "center", behavior: "instant"}});
            line.classList.add("cp-line-flash");
            setTimeout(() => line.classList.remove("cp-line-flash"), 700);
        }})();
        """
        try:
            self._eval_webview_js(js)
        except Exception:
            pass

    def _jump_editor_to_line(self, line_no):
        try:
            line = max(0, int(line_no) - 1)

            result = self.buffer.get_iter_at_line(line)

            if isinstance(result, tuple):
                ok, it = result
                if not ok:
                    return
            else:
                it = result

            self.buffer.place_cursor(it)
            self.editor.grab_focus()
            self.editor.scroll_to_iter(it, 0.15, True, 0.0, 0.35)

        except Exception as exc:
            print("line jump to editor failed:", exc)

    def _setup_format_controls(self):
        key = Gtk.EventControllerKey.new()
        key.connect("key-pressed", self._on_format_key_pressed)
        self.editor.add_controller(key)

    def _on_format_key_pressed(self, controller, keyval, keycode, state):
        try:
            is_ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
            is_shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        except Exception:
            return False

        if is_ctrl and is_shift and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self._format_current_line()
            return True

        return False

    def _format_current_line(self, *_args):
        try:
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            line_no = cursor.get_line()

            start = self.buffer.get_iter_at_line(line_no)
            if isinstance(start, tuple):
                _ok, start = start

            end = start.copy()
            if not end.ends_line():
                end.forward_to_line_end()

            original = self.buffer.get_text(start, end, False)
            formatted = self._format_calcpad_line(original)

            if formatted == original:
                return

            self.buffer.begin_user_action()
            self.buffer.delete(start, end)
            self.buffer.insert(start, formatted)
            self.buffer.end_user_action()

        except Exception as exc:
            print("format current line failed:", exc)

    def _start_with_empty_document(self):
        try:
            if getattr(self, "current_file", None):
                return

            self.buffer.set_text("")
            self.buffer.set_modified(False)
            self.current_file = None
        except Exception as e:
            print("empty startup failed:", e)

    def _build_editor(self):
        self.buffer = GtkSource.Buffer()
        self.buffer.set_highlight_syntax(False)
        lm = GtkSource.LanguageManager.get_default()
        lang = lm.get_language("calcpad") if self._calcpad_lang_ok else None
        if lang: self.buffer.set_language(lang)
        self.buffer.set_text(DEFAULT_SAMPLE); self.buffer.set_modified(False)
        self.buffer.connect("changed", self.on_text_changed)
        self.editor = GtkSource.View.new_with_buffer(self.buffer)
        self.editor.add_css_class("calcpad-editor")
        self.editor.set_show_line_numbers(True); self.editor.set_monospace(True)
        self.editor.set_auto_indent(True); self.editor.set_tab_width(2)
        self.editor.set_insert_spaces_instead_of_tabs(True)
        self.editor.set_highlight_current_line(True)
        self.editor.set_name("calcpad-editor")
        self.editor.set_monospace(True)
        try:
            self.editor.set_pixels_above_lines(1)
            self.editor.set_pixels_below_lines(3)
        except Exception:
            pass
        self.editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_margin_end(6)
        scroll.set_child(self.editor); return scroll

    def insert_at_cursor(self, text):
        text = text.replace("µ", "μ")
        self.buffer.insert_at_cursor(text)

        def refocus_editor():
            self.editor.grab_focus()
            return False

        GLib.idle_add(refocus_editor)

    def _get_buffer_text(self) -> str:
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, True)

    def _get_text_for_cli(self) -> str:
        return self._normalize(self._get_buffer_text())

    def _get_text(self) -> str:
        return self._get_text_for_cli()
