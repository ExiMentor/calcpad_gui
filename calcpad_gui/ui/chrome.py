"""ChromeActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.assets import find_logo
from calcpad_gui.bootstrap import GLib
from calcpad_gui.bootstrap import Gdk
from calcpad_gui.bootstrap import Gio
from calcpad_gui.bootstrap import Gtk
from calcpad_gui.config import save_settings
from calcpad_gui.data import QUICK_HOTKEYS

class ChromeActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

    def _apply_app_theme(self):
        dark = bool(self.settings.get("dark_preview", False))

        try:
            self.editor.set_highlight_current_line(not dark)
        except Exception:
            pass

        try:
            gtk_settings = Gtk.Settings.get_default()
            if gtk_settings:
                gtk_settings.set_property("gtk-application-prefer-dark-theme", dark)
        except Exception:
            pass

        try:
            if not hasattr(self, "_app_theme_css_provider"):
                self._app_theme_css_provider = Gtk.CssProvider()

            if dark:
                css = """
                #calcpad-editor,
                #calcpad-editor text,
                textview#calcpad-editor,
                textview#calcpad-editor text {
                    background-color: #1e1e1e;
                    color: #d8d8d8;
                    caret-color: #ffffff;
                }

                #calcpad-editor selection,
                #calcpad-editor text selection {
                    background-color: #355a8a;
                    color: #ffffff;
                }

                #calcpad-editor gutter,
                #calcpad-editor gutter text {
                    background-color: #252525;
                    color: #8a8a8a;
                }
                """
            else:
                css = """
                #calcpad-editor,
                #calcpad-editor text,
                textview#calcpad-editor,
                textview#calcpad-editor text {
                    background-color: @theme_base_color;
                    color: @theme_text_color;
                }

                #calcpad-editor gutter,
                #calcpad-editor gutter text {
                    background-color: @theme_base_color;
                    color: alpha(@theme_text_color, 0.55);
                }
                """

            try:
                self._app_theme_css_provider.load_from_data(css.encode("utf-8"))
            except TypeError:
                self._app_theme_css_provider.load_from_data(css)

            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                self._app_theme_css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception:
            pass

        try:
            if dark:
                self.add_css_class("dark")
            else:
                self.remove_css_class("dark")
        except Exception:
            pass

    def _build_headerbar(self):
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        try:
            logo_path = find_logo()
            if logo_path is not None:
                logo = Gtk.Image.new_from_file(str(logo_path))
                logo.set_pixel_size(30)
                logo.set_opacity(0.9)
                logo.set_margin_end(8)
                logo.set_tooltip_text("Calcpad GUI")
                header.pack_start(logo)
        except Exception:
            pass
        def mkbtn(icon, tip, cb):
            b = Gtk.Button.new_from_icon_name(icon)
            b.set_tooltip_text(tip); b.connect("clicked", cb); return b
        header.pack_start(mkbtn("document-new-symbolic","New Window (Ctrl+N)",self.on_new))
        header.pack_start(mkbtn("document-open-symbolic","Open (Ctrl+O)",self.on_open))
        self.recent_btn = Gtk.MenuButton(
            icon_name="document-open-recent-symbolic", tooltip_text="Open recent")
        self._refresh_recent_menu()
        header.pack_start(self.recent_btn)
        header.pack_start(mkbtn("document-save-symbolic","Save (Ctrl+S)",self.on_save))
        header.pack_start(mkbtn("document-save-as-symbolic","Save As (Ctrl+Shift+S)",self.on_save_as))
        header.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        header.pack_start(mkbtn("media-playback-start-symbolic","Calculate (F5)",self.on_run))

        format_btn = Gtk.Button(label="Format")
        format_btn.set_tooltip_text("Format current line (Ctrl+Shift+F)")
        format_btn.connect("clicked", self._format_current_line)
        header.pack_start(format_btn)

        export_btn = Gtk.MenuButton(icon_name="document-send-symbolic", tooltip_text="Export")
        menu = Gio.Menu()
        menu.append("Export HTML…","win.export_html")
        menu.append("Export PDF…","win.export_pdf")
        menu.append("Quick export Word + open", "win.export_docx")
        menu.append("Export Word as…", "win.export_docx_as")
        export_btn.set_menu_model(menu)
        header.pack_start(export_btn)
        for name,fmt in [("export_html","html"),("export_pdf","pdf"),("export_docx","docx")]:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda _a,_p,f=fmt: self._quick_export_docx() if f == "docx" else self._export(f))
            self.add_action(a)

        word_as = Gio.SimpleAction.new("export_docx_as", None)
        word_as.connect("activate", lambda *_: self._export("docx"))
        self.add_action(word_as)
        self.get_application().set_accels_for_action("win.export_docx", ["<Primary><Shift>e"])
        quick_word = Gtk.Button(label="Word Quick Export",
                                tooltip_text="Quick export Word + open (Ctrl+Shift+E)")
        quick_word.set_action_name("win.export_docx")
        header.pack_start(quick_word)

        self.auto_toggle = Gtk.ToggleButton(icon_name="view-refresh-symbolic", tooltip_text="Auto-refresh")
        self.auto_toggle.set_active(self.settings["auto_refresh"])
        self.auto_toggle.connect("toggled", self._on_toggle, "auto_refresh")
        header.pack_end(self.auto_toggle)
        self.dark_toggle = Gtk.ToggleButton(icon_name="weather-clear-night-symbolic", tooltip_text="Dark mode")
        self.dark_toggle.set_active(self.settings["dark_preview"])
        self.dark_toggle.connect("toggled", self._on_toggle, "dark_preview")
        self.dark_toggle.connect("toggled", lambda *_: self.on_run(None))
        header.pack_end(self.dark_toggle)
        self.comma_toggle = Gtk.ToggleButton(icon_name="accessories-calculator-symbolic", tooltip_text="Decimal: comma instead of dot")
        self.comma_toggle.set_active(self.settings.get("decimal_comma", False))
        self.comma_toggle.connect("toggled", self._on_toggle, "decimal_comma")
        self.comma_toggle.connect("toggled", lambda *_: self.on_run(None))
        header.pack_end(self.comma_toggle)

        self.decimals_spin = Gtk.SpinButton.new_with_range(0, 10, 1)
        self.decimals_spin.set_value(int(self.settings.get("decimal_places", 3)))
        self.decimals_spin.set_tooltip_text("Number of decimal places")
        self.decimals_spin.set_width_chars(2)
        self.decimals_spin.connect("value-changed", self._on_decimal_places_changed)
        header.pack_end(self.decimals_spin)

        self.keyboard_toggle = Gtk.ToggleButton(icon_name="input-keyboard-symbolic", tooltip_text="Show/hide keyboard")
        self.keyboard_toggle.set_active(bool(self.settings.get("keyboard_visible", True)))
        self.keyboard_toggle.connect("toggled", self._on_keyboard_visible_toggled)
        header.pack_end(self.keyboard_toggle)

    def _on_toggle(self, btn, key):
        self.settings[key] = btn.get_active()
        save_settings(self.settings)

        if key == "dark_preview":
            self._apply_app_theme()

    def _on_keyboard_visible_toggled(self, btn):
        visible = bool(btn.get_active())
        self.settings["keyboard_visible"] = visible
        save_settings(self.settings)
        revealer = getattr(self, "_keyboard_revealer", None)
        if revealer is not None:
            revealer.set_reveal_child(visible)

    def _on_decimal_places_changed(self, spin):
        self.settings["decimal_places"] = int(spin.get_value())
        save_settings(self.settings)
        self.on_run(None)

    def _refresh_recent_menu(self):
        menu = Gio.Menu()
        recent = self.settings.get("recent", [])
        if not recent:
            menu.append("(no recent files)", "win.noop")
            if not self.lookup_action("noop"):
                a = Gio.SimpleAction.new("noop", None); a.set_enabled(False); self.add_action(a)
        else:
            for idx, path in enumerate(recent[:10]):
                action_name = f"open_recent_{idx}"
                menu.append(GLib.path_get_basename(path), f"win.{action_name}")
                if self.lookup_action(action_name):
                    self.remove_action(action_name)
                act = Gio.SimpleAction.new(action_name, None)
                act.connect("activate", lambda _a,_p,p=path: self._open_path(p))
                self.add_action(act)
            menu.append("Clear list", "win.clear_recent")
            if not self.lookup_action("clear_recent"):
                a = Gio.SimpleAction.new("clear_recent", None)
                a.connect("activate", lambda *_: self._clear_recent())
                self.add_action(a)
        self.recent_btn.set_menu_model(menu)

    def _clear_recent(self):
        self.settings["recent"] = []; save_settings(self.settings); self._refresh_recent_menu()

    def _build_layout(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)
        inner = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        inner.set_position(720)
        inner.set_vexpand(True)
        inner.set_start_child(self._build_editor())
        inner.set_end_child(self._build_preview())
        root.append(self._build_search_bar())
        root.append(inner)

        self._keyboard_revealer = Gtk.Revealer()
        self._keyboard_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._keyboard_revealer.set_reveal_child(bool(self.settings.get("keyboard_visible", True)))
        self._keyboard_revealer.set_child(self._build_keyboard())
        root.append(self._keyboard_revealer)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")
        root.append(self.status)
        if self._cli_cmd:
            self.set_status(f"Ready. CLI: {self._cli_hint}")
        else:
            self.set_status("Calcpad.Cli not found - see preview pane.")

    def _install_shortcuts(self):
        ctl = Gtk.ShortcutController()
        ctl.set_scope(Gtk.ShortcutScope.GLOBAL); self.add_controller(ctl)
        def add(combo, fn):
            trig = Gtk.ShortcutTrigger.parse_string(combo)
            if trig is None: return
            def cb(_w,_a,_u=None,_fn=fn): _fn(None); return True
            ctl.add_shortcut(Gtk.Shortcut.new(trig, Gtk.CallbackAction.new(cb)))
        add("<Control>n", self.on_new); add("<Control>o", self.on_open); add("<Control>f", self._show_search_bar)
        add("<Control>s", self.on_save); add("<Control><Shift>s", self.on_save_as)
        add("F5", self.on_run); add("<Control>g", lambda _: self.symbol_search.grab_focus())
        for key,ch in QUICK_HOTKEYS.items():
            add(f"<Control><Alt>{key}", lambda _b,c=ch: self.insert_at_cursor(c))

    def set_status(self, msg): self.status.set_text(msg)

    def _initial_run(self): self.on_run(None); return False
