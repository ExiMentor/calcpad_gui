"""AutocompleteActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import GLib
from calcpad_gui.bootstrap import Gdk
from calcpad_gui.bootstrap import Gtk
import re

class AutocompleteActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _setup_autocomplete_controls(self):
        self._autocomplete_items = [
            "sin(", "cos(", "tan(", "asin(", "acos(", "atan(", "atan2(",
            "sinh(", "cosh(", "tanh(", "sqrt(", "root(", "root2(",
            "ln(", "log(", "log_2(", "exp(", "abs(",
            "min(", "max(", "round(", "trunc(", "floor(", "ceiling(",
            "random(", "sign(", "conj(", "re(", "im(", "phase(",
            "area(", "slope(", "sup(", "inf(",

            "#if", "#else", "#end if", "#for", "#repeat", "#loop",
            "#break", "#include", "#hide", "#show", "#pre", "#post",
            "#round", "#format",

            "mm", "cm", "m", "km",
            "s", "ms", "min", "h",
            "V", "mV", "kV",
            "A", "mA", "µA", "μA",
            "Ω", "kΩ", "MΩ",
            "W", "mW", "kW",
            "F", "mF", "µF", "μF", "nF", "pF",
            "H", "mH", "µH", "μH", "nH",
            "Hz", "kHz", "MHz",
            "Pa", "kPa", "MPa",
        ]

        self._autocomplete_prefix = ""
        self._autocomplete_suggestions = []
        self._autocomplete_index = 0
        self._autocomplete_update_id = 0
        self._autocomplete_inserting = False

        self._autocomplete_popover = Gtk.Popover()
        self._autocomplete_popover.set_parent(self.editor)
        # Keep keyboard focus in the editor so Tab accepts the selection.
        self._autocomplete_popover.set_autohide(False)
        self._autocomplete_popover.set_can_focus(False)

        self._autocomplete_list = Gtk.ListBox()
        self._autocomplete_list.set_can_focus(False)
        self._autocomplete_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._autocomplete_list.connect("row-activated", self._on_autocomplete_row_activated)
        self._autocomplete_popover.set_child(self._autocomplete_list)

        key = Gtk.EventControllerKey.new()
        try:
            key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        except Exception:
            pass
        key.connect("key-pressed", self._on_autocomplete_key_pressed)
        self.editor.add_controller(key)

        self.buffer.connect("changed", self._schedule_autocomplete_update)
        self.editor.connect(
            "notify::has-focus",
            lambda editor, _pspec: (
                self._hide_autocomplete_popover() if not editor.has_focus() else None
            ),
        )

    def _schedule_autocomplete_update(self, *_args):
        if getattr(self, "_autocomplete_inserting", False):
            return
        if self._autocomplete_update_id:
            GLib.source_remove(self._autocomplete_update_id)
            self._autocomplete_update_id = 0
        self._autocomplete_update_id = GLib.timeout_add(120, self._update_autocomplete)

    def _on_autocomplete_key_pressed(self, controller, keyval, keycode, state):
        if not getattr(self, "_autocomplete_popover", None):
            return False

        if not self._autocomplete_popover.get_visible():
            return False

        if keyval == Gdk.KEY_Escape:
            self._hide_autocomplete_popover()
            return True

        if keyval == Gdk.KEY_Down:
            self._move_autocomplete_selection(1)
            return True

        if keyval == Gdk.KEY_Up:
            self._move_autocomplete_selection(-1)
            return True

        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            self._insert_autocomplete_selection()
            return True

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self._hide_autocomplete_popover()
            return False

        return False

    def _hide_autocomplete_popover(self):
        if self._autocomplete_update_id:
            GLib.source_remove(self._autocomplete_update_id)
            self._autocomplete_update_id = 0
        self._autocomplete_prefix = ""
        self._autocomplete_suggestions = []
        self._autocomplete_index = 0
        if self._autocomplete_popover.get_visible():
            self._autocomplete_popover.popdown()

    def _update_autocomplete(self):
        self._autocomplete_update_id = 0

        try:
            if not self.editor.has_focus():
                self._hide_autocomplete_popover()
                return False
        except Exception:
            pass

        prefix = self._get_autocomplete_prefix()

        if len(prefix) < 2:
            self._hide_autocomplete_popover()
            return False

        suggestions = self._get_autocomplete_suggestions(prefix)

        if not suggestions:
            self._hide_autocomplete_popover()
            return False

        self._autocomplete_prefix = prefix
        self._autocomplete_suggestions = suggestions[:12]
        self._autocomplete_index = 0

        self._rebuild_autocomplete_list()
        self._position_autocomplete_popover()
        self._autocomplete_popover.popup()

        return False

    def _position_autocomplete_popover(self):
        try:
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            rect = self.editor.get_iter_location(cursor)

            try:
                x, y = self.editor.buffer_to_window_coords(
                    Gtk.TextWindowType.TEXT,
                    rect.x,
                    rect.y + rect.height
                )
                rect.x = x
                rect.y = y
            except Exception:
                pass

            self._autocomplete_popover.set_pointing_to(rect)
        except Exception:
            pass

    def _get_autocomplete_prefix(self):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_start = cursor.copy()
        line_start.set_line_offset(0)

        line_text = self.buffer.get_text(line_start, cursor, False)
        stripped = line_text.lstrip()

        if stripped.startswith(("'", '"', "“", "‘")):
            return ""

        quote_positions = [
            pos for pos in (
                line_text.find("'"),
                line_text.find('"'),
                line_text.find("“"),
                line_text.find("‘"),
            )
            if pos >= 0
        ]

        if quote_positions:
            return ""

        match = re.search(
            r"([#A-Za-z_Α-Ωα-ωµμΩ][#A-Za-z0-9_Α-Ωα-ωµμΩ]*)$",
            line_text
        )

        return match.group(1) if match else ""

    def _get_autocomplete_suggestions(self, prefix):
        prefix_l = prefix.lower()

        items = []
        items.extend(self._autocomplete_items)
        items.extend(self._get_document_symbols_above_cursor())

        seen = set()
        unique = []

        for item in items:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        # An existing complete name must not reopen completion just because
        # a longer name shares its prefix (I_spark / I_spark_permitted).
        if any(item.lower() == prefix_l for item in unique):
            return []

        starts = [item for item in unique if item.lower().startswith(prefix_l)]
        contains = [
            item for item in unique
            if prefix_l in item.lower() and not item.lower().startswith(prefix_l)
        ]

        return sorted(starts, key=str.lower) + sorted(contains, key=str.lower)

    def _get_document_symbols_above_cursor(self):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        start = self.buffer.get_start_iter()
        text = self.buffer.get_text(start, cursor, False)

        symbols = set()

        for match in re.finditer(
            r"(?m)^\s*([A-Za-z_Α-Ωα-ωµμ][A-Za-z0-9_Α-Ωα-ωµμ]*)\s*=",
            text
        ):
            symbols.add(match.group(1))

        for match in re.finditer(
            r"(?m)^\s*([A-Za-z_Α-Ωα-ωµμ][A-Za-z0-9_Α-Ωα-ωµμ]*)\s*\(",
            text
        ):
            symbols.add(match.group(1) + "(")

        return sorted(symbols, key=str.lower)

    def _rebuild_autocomplete_list(self):
        child = self._autocomplete_list.get_first_child()

        while child is not None:
            nxt = child.get_next_sibling()
            self._autocomplete_list.remove(child)
            child = nxt

        for item in self._autocomplete_suggestions:
            label = Gtk.Label(label=item)
            label.set_xalign(0)
            label.set_margin_start(8)
            label.set_margin_end(8)
            label.set_margin_top(4)
            label.set_margin_bottom(4)

            row = Gtk.ListBoxRow()
            row.set_can_focus(False)
            row.set_child(label)
            self._autocomplete_list.append(row)

        row = self._autocomplete_list.get_row_at_index(0)
        if row:
            self._autocomplete_list.select_row(row)

    def _move_autocomplete_selection(self, delta):
        if not self._autocomplete_suggestions:
            return

        self._autocomplete_index = (
            self._autocomplete_index + delta
        ) % len(self._autocomplete_suggestions)

        row = self._autocomplete_list.get_row_at_index(self._autocomplete_index)
        if row:
            self._autocomplete_list.select_row(row)

    def _on_autocomplete_row_activated(self, _listbox, row):
        self._autocomplete_index = row.get_index()
        self._insert_autocomplete_selection()

    def _insert_autocomplete_selection(self):
        if not self._autocomplete_suggestions:
            return
        suggestion = self._autocomplete_suggestions[self._autocomplete_index]
        prefix = self._autocomplete_prefix
        # Reject a stale popup after the cursor or text has changed.
        if not prefix or self._get_autocomplete_prefix() != prefix:
            self._hide_autocomplete_popover()
            return
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        start = cursor.copy()
        if not start.backward_chars(len(prefix)):
            return
        self._hide_autocomplete_popover()
        # Both delete() and insert() emit changed; suppress the whole transaction.
        self._autocomplete_inserting = True
        try:
            self.buffer.begin_user_action()
            try:
                self.buffer.delete(start, cursor)
                self.buffer.insert(start, suggestion)
            finally:
                self.buffer.end_user_action()
        finally:
            self._autocomplete_inserting = False
        self.editor.grab_focus()
