"""PreviewActions implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.bootstrap import WebKit

class PreviewActions:
    """Window callbacks; requires the shared CalcpadWindow state."""

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
