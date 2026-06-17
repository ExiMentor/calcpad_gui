#!/usr/bin/env python3
"""
CalcpadCE Linux GUI v4 (GTK 4.10+ only)
Repo: https://github.com/imartincei/CalcpadCE
"""
from __future__ import annotations
import re
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
    ("≥","greater or eq","≥"),("≠","not equal","≠"),
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
        # comments / text:
        # Calcpad text comments usually start with single or double quotes.
        # Apply this last so it overrides variables, units and operators.
        text_tag = self._hl_tags["text"]
        for line_match in re.finditer(r"(?m)^.*$", text):
            line = line_match.group(0)
            line_start = line_match.start()

            quote_positions = [
                pos for pos in (
                    line.find('"'),
                    line.find("'"),
                    line.find("“"),
                    line.find("‘"),
                )
                if pos >= 0
            ]

            if not quote_positions:
                continue

            qpos = min(quote_positions)
            a = self.buffer.get_iter_at_offset(line_start + qpos)
            b = self.buffer.get_iter_at_offset(line_match.end())
            self.buffer.apply_tag(text_tag, a, b)

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



def inject_output_scroll_restore(html: str) -> str:
    """Keep WebKit preview scroll position stable across HTML reloads."""
    script = r"""
<script id="calcpad-scroll-restore">
(function () {
    const markerY = "calcpadScrollY=";
    const markerRatio = "calcpadScrollRatio=";

    function getScrollElement() {
        return document.scrollingElement || document.documentElement || document.body;
    }

    function getMaxScroll(el) {
        if (!el) return 0;
        return Math.max(0, el.scrollHeight - el.clientHeight);
    }

    function readValue(marker) {
        const name = String(window.name || "");
        const idx = name.indexOf(marker);
        if (idx < 0) return 0;

        const raw = name.slice(idx + marker.length).split(";")[0];
        const value = parseFloat(raw);

        return Number.isFinite(value) ? value : 0;
    }

    function writeValue(marker, value) {
        let name = String(window.name || "");
        const escaped = marker.replace(/[.*+?^${}()|[\]\]/g, "\$&");
        name = name.replace(new RegExp(";?" + escaped + "[0-9.]+", "g"), "");
        window.name = name + ";" + marker + String(Math.max(0, value || 0));
    }

    function save() {
        const el = getScrollElement();
        if (!el) return;

        const y = el.scrollTop || window.scrollY || 0;
        const max = getMaxScroll(el);
        const ratio = max > 0 ? y / max : 0;

        writeValue(markerY, y);
        writeValue(markerRatio, ratio);
    }

    function restore() {
        const el = getScrollElement();
        if (!el) return;

        const savedY = readValue(markerY);
        const savedRatio = readValue(markerRatio);
        const max = getMaxScroll(el);

        let targetY = savedY;

        if (max > 0 && savedRatio > 0) {
            targetY = Math.min(savedY, max);
            if (savedY > max) {
                targetY = max * savedRatio;
            }
        }

        if (!targetY) return;

        function apply() {
            window.scrollTo(0, targetY);
            el.scrollTop = targetY;
        }

        apply();
        setTimeout(apply, 50);
        setTimeout(apply, 150);
        setTimeout(apply, 350);
        setTimeout(apply, 700);
    }

    window.addEventListener("scroll", save, { passive: true });
    window.addEventListener("beforeunload", save);
    window.addEventListener("DOMContentLoaded", restore);
    window.addEventListener("load", restore);
})();
</script>
"""

    if 'id="calcpad-scroll-restore"' in html:
        return html

    lower = html.lower()
    body_idx = lower.rfind("</body>")

    if body_idx >= 0:
        return html[:body_idx] + script + html[body_idx:]

    return html + script

class CalcpadWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_TITLE)
        self.set_default_size(1500, 950)
        self.settings = load_settings()
        self.settings.setdefault("decimal_places", 3)
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
        self._setup_zoom_controls()
        self._setup_line_navigation_controls()
        self._setup_format_controls()
        self._install_shortcuts()
        self.buffer.connect("modified-changed", self._on_modified_changed)
        self.buffer.connect("notify::cursor-position", self._on_editor_cursor_position_changed)
        self._setup_editor_highlighting()
        self.connect("close-request", self._on_close_request)
        GLib.timeout_add(400, self._initial_run)


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

        # 1) full comment/text lines first collected, applied last
        comment_ranges = []
        for m in re.finditer(r"(?m)^[ \t]*[\"'“‘].*$", text):
            comment_ranges.append((m.start(), m.end()))

        def in_comment(pos):
            return any(a <= pos < b for a, b in comment_ranges)

        # 2) variable name only left of '='
        for m in re.finditer(r"(?m)^[ \t]*([A-Za-z_Α-Ωα-ωµμ][A-Za-z0-9_Α-Ωα-ωµμ]*)[ \t]*=", text):
            if not in_comment(m.start(1)):
                apply_range("var", m.start(1), m.end(1))

        # 3) functions
        for m in re.finditer(
            r"\b(?:sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|sqrt|root|root2|ln|log|exp|abs|min|max|round|trunc|floor|ceiling|random|sign|conj|re|im|phase|area|slope|sup|inf)\b(?=\s*\()",
            text,
            re.IGNORECASE
        ):
            if not in_comment(m.start()):
                apply_range("func", m.start(), m.end())

        # 4) units
        unit_pattern = r"(?<![A-Za-z_])(?:MΩ|kΩ|Ω|µF|μF|uF|mF|nF|pF|µH|μH|uH|mH|nH|µV|μV|uV|mV|kV|V|µA|μA|uA|mA|A|mW|kW|W|MHz|kHz|Hz|MPa|kPa|Pa|mm|cm|km|ms|°C|K|m|s)(?![A-Za-z_])"
        for m in re.finditer(unit_pattern, text):
            if not in_comment(m.start()):
                apply_range("unit", m.start(), m.end())

        # 5) operators
        for m in re.finditer(r"[+\-*/^=<>≤≥≠%∑∏√·×]", text):
            if not in_comment(m.start()):
                apply_range("op", m.start(), m.end())

        # 6) brackets
        for m in re.finditer(r"[()\[\]{}]", text):
            if not in_comment(m.start()):
                apply_range("bracket", m.start(), m.end())

        # 7) directives
        for m in re.finditer(
            r"(?m)^\s*#(?:if|else|end\s+if|for|repeat|loop|break|include|hide|show|pre|post)\b",
            text,
            re.IGNORECASE
        ):
            if not in_comment(m.start()):
                apply_range("keyword", m.start(), m.end())

        # 8) comments/text last so they override everything
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
        # Kept for compatibility; editor line sync is handled by cursor-position.
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

    def _inject_output_line_navigation(self, html):
        css = """
<style id="calcpad-clickable-line-numbers">
.calcpad-output p::before,
.calcpad-output h1::before,
.calcpad-output h2::before,
.calcpad-output h3::before,
.calcpad-output h4::before,
.calcpad-output h5::before,
.calcpad-output h6::before{
    content:none !important;
}
.calcpad-output p,
.calcpad-output h1,
.calcpad-output h2,
.calcpad-output h3,
.calcpad-output h4,
.calcpad-output h5,
.calcpad-output h6{
    position:relative;
    padding-left:3.2em;
}
.cp-line-no{
    position:absolute;
    left:0;
    top:0;
    width:2.4em;
    text-align:right;
    color:#999;
    font-family:monospace;
    font-size:85%;
    user-select:none;
    cursor:pointer;
}
.cp-line-no:hover{
    color:#0066dd;
    text-decoration:underline;
}
.cp-line-flash{
    outline:2px solid rgba(0,102,221,.35);
    outline-offset:2px;
}
</style>
"""
        js = """
<script id="calcpad-clickable-line-script">
(function () {
    function installLineNumbers() {
        const nodes = document.querySelectorAll(
            ".calcpad-output p,.calcpad-output h1,.calcpad-output h2,.calcpad-output h3,.calcpad-output h4,.calcpad-output h5,.calcpad-output h6"
        );

        nodes.forEach((node, index) => {
            if (node.dataset.cpLine) return;

            const line = index + 1;
            node.dataset.cpLine = String(line);

            const span = document.createElement("span");
            span.className = "cp-line-no";
            span.textContent = String(line);
            span.title = "Jump to editor line " + String(line);
            span.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                document.title = "__calcpad_jump__:" + String(line);
            });

            node.insertBefore(span, node.firstChild);
        });
    }

    document.addEventListener("DOMContentLoaded", installLineNumbers);
    window.addEventListener("load", installLineNumbers);
    setTimeout(installLineNumbers, 0);
    setTimeout(installLineNumbers, 100);
})();
</script>
"""
        insert = css + js

        if 'id="calcpad-clickable-line-script"' in html:
            return html

        lower = html.lower()
        idx = lower.rfind("</body>")
        if idx >= 0:
            return html[:idx] + insert + html[idx:]
        return html + insert


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

    def _format_calcpad_line(self, line: str) -> str:
        # Keep comments/text part unchanged.
        quote_positions = [p for p in (line.find("'"), line.find('"')) if p >= 0]
        if quote_positions:
            split_at = min(quote_positions)
            code = line[:split_at]
            comment = line[split_at:]
        else:
            code = line
            comment = ""

        # Normalize spacing around common binary operators.
        code = re.sub(r"\s*(≤|≥|≠|==|!=|=|<|>|\+|\*|/|\\\\|\^)\s*", r" \1 ", code)

        # Minus is tricky because it can be unary. Only space obvious binary minus.
        code = re.sub(r"(?<=\S)\s+-\s+(?=\S)", " - ", code)
        code = re.sub(r"(?<=[A-Za-z0-9_)\]Α-Ωα-ωµμ])\s*-\s*(?=[A-Za-z0-9_(\[Α-Ωα-ωµμ])", " - ", code)

        # Clean up duplicated whitespace, but preserve leading indentation.
        leading = re.match(r"^\s*", code).group(0)
        body = code[len(leading):]
        body = re.sub(r"[ \t]+", " ", body).strip()

        return leading + body + comment


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

        format_btn = Gtk.Button(label="Format")
        format_btn.set_tooltip_text("Format current line (Ctrl+Shift+F)")
        format_btn.connect("clicked", self._format_current_line)
        header.pack_start(format_btn)

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

        self.decimals_spin = Gtk.SpinButton.new_with_range(0, 10, 1)
        self.decimals_spin.set_value(int(self.settings.get("decimal_places", 3)))
        self.decimals_spin.set_tooltip_text("Number of decimal places")
        self.decimals_spin.set_width_chars(2)
        self.decimals_spin.connect("value-changed", self._on_decimal_places_changed)
        header.pack_end(self.decimals_spin)

    def _on_toggle(self, btn, key):
        self.settings[key] = btn.get_active(); save_settings(self.settings)

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

                    row_box.append(btn)

                page.append(row_box)

            return page

        basic_rows = [row[:10] for row in rows]
        function_rows = [row[10:18] for row in rows]
        greek_rows = [row[18:] for row in rows]

        stack.add_titled(build_keyboard_page(basic_rows), "basic", "Basic")
        stack.add_titled(build_keyboard_page(function_rows), "functions", "Functions")
        stack.add_titled(build_keyboard_page(greek_rows, greek_page=True), "greek", "Greek")

        box.append(stack)
        return box

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
        scroll.set_child(self.editor); return scroll

    def _build_preview(self):
        self.webview = WebKit.WebView()
        self.webview.connect("load-changed", self._on_preview_load_changed)
        self.webview.connect("notify::title", self._on_preview_title_changed)
        self.webview.load_html(self._wrap_preview(
            "<h3 style='color:#888;font-family:sans-serif'>Press Calculate (F5) or start typing...</h3>"
        ), "file:///")
        return self.webview


    def _js_value_to_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            if hasattr(value, "to_double"):
                return float(value.to_double())
            if hasattr(value, "to_number"):
                return float(value.to_number())
            if hasattr(value, "to_string"):
                return float(value.to_string())
        except Exception:
            return default
        return default

    def _eval_webview_js(self, script, callback=None):
        try:
            return self.webview.evaluate_javascript(
                script, -1, None, None, None, callback, None
            )
        except TypeError:
            try:
                return self.webview.evaluate_javascript(
                    script, -1, None, None, None, callback
                )
            except TypeError:
                try:
                    return self.webview.run_javascript(script, None, callback, None)
                except TypeError:
                    return self.webview.run_javascript(script, None, callback)
        except Exception:
            return None

    def _finish_webview_js(self, webview, result):
        try:
            if hasattr(webview, "evaluate_javascript_finish"):
                return webview.evaluate_javascript_finish(result)
            if hasattr(webview, "run_javascript_finish"):
                js_result = webview.run_javascript_finish(result)
                if hasattr(js_result, "get_js_value"):
                    return js_result.get_js_value()
                return js_result
        except Exception:
            return None
        return None

    def _load_preview_preserving_scroll(self, html, base_uri):
        html = self._inject_output_line_navigation(html)
        y = getattr(self, "_preview_scroll_y", 0)

        script = f"""
<script id="calcpad-scroll-sync">
(function () {{
    const initialY = {float(y)};

    function scrollElement() {{
        return document.scrollingElement || document.documentElement || document.body;
    }}

    function saveScroll() {{
        const el = scrollElement();
        const y = el ? el.scrollTop : (window.scrollY || 0);
        document.title = "__calcpad_scroll__:" + String(Math.max(0, Math.round(y)));
    }}

    function restoreScroll() {{
        const el = scrollElement();
        if (el) el.scrollTop = initialY;
        window.scrollTo(0, initialY);
    }}

    window.addEventListener("scroll", saveScroll, {{ passive: true }});
    window.addEventListener("load", restoreScroll);
    window.addEventListener("DOMContentLoaded", restoreScroll);

    setTimeout(restoreScroll, 50);
    setTimeout(restoreScroll, 150);
    setTimeout(restoreScroll, 350);
    setTimeout(restoreScroll, 700);
}})();
</script>
"""

        if "</body>" in html:
            html = html.replace("</body>", script + "</body>")
        else:
            html += script

        self.webview.load_html(html, base_uri)

    def _on_preview_title_changed(self, webview, _param):
        title = webview.get_title() or ""

        jump_prefix = "__calcpad_jump__:"
        if title.startswith(jump_prefix):
            try:
                self._jump_editor_to_line(int(float(title[len(jump_prefix):])))
            except Exception:
                pass
            return

        prefix = "__calcpad_scroll__:"
        if not title.startswith(prefix):
            return

        try:
            self._preview_scroll_y = float(title[len(prefix):])
        except Exception:
            pass

    def _on_preview_load_changed(self, webview, load_event):
        try:
            nick = getattr(load_event, "value_nick", "")
            if nick and nick != "finished":
                return
            if not nick and "FINISHED" not in str(load_event).upper():
                return
        except Exception:
            return

        y = getattr(self, "_preview_scroll_y", 0)
        if not y:
            return

        restore_js = f"""
        (function () {{
            const y = {float(y)};
            function restore() {{
                const el = document.scrollingElement || document.documentElement || document.body;
                if (el) el.scrollTop = y;
                window.scrollTo(0, y);
            }}
            restore();
            setTimeout(restore, 50);
            setTimeout(restore, 150);
            setTimeout(restore, 350);
            setTimeout(restore, 700);
        }})();
        """

        self._eval_webview_js(restore_js)

    def _format_preview_numbers(self, html):
        try:
            places = int(self.settings.get("decimal_places", 3))
        except Exception:
            places = 3

        places = max(0, min(10, places))
        use_comma = bool(self.settings.get("decimal_comma", False))

        number_re = re.compile(
            r"(?<![A-Za-z0-9_.,])([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)(?![A-Za-z0-9_.,])"
        )

        def format_match(match):
            raw = match.group(1)
            try:
                value = float(raw)
            except Exception:
                return raw

            formatted = f"{value:.{places}f}"

            if use_comma:
                formatted = formatted.replace(".", ",")

            return formatted

        parts = re.split(r"(<[^>]+>)", html)

        for i, part in enumerate(parts):
            if part.startswith("<") and part.endswith(">"):
                continue
            parts[i] = number_re.sub(format_match, part)

        return "".join(parts)


    def _wrap_preview(self, body):
        body = self._format_preview_numbers(body)
        css = "body{font-family:'Segoe UI','Liberation Sans',sans-serif;padding:1em;line-height:1.6;color:#111}.calcpad-output var{font-style:italic;font-family:'Cambria Math','STIX Two Math',serif;color:#0066DD}.calcpad-output i{font-style:italic;font-family:'Cambria Math','STIX Two Math',serif;color:#119911}.eq{display:inline-block;vertical-align:middle}.dvc,.dvr,.dvs{display:inline-block;vertical-align:middle;white-space:nowrap}.dvc{padding-left:2pt;padding-right:2pt;text-align:center;line-height:110%}.dvr{text-align:center;line-height:110%;position:relative;top:-3pt}.dvs{text-align:left;line-height:110%}.dvl{display:block;border-bottom:solid 1pt #444;margin-top:1pt;margin-bottom:1pt}.dvc.down{position:relative;top:.5em}.dvc.up{position:relative;bottom:.6em}.low{font-size:70%;display:inline-block;position:relative;top:1.2em}sub,sup{font-size:70%}.o1{display:inline-block;border-top:1pt solid currentColor;padding-top:1pt;margin-left:-1pt}.r1{display:inline-block;font-size:140%;line-height:60%;vertical-align:-.05em;margin-right:-2pt}.r1::before{content:'\\221a'}.nary{font-size:240%;font-family:'Cambria Math',serif;line-height:70%;display:inline-block;margin:0 2pt;vertical-align:middle;color:#C080F0}.calcpad-output p{margin:.45em 0}.calcpad-output{counter-reset:cp-line;}.calcpad-output p,.calcpad-output h1,.calcpad-output h2,.calcpad-output h3,.calcpad-output h4,.calcpad-output h5,.calcpad-output h6{position:relative;padding-left:3.2em;}.calcpad-output p::before,.calcpad-output h1::before,.calcpad-output h2::before,.calcpad-output h3::before,.calcpad-output h4::before,.calcpad-output h5::before,.calcpad-output h6::before{counter-increment:cp-line;content:counter(cp-line);position:absolute;left:0;top:0;width:2.4em;text-align:right;color:#999;font-family:monospace;font-size:85%;user-select:none;}"
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

    def _code_with_decimal_places(self, code: str) -> str:
        try:
            places = int(self.settings.get("decimal_places", 3))
        except Exception:
            places = 3

        places = max(0, min(15, places))
        return f"#round {places}\n" + code

    def _run_cli(self, out_format, body_only):
        if not self._cli_cmd:
            return None, self._wrap_preview(
                f"<pre style='color:#b00;font-family:monospace;padding:1em'>"
                f"{GLib.markup_escape_text(self._cli_hint)}</pre>")
        try:
            tmp = tempfile.NamedTemporaryFile("w", suffix=".cpd", delete=False, encoding="utf-8")
            tmp.write(self._code_with_decimal_places(self._get_text())); tmp.close(); in_path = tmp.name
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
            self._load_preview_preserving_scroll(self._wrap_preview(html), base)
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
