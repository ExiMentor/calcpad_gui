"""PreviewRenderer implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.resource_loader import read_resource

class PreviewRenderer:
    """GTK-independent behavior; callable names retained for compatibility."""

    def _wrap_preview(self, body):
        body = self._format_preview_numbers(body)
        css = read_resource('preview.css')
        if self.settings["dark_preview"]:
            css = css + read_resource('preview-dark.css')
        root_script = read_resource('root-fix-v3.html')
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='generator' content='CalcpadCE GTK root-fix-v3'>"
                "<style>" + css + "</style>"
                "</head><body>" + body + root_script + "</body></html>")

    def _inject_output_line_navigation(self, html):
        css = read_resource('line-navigation.css.html')
        js = read_resource('line-navigation.js.html')
        insert = css + js

        if 'id="calcpad-clickable-line-script"' in html:
            return html

        lower = html.lower()
        idx = lower.rfind("</body>")
        if idx >= 0:
            return html[:idx] + insert + html[idx:]
        return html + insert
