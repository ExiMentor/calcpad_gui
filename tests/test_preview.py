"""Synthetic v3 numeric-DOM tests adapted from the user-validated patch.

No original workspace files are needed. These tests execute the actual bundled
script in Node, not WebKit: geometry doubles do not establish visual parity.
"""
import hashlib
import json
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path
from calcpad_gui.preview.html import PreviewRenderer
from calcpad_gui.domain.numbers import NumberFormatting
from calcpad_gui.preview.scroll import inject_output_scroll_restore
from calcpad_gui.data import APP_TITLE
from calcpad_gui.resource_loader import read_resource
from tests.support import ROOT

HERE = Path(__file__).resolve().parent
FIXTURES = json.loads((HERE / "fixtures/outputs.json").read_text())

class Preview(PreviewRenderer, NumberFormatting):
    pass

class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.active = None
        self.css = ""
        self.script = ""
        self.tags = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "style":
            self.active = "css"
        elif tag == "script" and attrs.get("id", "").startswith("calcpad-root-fix-"):
            self.active = "script"

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.active = None

    def handle_data(self, data):
        if self.active:
            setattr(self, self.active, getattr(self, self.active) + data)

class TreeParser(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tree = {"tag": "body", "attrs": {}, "children": []}
        self.stack = [self.tree]
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": []}
        self.stack[-1]["children"].append(node)
        if tag not in ("br", "hr", "img", "input", "meta", "link"):
            self.stack.append(node)

    def handle_endtag(self, tag):
        assert self.stack[-1]["tag"] == tag, "Unbalanced fixture: " + tag
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1]["children"].append(data)

def body_of(html):
    body = html.split("<body>", 1)[1].rsplit("</body>", 1)[0]
    return re.sub(r'\n<script id="calcpad-root-fix-v[23]">.*?</script>\n', "", body, flags=re.S)

def rules(css):
    assert not re.sub(r"[^{}]+\{[^{}]*\}", "", css).strip(), "Unbalanced CSS"
    result = {}
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        declarations = dict(declaration.split(":", 1) for declaration in match[2].split(";") if declaration)
        for selector in match[1].split(","):
            result.setdefault(selector.strip(), {}).update(declarations)
    return result

def root(content, form="forward", level=1, bar=1, degree="", own_eq=False, padding=""):
    r = f'<span class="r{level}{" eq" if own_eq else ""}">'
    o = f'<span class="o{bar}"{padding}>'
    index = f"<sup>{degree}</sup>" if degree else ""
    if form == "forward":
        return r + index + o + content + "</span></span>"
    if form == "adjacent":
        return r + index + "</span> \n" + o + content + "</span>"
    if form == "inverse":
        return o + index + r + content + "</span></span>"
    if form == "inverse-marker":
        return o + index + r + "</span> \n" + content + "</span>"
    raise AssertionError(form)

def fraction(numerator, denominator, kind="dvr"):
    return (f'<span class="{kind}"><span class="dvl">{numerator}</span>'
            f'<span class="denominator">{denominator}</span></span>')

def math_body(content, scope="eq"):
    if scope == "eq":
        return '<div class="calcpad-output"><p><span class="eq">' + content + '</span></p></div>'
    if scope == "output":
        return '<div class="calcpad-output"><p>' + content + '</p></div>'
    return "<p>" + content + "</p>"

def descendants(tree):
    if isinstance(tree, str):
        return
    yield tree
    for child in tree["children"]:
        yield from descendants(child)

def with_class(tree, name):
    return [node for node in descendants(tree) if name in node["attrs"].get("class", "").split()]

class PreviewRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixed = Preview
        cls.node = shutil.which("node")

    def preview(self, dark=False, places=3, comma=False):
        preview = self.fixed()
        preview.settings = {"dark_preview": dark, "decimal_places": places, "decimal_comma": comma}
        return preview

    def dom(self, fixture, dark=False, events=()):
        self.assertIsNotNone(self.node, "Node is required for the actual script tests")
        html = self.preview(dark=dark)._wrap_preview(fixture)
        page = Page(html)
        result = subprocess.run([self.node, str(HERE / "dom_harness.js")],
                                input=json.dumps({"tree": TreeParser(body_of(html)).tree,
                                                  "script": page.script, "events": events}),
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["textBefore"], data["textAfter"], "Source math/text must not be changed")
        self.assertTrue(data["idempotent"], "Installing twice must not add a second root")
        self.assertTrue(data["listenerStable"], "Installing twice must not add listeners")
        self.assertEqual(data["repeatWrites"], 0, "An unchanged redraw must perform no DOM/style writes")
        self.assertEqual(data["observerCount"], 1)
        return data

    def assert_enclosures(self, snapshot, count):
        self.assertEqual(len(snapshot["roots"]), count)
        for entry in snapshot["roots"]:
            svg = entry["svg"]
            self.assertEqual(svg["attrs"]["aria-hidden"], "true")
            self.assertEqual(svg["attrs"]["focusable"], "false")
            self.assertEqual(len(svg["children"]), 1)
            path = svg["children"][0]["attrs"]
            self.assertEqual(path["stroke"], "currentColor")
            self.assertEqual(path["fill"], "none")
            d = path["d"]
            self.assertEqual(d.count("M"), 1)
            self.assertEqual(d.count("L"), 4)
            points = [tuple(map(float, match)) for match in re.findall(r"[ML]([0-9.+-]+) ([0-9.+-]+)", d)]
            self.assertEqual(len(points), 5)
            width, height = [float(value) for value in svg["attrs"]["viewBox"].split()[2:]]
            self.assertAlmostEqual(width, entry["box"]["width"] / entry["scale"], delta=.02)
            self.assertAlmostEqual(height, entry["box"]["height"] / entry["scale"], delta=.02)
            boxes = [entry["radicand"]] + [item["box"] for item in entry["descendants"]
                     if item["box"]["right"] > item["box"]["left"] and item["box"]["bottom"] > item["box"]["top"]]
            left = min(box["left"] for box in boxes)
            right = max(box["right"] for box in boxes)
            top = min(box["top"] for box in boxes)
            bottom = max(box["bottom"] for box in boxes)
            self.assertAlmostEqual(points[3][1], points[4][1], delta=.001)
            self.assertLess(points[3][0], left, "Rising stroke must join left of all radicand content")
            self.assertGreater(points[4][0], right, "Continuous overbar must cover full numerator/denominator width")
            self.assertLessEqual(points[3][1], top - 1.45, "Bar must clear the topmost visual rect")
            self.assertGreaterEqual(points[2][1], bottom + 1.45, "Radical foot must clear the denominator")
            self.assertGreater(points[2][1] - points[3][1], bottom - top)
            stroke = float(path["stroke-width"])
            self.assertGreaterEqual(min(x for x, y in points), stroke / 2 - .01)
            self.assertGreaterEqual(min(y for x, y in points), stroke / 2 - .01)
            self.assertLessEqual(max(x for x, y in points), width - stroke / 2 + .01)
            self.assertLessEqual(max(y for x, y in points), height - stroke / 2 + .01)
        self.assertEqual(snapshot["diagnostics"].get("data-calcpad-root-fix"), "v3")
        self.assertEqual(snapshot["diagnostics"].get("data-calcpad-root-count"), str(count))

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_all_four_synthetic_layouts_enclose_one_fifth_in_both_themes(self):
        for dark in (False, True):
            for form in ("forward", "adjacent", "inverse", "inverse-marker"):
                with self.subTest(dark=dark, form=form):
                    data = self.dom(math_body(root(fraction("1", "5"), form, level=2, bar=1) + " = 0.4472135955"), dark=dark)
                    self.assert_enclosures(data["initial"], 1)
                    self.assertIn(" = 0.447", data["textAfter"])

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_root_need_not_have_eq_ancestor(self):
        for scope in ("output", "none"):
            for own_eq in (False, True):
                fixture = math_body(root(fraction("1", "5"), own_eq=own_eq), scope)
                with self.subTest(scope=scope, own_eq=own_eq):
                    self.assert_enclosures(self.dom(fixture)["initial"], 1)

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_numeric_root_levels_and_mismatched_numeric_bar_levels(self):
        for level in (0, 1, 2, 3, 12):
            for form in ("forward", "adjacent", "inverse", "inverse-marker"):
                with self.subTest(level=level, form=form):
                    self.assert_enclosures(self.dom(math_body(root("5", form, level, bar=3)))["initial"], 1)

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_nested_radicals_numerators_denominators_and_nested_fractions(self):
        cases = ((fraction(root("5", "inverse"), "2"), 1),
                 (fraction("1", root("5", "inverse-marker")), 1),
                 (root(root(fraction("1", "5"), "inverse"), "inverse-marker"), 2),
                 (root(fraction(root("5", "adjacent"), root("3", "inverse-marker")), "inverse"), 3),
                 (root(fraction("1", fraction("5", "7")), "inverse"), 1),
                 (fraction(root(fraction("1", "5"), "inverse-marker"),
                           root(fraction("3", root("7", "inverse")), "forward")), 3))
        for content, count in cases:
            with self.subTest(content=content):
                self.assert_enclosures(self.dom(math_body(content))["initial"], count)

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_superscripts_subscripts_padding_and_negative_visual_offsets(self):
        content = '<var>x</var><sup>123</sup><sub>456</sub>' + fraction("1", "5")
        fixture = math_body(root(content, padding=' data-padding="7,9,5,11"'))
        data = self.dom(fixture)
        self.assert_enclosures(data["initial"], 1)
        boxes = data["initial"]["roots"][0]["descendants"]
        self.assertTrue(any(item["tag"] == "SUP" for item in boxes))
        self.assertTrue(any("dvr" in item["classes"].split() for item in boxes))
        for tag in ("sup", "sub"):
            self.assert_enclosures(self.dom(math_body(f"<{tag}>" + root(fraction("1", "5"), "inverse") + f"</{tag}>"))["initial"], 1)

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_nth_root_degrees_are_visible_preserved_and_not_duplicated(self):
        for form in ("forward", "adjacent", "inverse", "inverse-marker"):
            with self.subTest(form=form):
                fixture = math_body(root(fraction("1", "5"), form, degree="123"))
                data = self.dom(fixture)
                self.assert_enclosures(data["initial"], 1)
                indices = with_class(data["initial"]["tree"], "cp-preview-root-index")
                self.assertEqual(len(indices), 1)
                self.assertEqual(indices[0]["children"], ["123"])
                self.assertFalse(with_class(indices[0], "cp-preview-root-marker"))

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_font_resize_zoom_load_and_repeat_redraws_coalesce_and_stabilize(self):
        fixture = math_body(root(fraction(root("1", "inverse"), '<var>x</var><sup>2</sup>'), "inverse-marker"))
        events = [{"type": "DOMContentLoaded"}, {"type": "load"}, {"type": "fontready", "fontScale": 1.25},
                  {"type": "resize", "fontScale": 1.5}, {"type": "visualresize", "scale": 1.8},
                  {"type": "loadingdone", "fontScale": .8}, {"type": "burst"},
                  {"type": "observer"}, {"type": "observer"}]
        data = self.dom(fixture, events=events)
        self.assert_enclosures(data["initial"], 2)
        for snapshot in data["events"]:
            self.assert_enclosures(snapshot, 2)
            self.assertLessEqual(snapshot["frameCount"], 1)
            self.assertLessEqual(snapshot["queued"], 1)
        self.assertEqual(data["events"][-2]["writes"], 0)
        self.assertEqual(data["events"][-1]["writes"], 0)
        self.assertNotEqual(data["initial"]["roots"][0]["svg"]["attrs"]["viewBox"],
                            data["events"][3]["roots"][0]["svg"]["attrs"]["viewBox"])

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_plain_prose_malformed_pairs_and_code_are_not_rewritten(self):
        invalid = ('<p>sqrt(1/5), r2 o2, Grüße √ a □ &amp; Ω</p>',
                   '<span class="r2-extra"><span class="o2">5</span></span>',
                   '<span class="radius"><span class="o2">5</span></span>',
                   '<span class="r2">literal a<span class="o2">5</span></span>',
                   '<span class="r2"></span>user text<span class="o2">5</span>',
                   '<span class="r2"><span class="o1">5</span><span class="o2">3</span></span>',
                   '<span class="r2"><span class="o1"> </span></span>')
        for content in invalid:
            with self.subTest(content=content):
                data = self.dom(math_body(content))
                self.assert_enclosures(data["initial"], 0)
                self.assertFalse(with_class(data["initial"]["tree"], "cp-preview-radicand"))
        for tag in ("pre", "code", "textarea", "style", "script"):
            fixture = f"<{tag}>" + root("5", "inverse") + f"</{tag}>"
            with self.subTest(tag=tag):
                self.assert_enclosures(self.dom(fixture)["initial"], 0)
        fixture = '<div contenteditable="true">' + root("5") + '</div>'
        self.assert_enclosures(self.dom(fixture)["initial"], 0)

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js unavailable: synthetic DOM geometry not executed")
    def test_visible_literal_sign_is_hidden_without_losing_source_text(self):
        fixture = math_body('<span class="r1">√<span class="o1">' + fraction("1", "5") + '</span></span>')
        data = self.dom(fixture)
        self.assert_enclosures(data["initial"], 1)
        self.assertEqual(data["textAfter"].count("√"), 1)
        self.assertEqual(len(with_class(data["initial"]["tree"], "cp-preview-root-sign")), 1)
        self.assertEqual(len(with_class(data["initial"]["tree"], "cp-preview-root-marker")), 1)

    def test_identifiable_self_contained_no_bad_escapes(self):
        source = (ROOT / "calcpad_gui/data.py").read_text(encoding="utf-8")
        self.assertIn('APP_TITLE = "CalcpadCE"', source)
        self.assertEqual(APP_TITLE, 'CalcpadCE')
        for dark in (False, True):
            page = Page(self.preview(dark=dark)._wrap_preview(""))
            self.assertIn(("meta", {"name": "generator", "content": "CalcpadCE GTK root-fix-v3"}), page.tags)
            self.assertFalse(any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in page.css))
            self.assertNotIn(r"\221a", page.css)
            self.assertFalse(any(tag in ("link", "iframe") or "src" in attrs for tag, attrs in page.tags))
            for unsafe in ("fetch(", "innerHTML", "textContent ="):
                self.assertNotIn(unsafe, page.script)
            self.assertIn('document.querySelectorAll("span")', page.script)
            self.assertNotIn('document.querySelectorAll(".eq span")', page.script)

    def test_full_emitted_html_matches_48_frozen_v3_outputs(self):
        for case in FIXTURES['preview']:
            with self.subTest(settings=case['settings']):
                preview = Preview()
                preview.settings = case['settings']
                self.assertEqual(hashlib.sha256(preview._wrap_preview(case['body']).encode()).hexdigest(), case['sha256'])

    def test_scroll_and_clickable_navigation_frozen_and_idempotent(self):
        preview = Preview()
        for case in FIXTURES['scroll']:
            self.assertEqual(hashlib.sha256(inject_output_scroll_restore(case['in']).encode()).hexdigest(), case['out_sha256'])
        for case in FIXTURES['navigation']:
            html = preview._inject_output_line_navigation(case['in'])
            self.assertEqual(hashlib.sha256(html.encode()).hexdigest(), case['out_sha256'])
            self.assertEqual(preview._inject_output_line_navigation(html), html)

    @unittest.skipUnless(shutil.which('node'), 'Optional Node.js unavailable: JS syntax not executed')
    def test_actual_extracted_root_scroll_and_navigation_javascript_syntax(self):
        preview = Preview()
        preview.settings = {'dark_preview': False}
        html = preview._inject_output_line_navigation(inject_output_scroll_restore(preview._wrap_preview('')))
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
        self.assertEqual(len(scripts), 3)
        for script in scripts:
            checked = subprocess.run([self.node, '--check'], input=script, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
