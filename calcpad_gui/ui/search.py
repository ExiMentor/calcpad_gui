"""SearchActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import Gdk
from calcpad_gui.bootstrap import Gtk

class SearchActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _build_search_bar(self):
        self.search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_bar.set_margin_start(8)
        self.search_bar.set_margin_end(8)
        self.search_bar.set_margin_top(6)
        self.search_bar.set_margin_bottom(4)
        self.search_bar.set_visible(False)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Find")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", lambda *_: self._find_next())

        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace")
        self.replace_entry.set_hexpand(True)

        prev_btn = Gtk.Button(label="Prev")
        prev_btn.connect("clicked", lambda *_: self._find_previous())

        next_btn = Gtk.Button(label="Next")
        next_btn.connect("clicked", lambda *_: self._find_next())

        replace_btn = Gtk.Button(label="Replace")
        replace_btn.connect("clicked", lambda *_: self._replace_current())

        replace_all_btn = Gtk.Button(label="Replace all")
        replace_all_btn.connect("clicked", lambda *_: self._replace_all())

        close_btn = Gtk.Button(label="×")
        close_btn.set_tooltip_text("Close search")
        close_btn.connect("clicked", lambda *_: self._hide_search_bar())

        self.search_bar.append(Gtk.Label(label="Find:"))
        self.search_bar.append(self.search_entry)
        self.search_bar.append(Gtk.Label(label="Replace:"))
        self.search_bar.append(self.replace_entry)
        self.search_bar.append(prev_btn)
        self.search_bar.append(next_btn)
        self.search_bar.append(replace_btn)
        self.search_bar.append(replace_all_btn)
        self.search_bar.append(close_btn)

        key = Gtk.EventControllerKey.new()
        key.connect("key-pressed", self._on_search_key_pressed)
        self.search_bar.add_controller(key)

        return self.search_bar

    def _show_search_bar(self, *_args):
        try:
            selected = self._get_selected_text()
            if selected:
                self.search_entry.set_text(selected)
        except Exception:
            pass

        self.search_bar.set_visible(True)
        self.search_entry.grab_focus()
        self.search_entry.select_region(0, -1)

    def _hide_search_bar(self):
        self.search_bar.set_visible(False)
        self.editor.grab_focus()

    def _on_search_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self._hide_search_bar()
            return True

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            try:
                if state & Gdk.ModifierType.SHIFT_MASK:
                    self._find_previous()
                else:
                    self._find_next()
            except Exception:
                self._find_next()
            return True

        return False

    def _get_selected_text(self):
        try:
            bounds = self.buffer.get_selection_bounds()
            if not bounds:
                return ""
            start, end = bounds
            return self.buffer.get_text(start, end, False)
        except Exception:
            return ""

    def _get_insert_iter(self):
        return self.buffer.get_iter_at_mark(self.buffer.get_insert())

    def _set_search_status(self, msg):
        try:
            self.set_status(msg)
        except Exception:
            pass

    def _find_next(self):
        needle = self.search_entry.get_text()
        if not needle:
            return False

        insert = self._get_insert_iter()
        start = insert.copy()

        if not start.is_end():
            start.forward_char()

        result = start.forward_search(
            needle,
            Gtk.TextSearchFlags.CASE_INSENSITIVE,
            None
        )

        if not result:
            start = self.buffer.get_start_iter()
            result = start.forward_search(
                needle,
                Gtk.TextSearchFlags.CASE_INSENSITIVE,
                None
            )

        if not result:
            self._set_search_status(f"No match: {needle}")
            return False

        match_start, match_end = result
        self.buffer.select_range(match_start, match_end)
        self.editor.scroll_to_iter(match_start, 0.15, True, 0.0, 0.35)
        self.editor.grab_focus()
        self._set_search_status(f"Found: {needle}")
        return True

    def _find_previous(self):
        needle = self.search_entry.get_text()
        if not needle:
            return False

        insert = self._get_insert_iter()
        start = insert.copy()

        result = start.backward_search(
            needle,
            Gtk.TextSearchFlags.CASE_INSENSITIVE,
            None
        )

        if not result:
            start = self.buffer.get_end_iter()
            result = start.backward_search(
                needle,
                Gtk.TextSearchFlags.CASE_INSENSITIVE,
                None
            )

        if not result:
            self._set_search_status(f"No match: {needle}")
            return False

        match_start, match_end = result
        self.buffer.select_range(match_start, match_end)
        self.editor.scroll_to_iter(match_start, 0.15, True, 0.0, 0.35)
        self.editor.grab_focus()
        self._set_search_status(f"Found: {needle}")
        return True

    def _replace_current(self):
        needle = self.search_entry.get_text()
        replacement = self.replace_entry.get_text()

        if not needle:
            return

        bounds = self.buffer.get_selection_bounds()

        if not bounds:
            if not self._find_next():
                return
            bounds = self.buffer.get_selection_bounds()

        if not bounds:
            return

        start, end = bounds
        selected = self.buffer.get_text(start, end, False)

        if selected.lower() != needle.lower():
            if not self._find_next():
                return
            bounds = self.buffer.get_selection_bounds()
            if not bounds:
                return
            start, end = bounds

        self.buffer.begin_user_action()
        self.buffer.delete(start, end)
        self.buffer.insert(start, replacement)
        self.buffer.end_user_action()

        self._set_search_status("Replaced")
        self._find_next()

    def _replace_all(self):
        needle = self.search_entry.get_text()
        replacement = self.replace_entry.get_text()

        if not needle:
            return

        start = self.buffer.get_start_iter()
        count = 0

        self.buffer.begin_user_action()

        try:
            while True:
                result = start.forward_search(
                    needle,
                    Gtk.TextSearchFlags.CASE_INSENSITIVE,
                    None
                )

                if not result:
                    break

                match_start, match_end = result
                self.buffer.delete(match_start, match_end)
                self.buffer.insert(match_start, replacement)

                start = match_start.copy()
                count += 1
        finally:
            self.buffer.end_user_action()

        self._set_search_status(f"Replaced {count} occurrence(s)")
