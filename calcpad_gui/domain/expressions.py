"""ExpressionTransforms implementation. See docs/ARCHITECTURE.md for state contracts."""
from __future__ import annotations
from calcpad_gui.data import _SUB_DIGITS
from calcpad_gui.data import _SUPER_DIGITS
import re

class ExpressionTransforms:
    """GTK-independent behavior; callable names retained for compatibility."""

    def _format_calcpad_line(self, line: str) -> str:
        quote_positions = [p for p in (line.find("'"), line.find('"')) if p >= 0]
        if quote_positions:
            split_at = min(quote_positions)
            code = line[:split_at]
            comment = line[split_at:]
        else:
            code = line
            comment = ""

        code = re.sub(r"\s*(≤|≥|≠|==|!=|=|<|>|\+|\*|/|\\\\|\^)\s*", r" \1 ", code)

        code = re.sub(r"(?<=\S)\s+-\s+(?=\S)", " - ", code)
        code = re.sub(r"(?<=[A-Za-z0-9_)\]Α-Ωα-ωµμ])\s*-\s*(?=[A-Za-z0-9_(\[Α-Ωα-ωµμ])", " - ", code)

        leading = re.match(r"^\s*", code).group(0)
        body = code[len(leading):]
        body = re.sub(r"[ \t]+", " ", body).strip()

        return leading + body + comment

    @classmethod
    def _parallel_resistance_expression(cls, expression):
        """Expand a || b [|| c] to the reciprocal-sum expression Calcpad understands."""
        expression = expression.strip()
        if "||" not in expression:
            return expression

        # Split only at the current parenthesis level. Nested parallel groups
        # are handled recursively below.
        parts = []
        start = 0
        depth = 0
        i = 0
        while i < len(expression):
            ch = expression[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == "|" and i + 1 < len(expression) and expression[i + 1] == "|" and depth == 0:
                parts.append(expression[start:i].strip())
                start = i + 2
                i += 1
            i += 1

        if parts:
            parts.append(expression[start:].strip())
            if any(not part for part in parts):
                return expression
            terms = [cls._parallel_resistance_expression(part) for part in parts]
            reciprocal_sum = " + ".join(f"1 / ({term})" for term in terms)
            return f"1 / ({reciprocal_sum})"

        # No top-level operator: recurse into balanced parentheses so that
        # expressions such as 2 * (R1 || R2) also work.
        out = []
        i = 0
        while i < len(expression):
            if expression[i] != "(":
                out.append(expression[i])
                i += 1
                continue
            depth = 1
            end = i + 1
            while end < len(expression) and depth:
                if expression[end] == "(":
                    depth += 1
                elif expression[end] == ")":
                    depth -= 1
                end += 1
            if depth:
                return expression
            inner = expression[i + 1:end - 1]
            out.append("(" + cls._parallel_resistance_expression(inner) + ")")
            i = end
        return "".join(out)

    @classmethod
    def _expand_parallel_resistors(cls, text):
        """Expand the custom resistor operator || without changing editor text."""
        result = []
        for line in text.splitlines(keepends=True):
            ending = "\n" if line.endswith("\n") else ""
            raw = line[:-1] if ending else line
            stripped = raw.lstrip()
            if "||" not in raw or stripped.startswith(("'", '"', "#")):
                result.append(line)
                continue

            # Keep inline comments untouched. Calcpad comments start with '.
            comment_at = raw.find("'")
            code = raw if comment_at < 0 else raw[:comment_at]
            comment = "" if comment_at < 0 else raw[comment_at:]

            # For assignments, transform only the right-hand expression.
            eq_at = -1
            depth = 0
            for i, ch in enumerate(code):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth = max(0, depth - 1)
                elif ch == "=" and depth == 0:
                    previous = code[i - 1] if i else ""
                    following = code[i + 1] if i + 1 < len(code) else ""
                    if previous not in "<>!=" and following != "=":
                        eq_at = i
                        break

            if eq_at >= 0:
                left = code[:eq_at + 1]
                right = code[eq_at + 1:]
                leading = right[:len(right) - len(right.lstrip())]
                expanded = cls._parallel_resistance_expression(right)
                code = left + leading + expanded
            else:
                leading = code[:len(code) - len(code.lstrip())]
                code = leading + cls._parallel_resistance_expression(code)

            result.append(code + comment + ending)
        return "".join(result)

    def _normalize(self, text):
        import re as _re
        unicode_fix = getattr(
            self,
            "_UNICODE_FIX",
            globals().get("_UNICODE_FIX", globals().get("UNICODE_FIX", {}))
        )

        for bad, good in unicode_fix.items():
            text = text.replace(bad, good)

        # German keyboards produce U+00B5 MICRO SIGN (µ), while Calcpad
        # expects U+03BC GREEK SMALL LETTER MU (μ) for the micro prefix.
        # Normalize only the text sent to Calcpad; keep the editor unchanged.
        text = text.replace("µ", "μ")
        text = _re.sub(
            r"[\u2070\u00b9\u00b2\u00b3\u2074-\u2079]+",
            lambda m: "^" + m.group(0).translate(_SUPER_DIGITS),
            text)
        text = _re.sub(
            r"[\u2080-\u2089]+",
            lambda m: "_" + m.group(0).translate(_SUB_DIGITS),
            text)
        text = self._expand_parallel_resistors(text)
        return text
