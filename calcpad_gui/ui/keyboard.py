"""KeyboardActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import Gtk
from calcpad_gui.config import save_settings
from calcpad_gui.data import GREEK_TABLE
from calcpad_gui.data import SYMBOL_TABLE

class KeyboardActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _build_keyboard(self):
        rows = [
            [("7", "7"), ("8", "8"), ("9", "9"), ("×", "*"),
             ("\\", "\\"), ("x²", "^2"), ("≡", "="),
             ("∧", "and"), ("e", "e"), ("AC", "__clear__", "warn"),
             ("sin", "sin("), ("csc", "csc("), ("min", "min("),
             ("max", "max("), ("re", "re("), ("Root", "root("),
             ("Root2", "root2("), ("Find", "Find("),
             ("α", "α"), ("β", "β"),
             ("γ", "γ"), ("δ", "δ"),
             ("ε", "ε"), ("ζ", "ζ"),
             ("η", "η"), ("θ", "θ")],
            [("4", "4"), ("5", "5"), ("6", "6"), ("/", "/"),
             ("%", "%"), ("x³", "^3"), ("≠", "≠"),
             ("∨", "or"), ("π", "π"), ("←", "__bksp__"),
             ("cos", "cos("), ("sec", "sec("), ("round", "round("),
             ("trunc", "trunc("), ("im", "im("),
             ("Plot", "$Plot{"), ("Map", "$Map{"), ("Sum", "∑"),
             ("ι", "ι"), ("κ", "κ"),
             ("λ", "λ"), ("μ", "μ"),
             ("ν", "ν"), ("ξ", "ξ"),
             ("ο", "ο"), ("π", "π")],
            [("1", "1"), ("2", "2"), ("3", "3"), ("+", "+"),
             ("!", "!"), ("xʸ", "^"), ("≤", "≤"),
             ("xor", "xor"), ("i", "i"), ("↵", "\n"),
             ("tan", "tan("), ("cot", "cot("), ("floor", "floor("),
             ("ceiling", "ceiling("), ("phase", "phase("),
             ("Sup", "sup("), ("Inf", "inf("), ("Product", "∏"),
             ("ρ", "ρ"), ("ς", "ς"),
             ("σ", "σ"), ("τ", "τ"),
             ("υ", "υ"), ("φ", "φ"),
             ("χ", "χ"), ("ψ", "ψ")],
            [("0", "0"), (".", "."), ("=", "="), ("−", "-"),
             ("10ˣ", "10^"), ("eˣ", "exp("), ("≥", "≥"),
             ("∠", "∠"), ("(", "("), (")", ")"),
             ("atan2", "atan2("), ("random", "random("), ("abs", "abs("),
             ("sign", "sign("), ("conj", "conj("),
             ("Area", "area("), ("Slope", "slope("), ("Repeat", "repeat("),
             ("ω", "ω"), ("ϑ", "ϑ"),
             ("°", "°"), ("′", "′"),
             ("″", "″"), ("ø", "ø"),
             ("‰", "‰"), ("aA", "__case__")],
        ]
        greek_upper_map = {
            "α": "Α", "β": "Β", "γ": "Γ", "δ": "Δ",
            "ε": "Ε", "ζ": "Ζ", "η": "Η", "θ": "Θ",
            "ι": "Ι", "κ": "Κ", "λ": "Λ", "μ": "Μ",
            "ν": "Ν", "ξ": "Ξ", "ο": "Ο", "π": "Π",
            "ρ": "Ρ", "ς": "Σ", "σ": "Σ", "τ": "Τ",
            "υ": "Υ", "φ": "Φ", "χ": "Χ", "ψ": "Ψ",
            "ω": "Ω", "ϑ": "Θ",
        }
        self._greek_upper = False
        self._greek_buttons = []

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(4); box.set_margin_end(4)
        box.set_margin_top(2); box.set_margin_bottom(4)
        box.add_css_class("calcpad-keyboard")
        box.set_halign(Gtk.Align.CENTER)
        box.set_hexpand(False)
        box.set_halign(Gtk.Align.CENTER)
        box.set_hexpand(False)

        stack = Gtk.Stack()
        stack.set_vexpand(False)
        stack.set_hexpand(False)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(stack)
        switcher.set_halign(Gtk.Align.CENTER)
        box.append(switcher)

        def build_keyboard_page(page_rows, greek_page=False):
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            page.set_halign(Gtk.Align.CENTER)
            page.set_hexpand(False)
            page.set_halign(Gtk.Align.CENTER)
            page.set_hexpand(False)

            for row in page_rows:
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                  spacing=4, homogeneous=True)
                row_box.set_halign(Gtk.Align.CENTER)
                row_box.set_hexpand(False)

                for item in row:
                    label, action = item[0], item[1]
                    cls = item[2] if len(item) > 2 else None

                    btn = Gtk.Button(label=label)
                    btn.set_can_focus(False)
                    btn.add_css_class("kbd-btn")
                    btn.set_hexpand(False)
                    btn.set_halign(Gtk.Align.CENTER)
                    btn.set_size_request(72, 32)
                    btn.set_size_request(72, 32)
                    btn._insert_text = action
                    btn._favorite_label = label
                    btn._favorite_action = action

                    if greek_page and label in greek_upper_map:
                        btn._greek_lower = label
                        btn._greek_upper = greek_upper_map[label]
                        self._greek_buttons.append(btn)

                    if cls:
                        btn.add_css_class(cls)

                    if action == "__clear__":
                        btn.set_tooltip_text("Clear editor")
                        btn.connect("clicked", lambda _b: self._kbd_clear())
                    elif action == "__bksp__":
                        btn.set_tooltip_text("Backspace")
                        btn.connect("clicked", lambda _b: self._kbd_backspace())
                    elif action == "__case__":
                        btn.set_tooltip_text("Toggle Greek upper/lower case")
                        btn.connect("clicked", lambda _b: self._kbd_toggle_greek_case())
                    else:
                        btn.connect("clicked",
                                    lambda _b: self.insert_at_cursor(getattr(_b, "_insert_text", "")))

                    if action and action not in ("__clear__", "__bksp__", "__case__"):
                        self._attach_keyboard_favorite_toggle(btn)

                    row_box.append(btn)

                page.append(row_box)

            return page

        basic_rows = [row[:10] for row in rows]
        function_rows = [row[10:18] for row in rows]
        greek_rows = [row[18:] for row in rows]

        self._keyboard_favorites_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._keyboard_favorites_page.set_halign(Gtk.Align.CENTER)
        self._keyboard_favorites_page.set_hexpand(False)

        def refresh_favorites_page():
            child = self._keyboard_favorites_page.get_first_child()
            while child is not None:
                nxt = child.get_next_sibling()
                self._keyboard_favorites_page.remove(child)
                child = nxt

            fav_rows = self._get_keyboard_favorite_rows()
            if fav_rows:
                self._keyboard_favorites_page.append(build_keyboard_page(fav_rows))
            else:
                label = Gtk.Label(label="Right-click a button to add it to Favorites.")
                label.set_margin_top(12)
                label.set_margin_bottom(12)
                self._keyboard_favorites_page.append(label)

        self._refresh_keyboard_favorites_page = refresh_favorites_page
        refresh_favorites_page()

        stack.add_titled(self._keyboard_favorites_page, "favorites", "Favorites")
        stack.add_titled(build_keyboard_page(basic_rows), "basic", "Basic")
        stack.add_titled(build_keyboard_page(function_rows), "functions", "Functions")
        stack.add_titled(build_keyboard_page(greek_rows, greek_page=True), "greek", "Greek")

        box.append(stack)
        return box

    def _favorite_key(self, label, action):
        return f"{label}\t{action}"

    def _get_keyboard_favorites(self):
        favs = self.settings.setdefault("keyboard_favorites", [])
        clean = []
        seen = set()

        for item in favs:
            if not isinstance(item, dict):
                continue

            label = str(item.get("label", ""))
            action = str(item.get("action", ""))

            if not label or not action:
                continue

            key = self._favorite_key(label, action)
            if key in seen:
                continue

            seen.add(key)
            clean.append({"label": label, "action": action})

        if clean != favs:
            self.settings["keyboard_favorites"] = clean
            save_settings(self.settings)

        return clean

    def _get_keyboard_favorite_rows(self):
        favs = self._get_keyboard_favorites()
        buttons = [(item["label"], item["action"]) for item in favs]
        return [buttons[i:i + 10] for i in range(0, len(buttons), 10)]

    def _attach_keyboard_favorite_toggle(self, btn):
        try:
            click = Gtk.GestureClick.new()
            click.set_button(3)
            click.connect(
                "pressed",
                lambda _g, _n, _x, _y, b=btn: self._toggle_keyboard_favorite(b)
            )
            btn.add_controller(click)

            tip = btn.get_tooltip_text() or ""
            extra = "Right-click: add/remove favorite"
            btn.set_tooltip_text((tip + "\n" + extra).strip())
        except Exception:
            pass

    def _toggle_keyboard_favorite(self, btn):
        label = getattr(btn, "_favorite_label", None) or btn.get_label()
        action = getattr(btn, "_favorite_action", None) or getattr(btn, "_insert_text", "")

        if not label or not action:
            return

        favs = self._get_keyboard_favorites()
        key = self._favorite_key(label, action)

        existing = None
        for i, item in enumerate(favs):
            if self._favorite_key(item["label"], item["action"]) == key:
                existing = i
                break

        if existing is None:
            favs.append({"label": label, "action": action})
            self.set_status(f"Favorite added: {label}")
        else:
            del favs[existing]
            self.set_status(f"Favorite removed: {label}")

        self.settings["keyboard_favorites"] = favs
        save_settings(self.settings)

        refresh = getattr(self, "_refresh_keyboard_favorites_page", None)
        if refresh:
            refresh()

    def _kbd_toggle_greek_case(self):
        self._greek_upper = not getattr(self, "_greek_upper", False)

        for btn in getattr(self, "_greek_buttons", []):
            lower = getattr(btn, "_greek_lower", None)
            upper = getattr(btn, "_greek_upper", None)

            if not lower or not upper:
                continue

            text = upper if self._greek_upper else lower
            btn.set_label(text)
            btn._insert_text = text
            btn._favorite_label = text
            btn._favorite_action = text

    def _kbd_clear(self):
        self.buffer.set_text("")

    def _kbd_backspace(self):
        ins = self.buffer.get_insert()
        it = self.buffer.get_iter_at_mark(ins)
        if not it.is_start():
            prev = it.copy()
            prev.backward_char()
            self.buffer.delete(prev, it)

    def _build_quick_toolbar(self):
        return Gtk.Box()

    def _build_symbol_sidebar(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_start(6); outer.set_margin_end(6); outer.set_margin_top(6)
        self.symbol_search = Gtk.SearchEntry()
        self.symbol_search.set_placeholder_text("Search symbol (Ctrl+G)")
        self.symbol_search.connect("search-changed", self._on_symbol_search)
        outer.append(self.symbol_search)
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        self.symbol_grid = Gtk.FlowBox()
        self.symbol_grid.set_max_children_per_line(5)
        self.symbol_grid.set_min_children_per_line(4)
        self.symbol_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.symbol_grid.set_homogeneous(True)
        scroll.set_child(self.symbol_grid); outer.append(scroll)
        self._populate_symbols(""); return outer

    def _populate_symbols(self, filt):
        child = self.symbol_grid.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.symbol_grid.remove(child); child = nxt
        f = filt.lower().strip()
        for ch,name,trig in GREEK_TABLE + SYMBOL_TABLE:
            if f and (f not in name.lower() and f not in ch and f not in trig): continue
            btn = Gtk.Button(label=ch)
            btn.add_css_class("symbol-btn"); btn.add_css_class("flat")
            btn.set_can_focus(False)
            tip = name + (f"   {trig}" if trig else "")
            btn.set_tooltip_text(tip)
            btn.connect("clicked", lambda _b,c=ch: self.insert_at_cursor(c))
            self.symbol_grid.append(btn)

    def _on_symbol_search(self, entry): self._populate_symbols(entry.get_text())
