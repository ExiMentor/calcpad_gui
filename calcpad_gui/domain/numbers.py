"""NumberFormatting implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
import re

class NumberFormatting:
    """GTK-independent behavior; callable names retained for compatibility."""

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

    def _code_with_decimal_places(self, code: str) -> str:
        try:
            places = int(self.settings.get("decimal_places", 3))
        except Exception:
            places = 3

        places = max(0, min(15, places))
        return f"#round {places}\n" + code
