#!/usr/bin/env python3
"""
CalcpadCE Linux GUI v4 (GTK 4.10+ only)
Repo: https://github.com/imartincei/CalcpadCE
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile, textwrap, threading
from pathlib import Path
import gi

_REQUIRED = [("Gtk","4.0"), ("GtkSource","5"), ("WebKit","6.0")]
for ns,ver in _REQUIRED:
    try: gi.require_version(ns, ver)
    except ValueError as e:
        sys.exit(textwrap.dedent(f"""\
            ERROR: Required GI namespace {ns} {ver} not available.
            Install on Linux Mint 22 / Ubuntu 24.04 / Debian 13:
              sudo apt install python3-gi gir1.2-gtk-4.0 \\
                               gir1.2-gtksource-5 gir1.2-webkit-6.0
            Details: {e}
            """))

from gi.repository import Gtk, GtkSource, WebKit, Gio, GLib, Gdk  # noqa

_MIN_GTK = (4, 10)
_have = (Gtk.get_major_version(), Gtk.get_minor_version())
if _have < _MIN_GTK:
    sys.exit(f"ERROR: GTK {_MIN_GTK[0]}.{_MIN_GTK[1]}+ required, found "
             f"{_have[0]}.{_have[1]}. Please upgrade your distribution.")

APP_ID    = "org.community.calcpadce.linuxgui"
APP_TITLE = "CalcpadCE"
CFG_DIR   = Path(GLib.get_user_config_dir()) / "calcpad-gui"
CFG_FILE  = CFG_DIR / "settings.json"
LANG_DIR  = Path(GLib.get_user_data_dir()) / "gtksourceview-5" / "language-specs"
LANG_FILE = LANG_DIR / "calcpad.lang"
CFG_DIR.mkdir(parents=True, exist_ok=True)
LANG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "recent": [], "dark_preview": False, "auto_refresh": True,
    "last_dir": str(Path.home()), "schema": 1,
    "decimal_comma": False,
}

DEFAULT_SAMPLE = """' CalcpadCE Demo
' Electrical power across a resistor
U = 230 V
R = 47 Ω
I = U / R
P = U * I

' Using micro prefix:
C = 4.7 μF
τ = R * C
"""

GREEK_TABLE = [
    ("α","alpha","`a"),("β","beta","`b"),("χ","chi","`c"),
    ("δ","delta","`d"),("ε","epsilon","`e"),("φ","phi","`f"),
    ("γ","gamma","`g"),("η","eta","`h"),("ι","iota","`i"),
    ("κ","kappa","`k"),("λ","lambda","`l"),("μ","mu","`m"),
    ("ν","nu","`n"),("ο","omicron","`o"),("π","pi","`p"),
    ("θ","theta","`q"),("ρ","rho","`r"),("σ","sigma","`s"),
    ("τ","tau","`t"),("υ","upsilon","`u"),("ω","omega","`w"),
    ("ξ","xi","`x"),("ψ","psi","`y"),("ζ","zeta","`z"),
    ("Α","Alpha","`A"),("Β","Beta","`B"),("Γ","Gamma","`G"),
    ("Δ","Delta","`D"),("Ε","Epsilon","`E"),("Ζ","Zeta","`Z"),
    ("Η","Eta","`H"),("Θ","Theta","`Q"),("Κ","Kappa","`K"),
    ("Λ","Lambda","`L"),("Μ","Mu","`M"),("Ν","Nu","`N"),
    ("Ξ","Xi","`X"),("Π","Pi","`P"),("Ρ","Rho","`R"),
    ("Σ","Sigma","`S"),("Τ","Tau","`T"),("Υ","Upsilon","`U"),
    ("Φ","Phi","`F"),("Ψ","Psi","`Y"),("Ω","Omega","`W"),
]
SYMBOL_TABLE = [
    ("°","degree","`@"),("′","prime","`'"),
    ("″","double prime",'`\"'),("±","plus-minus",""),
    ("·","middle dot",""),("×","times",""),
    ("÷","divide",""),("≤","less or eq","<="),
    ("≥","greater or eq",">="),("≠","not equal","!="),
    ("≈","approx",""),("∞","infinity",""),
    ("√","sqrt",""),("∑","sum",""),
    ("∫","integral",""),("∂","partial",""),
    ("²","squared",""),("³","cubed",""),
]
QUICK_TOOLBAR = ["Ω","μ","π","°","²","³",
                 "±","·","≤","≥","≠","√",
                 "∑","∫","∞"]
QUICK_HOTKEYS = {"o":"Ω","m":"μ","p":"π","a":"α",
                 "b":"β","d":"δ","t":"τ","l":"λ",
                 "s":"σ","g":"γ"}

CALCPAD_LANG = r"""<?xml version="1.0" encoding="UTF-8"?>
<language id="calcpad" name="Calcpad" version="2.0" _section="Scientific">
  <metadata>
    <property name="globs">*.cpd;*.cpdz</property>
    <property name="line-comment-start">'</property>
  </metadata>
  <styles>
    <style id="comment"   name="Comment"   map-to="def:comment"/>
    <style id="string"    name="String"    map-to="def:string"/>
    <style id="directive" name="Directive" map-to="def:preprocessor"/>
    <style id="number"    name="Number"    map-to="def:decimal"/>
    <style id="operator"  name="Operator"  map-to="def:operator"/>
    <style id="greek"     name="Greek"     map-to="def:identifier"/>
  </styles>
  <definitions>
    <context id="line-comment" style-ref="comment" end-at-line-end="true">
      <start>'</start>
    </context>
    <context id="string-double" style-ref="string" end-at-line-end="true">
      <start>"</start>
      <end>"</end>
    </context>
    <context id="directive" style-ref="directive">
      <match>#[A-Za-z_]+(\s+[a-zA-Z_]+)?</match>
    </context>
    <context id="number" style-ref="number">
      <match>\b[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?\b</match>
    </context>
    <context id="operator" style-ref="operator" extend-parent="false">
      <match>[+\-*/^=&lt;&gt;!&amp;|%]</match>
    </context>
    <context id="greek-backtick" style-ref="greek">
      <match>`[A-Za-z@'"]</match>
    </context>
    <context id="calcpad" class="no-spell-check">
      <include>
        <context ref="line-comment"/>
        <context ref="string-double"/>
        <context ref="directive"/>
        <context ref="greek-backtick"/>
        <context ref="number"/>
        <context ref="operator"/>
      </include>
    </context>
  </definitions>
</language>
"""

def ensure_calcpad_language():
    try:
        if not LANG_FILE.exists():
            LANG_FILE.write_text(CALCPAD_LANG, encoding="utf-8")
        lm = GtkSource.LanguageManager.get_default()
        paths = list(lm.get_search_path() or [])
        if str(LANG_DIR) not in paths:
            paths.insert(0, str(LANG_DIR))
            lm.set_search_path(paths)
        return lm.get_language("calcpad") is not None
    except OSError:
        return False

def load_settings():
    data = dict(DEFAULT_SETTINGS)
    if CFG_FILE.exists():
        try:
            loaded = json.loads(CFG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update({k:v for k,v in loaded.items() if k in DEFAULT_SETTINGS})
        except (OSError, json.JSONDecodeError):
            pass
    return data

def save_settings(s):
    try: CFG_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")
    except OSError: pass

def discover_cli():
    env = os.environ.get("CALCPAD_CLI")
    if env:
        p = Path(env).expanduser()
        if p.suffix.lower() == ".dll" and p.is_file():
            return ["dotnet", str(p)], f"DLL from $CALCPAD_CLI: {p}"
        if p.is_file() and os.access(p, os.X_OK):
            return [str(p)], f"Binary from $CALCPAD_CLI: {p}"
    for cmd in ("CalcpadCli", "calcpad-cli", "calcpadcli"):
        path = shutil.which(cmd)
        if path: return [path], f"PATH: {path}"
    for dll in ("/usr/share/CalcpadCE/Cli.dll",
                "/usr/lib/calcpadce/Cli.dll",
                "/opt/CalcpadCE/Cli.dll",
                str(Path.home() / ".local/share/CalcpadCE/Cli.dll")):
        if Path(dll).is_file():
            return ["dotnet", dll], f"System DLL: {dll}"
    home = Path.home() / "CalcpadCE/Calcpad.Cli/bin"
    for cfg in ("Release", "Debug"):
        for tfm in ("net10.0", "net9.0", "net8.0"):
            for name in ("Cli.dll", "Calcpad.Cli.dll"):
                p = home / cfg / tfm / name
                if p.is_file():
                    return ["dotnet", str(p)], f"Local build: {p}"
    return None, ("CalcpadCli not found.\n"
                  "Build it from source:\n"
                  "  git clone https://github.com/imartincei/CalcpadCE.git\n"
                  "  cd CalcpadCE\n"
                  "  dotnet publish -c Release Calcpad.Cli -o ~/.local/share/CalcpadCE\n"
                  "  export CALCPAD_CLI=$HOME/.local/share/CalcpadCE/Cli.dll")

class CalcpadWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_TITLE)
        self.set_default_size(1500, 950)
        self.settings = load_settings()
        self.current_file = None
        self._debounce_id = None
        self._run_busy = False
        self._closing = False
        self._cli_cmd, self._cli_hint = discover_cli()
        self._calcpad_lang_ok = ensure_calcpad_language()

        css = Gtk.CssProvider()
        css.load_from_string(
            ".calcpad-editor textview { font-family: monospace; font-size: 11pt; }"
            ".kbd-btn { font-size: 10pt; min-width: 38px; min-height: 30px; padding: 1px 4px; }"
            ".kbd-btn.warn { color: #c43; font-weight: bold; }"
            ".calcpad-keyboard { background: alpha(@theme_fg_color, 0.05); border-top: 1px solid alpha(@theme_fg_color, 0.15); padding: 2px; }"
            ".status     { padding: 4px 10px; }"
            ".hint       { padding: 0 10px; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build_headerbar()
        self._build_layout()
        self._install_shortcuts()
        self.buffer.connect("modified-changed", self._on_modified_changed)
        self.connect("close-request", self._on_close_request)
        GLib.timeout_add(400, self._initial_run)

    def _build_headerbar(self):
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)
        def mkbtn(icon, tip, cb):
            b = Gtk.Button.new_from_icon_name(icon)
            b.set_tooltip_text(tip); b.connect("clicked", cb); return b
        header.pack_start(mkbtn("document-new-symbolic","New (Ctrl+N)",self.on_new))
        header.pack_start(mkbtn("document-open-symbolic","Open (Ctrl+O)",self.on_open))
        self.recent_btn = Gtk.MenuButton(
            icon_name="document-open-recent-symbolic", tooltip_text="Open recent")
        self._refresh_recent_menu()
        header.pack_start(self.recent_btn)
        header.pack_start(mkbtn("document-save-symbolic","Save (Ctrl+S)",self.on_save))
        header.pack_start(mkbtn("document-save-as-symbolic","Save As (Ctrl+Shift+S)",self.on_save_as))
        header.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        header.pack_start(mkbtn("media-playback-start-symbolic","Calculate (F5)",self.on_run))

        export_btn = Gtk.MenuButton(icon_name="document-send-symbolic", tooltip_text="Export")
        menu = Gio.Menu()
        menu.append("Export HTML…","win.export_html")
        menu.append("Export PDF…","win.export_pdf")
        menu.append("Export Word (DOCX)…","win.export_docx")
        export_btn.set_menu_model(menu)
        header.pack_start(export_btn)
        for name,fmt in [("export_html","html"),("export_pdf","pdf"),("export_docx","docx")]:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda _a,_p,f=fmt: self._export(f))
            self.add_action(a)

        self.auto_toggle = Gtk.ToggleButton(icon_name="view-refresh-symbolic", tooltip_text="Auto-refresh")
        self.auto_toggle.set_active(self.settings["auto_refresh"])
        self.auto_toggle.connect("toggled", self._on_toggle, "auto_refresh")
        header.pack_end(self.auto_toggle)
        self.dark_toggle = Gtk.ToggleButton(icon_name="weather-clear-night-symbolic", tooltip_text="Dark preview")
        self.dark_toggle.set_active(self.settings["dark_preview"])
        self.dark_toggle.connect("toggled", self._on_toggle, "dark_preview")
        self.dark_toggle.connect("toggled", lambda *_: self.on_run(None))
        header.pack_end(self.dark_toggle)
        self.comma_toggle = Gtk.ToggleButton(icon_name="accessories-calculator-symbolic", tooltip_text="Decimal: comma instead of dot")
        self.comma_toggle.set_active(self.settings.get("decimal_comma", False))
        self.comma_toggle.connect("toggled", self._on_toggle, "decimal_comma")
        self.comma_toggle.connect("toggled", lambda *_: self.on_run(None))
        header.pack_end(self.comma_toggle)

    def _on_toggle(self, btn, key):
        self.settings[key] = btn.get_active(); save_settings(self.settings)

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
        root.append(inner)
        root.append(self._build_keyboard())
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")
        root.append(self.status)
        if self._cli_cmd:
            self.set_status(f"Ready. CLI: {self._cli_hint}")
        else:
            self.set_status("Calcpad.Cli not found - see preview pane.")


    def _build_keyboard(self):
        # Each row is a list of (label, insert-text, optional-class)
        rows = [
            # Zahlen + Operatoren + häufige Buttons
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
             ("⊗", "%"), ("x³", "^3"), ("≠", "<>"),
             ("∨", "or"), ("π", "π"), ("←", "__bksp__"),
             ("cos", "cos("), ("sec", "sec("), ("round", "round("),
             ("trunc", "trunc("), ("im", "im("),
             ("Plot", "$Plot{"), ("Map", "$Map{"), ("Sum", "∑"),
             ("ι", "ι"), ("κ", "κ"),
             ("λ", "λ"), ("μ", "μ"),
             ("ν", "ν"), ("ξ", "ξ"),
             ("ο", "ο"), ("π", "π")],
            [("1", "1"), ("2", "2"), ("3", "3"), ("+", "+"),
             ("!", "!"), ("xʸ", "^"), ("≤", "<="),
             ("⊕", "xor"), ("i", "i"), ("↵", "\n"),
             ("tan", "tan("), ("cot", "cot("), ("floor", "floor("),
             ("ceiling", "ceiling("), ("phase", "phase("),
             ("Sup", "sup("), ("Inf", "inf("), ("Product", "∏"),
             ("ρ", "ρ"), ("ς", "ς"),
             ("σ", "σ"), ("τ", "τ"),
             ("υ", "υ"), ("φ", "φ"),
             ("χ", "χ"), ("ψ", "ψ")],
            [("0", "0"), (".", "."), ("=", "="), ("−", "-"),
             ("10ˣ", "10^"), ("eˣ", "exp("), ("≥", ">="),
             ("∠", "∠"), ("(", "("), (")", ")"),
             ("atan2", "atan2("), ("random", "random("), ("abs", "abs("),
             ("sign", "sign("), ("conj", "conj("),
             ("Area", "area("), ("Slope", "slope("), ("Repeat", "repeat("),
             ("ω", "ω"), ("ϑ", "ϑ"),
             ("°", "°"), ("′", "′"),
             ("″", "″"), ("ø", "ø"),
             ("‰", "‰"), ("aA", "__case__")],
        ]
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(4); box.set_margin_end(4)
        box.set_margin_top(2); box.set_margin_bottom(4)
        box.add_css_class("calcpad-keyboard")
        for row in rows:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              spacing=2, homogeneous=True)
            for item in row:
                label, action = item[0], item[1]
                cls = item[2] if len(item) > 2 else None
                btn = Gtk.Button(label=label)
                btn.set_can_focus(False)
                btn.add_css_class("kbd-btn")
                if cls:
                    btn.add_css_class(cls)
                if action == "__clear__":
                    btn.set_tooltip_text("Clear editor")
                    btn.connect("clicked", lambda _b: self._kbd_clear())
                elif action == "__bksp__":
                    btn.set_tooltip_text("Backspace")
                    btn.connect("clicked", lambda _b: self._kbd_backspace())
                elif action == "__case__":
                    btn.set_tooltip_text("Toggle case")
                    btn.connect("clicked", lambda _b: None)
                else:
                    btn.connect("clicked",
                                lambda _b, t=action: self.insert_at_cursor(t))
                row_box.append(btn)
            box.append(row_box)
        return box

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

    def _build_editor(self):
        self.buffer = GtkSource.Buffer()
        self.buffer.set_highlight_syntax(True)
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
        self.editor.set_wrap_mode(Gtk.WrapMode.NONE)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.editor); return scroll

    def _build_preview(self):
        self.webview = WebKit.WebView()
        self.webview.load_html(self._wrap_preview(
            "<h3 style='color:#888;font-family:sans-serif'>Press Calculate (F5) or start typing...</h3>"
        ), "file:///")
        return self.webview

    def _wrap_preview(self, body):
        css = "body{font-family:'Segoe UI','Liberation Sans',sans-serif;padding:1em;line-height:1.6;color:#111}.calcpad-output var{font-style:italic;font-family:'Cambria Math','STIX Two Math',serif;color:#0066DD}.calcpad-output i{font-style:italic;font-family:'Cambria Math','STIX Two Math',serif;color:#119911}.eq{display:inline-block;vertical-align:middle}.dvc,.dvr,.dvs{display:inline-block;vertical-align:middle;white-space:nowrap}.dvc{padding-left:2pt;padding-right:2pt;text-align:center;line-height:110%}.dvr{text-align:center;line-height:110%;position:relative;top:-3pt}.dvs{text-align:left;line-height:110%}.dvl{display:block;border-bottom:solid 1pt #444;margin-top:1pt;margin-bottom:1pt}.dvc.down{position:relative;top:.5em}.dvc.up{position:relative;bottom:.6em}.low{font-size:70%;display:inline-block;position:relative;top:1.2em}sub,sup{font-size:70%}.o1{display:inline-block;border-top:1pt solid currentColor;padding-top:1pt;margin-left:-1pt}.r1{display:inline-block;font-size:140%;line-height:60%;vertical-align:-.05em;margin-right:-2pt}.r1::before{content:'\\221a'}.nary{font-size:240%;font-family:'Cambria Math',serif;line-height:70%;display:inline-block;margin:0 2pt;vertical-align:middle;color:#C080F0}.calcpad-output p{margin:.45em 0}"
        if self.settings["dark_preview"]:
            css = css + 'body{background:#1e1e1e;color:#e0e0e0}.calcpad-output var{color:#6cb6ff}.calcpad-output i{color:#7ed87e}.dvl{border-bottom-color:#bbb}.o1{border-top-color:#bbb}table,td,th{border-color:#555}a{color:#6cf}pre{background:#111;color:#eee}'
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<style>" + css + "</style>"
                "</head><body>" + body + "</body></html>")
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<style>" + css + "</style>"
                "</head><body>" + body + "</body></html>")
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<style>" + '/* Calcpad fractions */.eq{vertical-align:middle}.dvc{display:inline-grid;grid-template-rows:auto auto auto;justify-items:center;align-items:center;vertical-align:middle;margin:0 .2em;line-height:1.15}.dvc>:nth-child(1){grid-row:1;padding:0 .25em}.dvl{grid-row:2;width:100%;height:1px;background:currentColor;min-width:2em;margin:.15em 0}.dvc>:nth-child(3){grid-row:3;padding:0 .25em}var{font-style:italic}.calcpad-output p{margin:.4em 0;line-height:1.8}' + "</style>"
                f"</head><body>{body}</body></html>")

    def _install_shortcuts(self):
        ctl = Gtk.ShortcutController()
        ctl.set_scope(Gtk.ShortcutScope.GLOBAL); self.add_controller(ctl)
        def add(combo, fn):
            trig = Gtk.ShortcutTrigger.parse_string(combo)
            if trig is None: return
            def cb(_w,_a,_u=None,_fn=fn): _fn(None); return True
            ctl.add_shortcut(Gtk.Shortcut.new(trig, Gtk.CallbackAction.new(cb)))
        add("<Control>n", self.on_new); add("<Control>o", self.on_open)
        add("<Control>s", self.on_save); add("<Control><Shift>s", self.on_save_as)
        add("F5", self.on_run); add("<Control>g", lambda _: self.symbol_search.grab_focus())
        for key,ch in QUICK_HOTKEYS.items():
            add(f"<Control><Alt>{key}", lambda _b,c=ch: self.insert_at_cursor(c))

    def insert_at_cursor(self, text):
        text = text.replace("µ", "μ")
        self.buffer.insert_at_cursor(text)
        GLib.idle_add(self.editor.grab_focus)

    def _get_text(self):
        s,e = self.buffer.get_bounds(); return self._normalize(self.buffer.get_text(s,e,True))


    # ---- Unicode-Normalisierung ---------------------------------
    _UNICODE_FIX = {
        "\u00b5": "\u03bc",
        "\u2126": "\u03a9",
        "\u2212": "-",
        "\u00d7": "*",
        "\u00f7": "/",
    }
    _SUPER_DIGITS = str.maketrans(
        "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079",
        "0123456789")
    _SUB_DIGITS = str.maketrans(
        "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089",
        "0123456789")

    def _normalize(self, text):
        import re as _re
        for bad, good in self._UNICODE_FIX.items():
            text = text.replace(bad, good)
        text = _re.sub(
            r"[\u2070\u00b9\u00b2\u00b3\u2074-\u2079]+",
            lambda m: "^" + m.group(0).translate(self._SUPER_DIGITS),
            text)
        text = _re.sub(
            r"[\u2080-\u2089]+",
            lambda m: "_" + m.group(0).translate(self._SUB_DIGITS),
            text)
        return text

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


    @staticmethod
    def _dots_to_commas(text):
        import re as _re
        return _re.sub(r"(\d)\.(\d)", r"\1,\2", text)

    def _apply_decimal_comma_html(self, html):
        import re as _re
        parts = _re.split(r"(<[^>]+>)", html)
        for i in range(0, len(parts), 2):
            parts[i] = self._dots_to_commas(parts[i])
        return "".join(parts)

    def _apply_decimal_comma_docx(self, docx_path):
        import zipfile, shutil
        tmp = docx_path + ".tmp"
        with zipfile.ZipFile(docx_path, "r") as zin:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename.endswith(".xml") and (
                            "document" in item.filename
                            or "header" in item.filename
                            or "footer" in item.filename):
                        try:
                            text = data.decode("utf-8")
                            text = self._apply_decimal_comma_html(text)
                            data = text.encode("utf-8")
                        except UnicodeDecodeError:
                            pass
                    zout.writestr(item, data)
        shutil.move(tmp, docx_path)

    def on_text_changed(self, *_):
        if not self.auto_toggle.get_active(): return
        if self._debounce_id is not None: GLib.source_remove(self._debounce_id)
        self._debounce_id = GLib.timeout_add(700, self._debounced_run)

    def _debounced_run(self):
        self._debounce_id = None; self.on_run(None); return False

    def _run_cli(self, out_format, body_only):
        if not self._cli_cmd:
            return None, self._wrap_preview(
                f"<pre style='color:#b00;font-family:monospace;padding:1em'>"
                f"{GLib.markup_escape_text(self._cli_hint)}</pre>")
        try:
            tmp = tempfile.NamedTemporaryFile("w", suffix=".cpd", delete=False, encoding="utf-8")
            tmp.write(self._get_text()); tmp.close(); in_path = tmp.name
        except OSError as e:
            return None, self._wrap_preview(
                f"<pre style='color:#b00'>Cannot create temp file: {e}</pre>")
        out_path = str(Path(in_path).with_suffix(f".{out_format}"))
        cmd = list(self._cli_cmd) + [in_path, out_path, "-s"]
        if body_only and out_format in ("html","htm"): cmd.append("-b")
        env = os.environ.copy(); env["DOTNET_CLI_UI_LANGUAGE"] = "en"
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
            if r.returncode != 0 or not Path(out_path).exists():
                msg = ((r.stderr or "") + "\n" + (r.stdout or "")).strip() \
                      or f"CLI exit code {r.returncode}"
                return None, self._wrap_preview(
                    f"<pre style='color:#b00;font-family:monospace;padding:1em'>"
                    f"{GLib.markup_escape_text(msg)}</pre>")
            return out_path, None
        except subprocess.TimeoutExpired:
            return None, self._wrap_preview(
                "<pre style='color:#b00'>Calculation timed out (60s).</pre>")
        except OSError as e:
            return None, self._wrap_preview(
                f"<pre style='color:#b00'>{GLib.markup_escape_text(str(e))}</pre>")
        finally:
            try: os.unlink(in_path)
            except OSError: pass

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
            self.webview.load_html(self._wrap_preview(html), base)
            self.set_status(f"OK - {len(html):,} bytes of output.")
        finally:
            if out:
                try: os.unlink(out)
                except OSError: pass
            self._run_busy = False
        return False

    def on_new(self, _btn):
        if self.is_dirty(): self._confirm_discard(lambda ok: ok and self._do_new())
        else: self._do_new()

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
                Path(self.current_file).write_text(self._get_text(), encoding="utf-8")
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
            Path(path).write_text(self._get_text(), encoding="utf-8")
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
                        if self.settings.get("decimal_comma", False):
                            tp = Path(target)
                            ext = tp.suffix.lower()
                            if ext in (".html", ".htm"):
                                txt = tp.read_text(encoding="utf-8")
                                tp.write_text(
                                    self._apply_decimal_comma_html(txt),
                                    encoding="utf-8")
                            elif ext == ".docx":
                                self._apply_decimal_comma_docx(str(tp))
                        self.settings["last_dir"] = str(Path(target).parent)
                        save_settings(self.settings)
                        self.set_status(f"Exported -> {target}")
                    except OSError as e: self.set_status(f"Move failed: {e}")
                return False
            GLib.idle_add(finish)
        threading.Thread(target=worker, daemon=True).start()

    def set_status(self, msg): self.status.set_text(msg)
    def _initial_run(self): self.on_run(None); return False


class CalcpadApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self._win = None
    def do_activate(self):
        if self._win is None: self._win = CalcpadWindow(self)
        self._win.present()
    def do_open(self, files, _n, _hint):
        self.do_activate()
        if files and self._win is not None:
            path = files[0].get_path()
            if path: GLib.idle_add(self._win.open_file_path, path)


def run_doctor():
    print("CalcpadCE Linux GUI - Doctor")
    print("=" * 35)
    print(f"Python:        {sys.version.split()[0]}")
    print(f"GTK:           {Gtk.get_major_version()}.{Gtk.get_minor_version()}."
          f"{Gtk.get_micro_version()}")
    print(f"GtkSourceView: {GtkSource.MAJOR_VERSION}.{GtkSource.MINOR_VERSION}")
    print(f"WebKitGTK:     6.0")
    print(f"Config:        {CFG_FILE}")
    print(f"Lang file:     {LANG_FILE} "
          f"({'present' if LANG_FILE.exists() else 'will be created'})")
    cmd, hint = discover_cli()
    if not cmd:
        print("CLI:           NOT FOUND"); print(); print(hint); return 1
    print(f"CLI:           OK  {hint}")
    with tempfile.TemporaryDirectory() as td:
        in_p = Path(td) / "test.cpd"; out_p = Path(td) / "test.html"
        in_p.write_text("x = 6\ny = 7\nz = x*y\n", encoding="utf-8")
        env = os.environ.copy(); env["DOTNET_CLI_UI_LANGUAGE"] = "en"
        try:
            r = subprocess.run(list(cmd) + [str(in_p), str(out_p), "-s", "-b"],
                               capture_output=True, text=True, timeout=30, env=env)
            if r.returncode != 0 or not out_p.exists():
                print(f"Roundtrip:     FAILED (exit {r.returncode})")
                if r.stderr.strip(): print(f"  stderr: {r.stderr.strip()[:300]}")
                return 1
            body = out_p.read_text(encoding="utf-8", errors="replace")
            if "42" in body:
                print("Roundtrip:     OK (6 * 7 = 42 found in output)"); return 0
            print(f"Roundtrip:     UNCLEAR (no '42' in {len(body)} bytes)"); return 0
        except subprocess.TimeoutExpired:
            print("Roundtrip:     TIMEOUT (30s)"); return 1
        except OSError as e:
            print(f"Roundtrip:     ERROR: {e}"); return 1


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


if __name__ == "__main__":
    sys.exit(main())
