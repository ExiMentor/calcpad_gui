"""Pure transformations and archive preservation with frozen baseline outputs."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import zipfile

from calcpad_gui import config
from calcpad_gui.domain.docx import DocxProcessing
from calcpad_gui.domain.expressions import ExpressionTransforms
from calcpad_gui.domain.numbers import NumberFormatting
from calcpad_gui.preview.html import PreviewRenderer
from tests.support import ROOT, isolated_directory

FIXTURES = json.loads((ROOT / 'tests/fixtures/outputs.json').read_text())


class PureBehavior(ExpressionTransforms, NumberFormatting, PreviewRenderer, DocxProcessing):
    pass


class ExpressionTests(unittest.TestCase):
    def setUp(self):
        self.domain = PureBehavior()

    def test_normalization_parallel_unicode_micro_and_comments_frozen(self):
        for case in FIXTURES['normalization']:
            self.assertEqual(self.domain._normalize(case['in']), case['out'])

    def test_formatting_and_comment_preservation_frozen(self):
        for case in FIXTURES['formatting']:
            self.assertEqual(self.domain._format_calcpad_line(case['in']), case['out'])

    def test_recursive_parallel_classmethod_dispatch_is_overridable(self):
        class Custom(ExpressionTransforms):
            seen = []

            @classmethod
            def _parallel_resistance_expression(cls, expression):
                cls.seen.append(expression)
                return super()._parallel_resistance_expression(expression)
        self.assertEqual(Custom._expand_parallel_resistors('R = (A || B) || C'),
                         'R = 1 / (1 / ((1 / (1 / (A) + 1 / (B)))) + 1 / (C))')
        self.assertIn('A', Custom.seen)
        self.assertIn('C', Custom.seen)

    def test_precision_limits_and_invalid_settings(self):
        for raw, expected in [(-1, 0), (20, 15), (None, 3), ('oops', 3), ('4', 4)]:
            self.domain.settings = {'decimal_places': raw}
            self.assertEqual(self.domain._code_with_decimal_places('x=1'), f'#round {expected}\nx=1')

    def test_html_decimal_conversion_never_touches_tag_attributes(self):
        html = '<span style="width:1.25em" data-n="2.34">-1.25 &lt; 3.45</span>'
        self.assertEqual(self.domain._apply_decimal_comma_html(html),
                         '<span style="width:1.25em" data-n="2.34">-1,25 &lt; 3,45</span>')
        self.domain.settings = {'decimal_places': 2, 'decimal_comma': True}
        self.assertEqual(self.domain._format_preview_numbers(html),
                         '<span style="width:1.25em" data-n="2.34">-1,25 &lt; 3,45</span>')

    def test_custom_unicode_replacements_are_preserved(self):
        self.domain._UNICODE_FIX = {'×': '*'}
        self.assertEqual(self.domain._normalize('2×3'), '2*3')


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.context = isolated_directory()
        self.folder = self.context.__enter__()
        self.patches = [patch.object(config, name, self.folder / value) for name, value in
                        [('CFG_DIR', 'cfg'), ('CFG_FILE', 'cfg/settings.json'),
                         ('LANG_DIR', 'lang'), ('LANG_FILE', 'lang/calcpad.lang')]]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.context.__exit__(None, None, None)

    def test_schema_defaults_and_missing_file(self):
        settings = config.load_settings()
        self.assertEqual(settings, config.DEFAULT_SETTINGS)
        self.assertEqual(settings['schema'], 1)
        self.assertEqual(settings['decimal_places'], 3)
        self.assertEqual(set(settings), {'recent', 'dark_preview', 'auto_refresh', 'last_dir', 'schema',
                                         'decimal_comma', 'decimal_places', 'keyboard_favorites', 'keyboard_visible'})
        self.assertFalse(config.CFG_DIR.exists())

    def test_load_merges_known_keys_only_and_roundtrips(self):
        config.CFG_DIR.mkdir()
        config.CFG_FILE.write_text(json.dumps({'dark_preview': True, 'schema': 1,
            'decimal_places': 7, 'keyboard_favorites': [{'label': 'Ω', 'action': 'Ω'}], 'unknown': 42}))
        settings = config.load_settings()
        self.assertTrue(settings['dark_preview'])
        self.assertEqual(settings['decimal_places'], 7)
        self.assertNotIn('unknown', settings)
        config.save_settings(settings)
        self.assertEqual(config.load_settings(), settings)

    def test_bad_json_non_dict_and_io_failures_retain_defaults(self):
        config.CFG_DIR.mkdir()
        for content in ('[1,2]', '{invalid', 'null'):
            config.CFG_FILE.write_text(content)
            self.assertEqual(config.load_settings(), config.DEFAULT_SETTINGS)
        with patch.object(Path, 'read_text', side_effect=OSError('denied')):
            self.assertEqual(config.load_settings(), config.DEFAULT_SETTINGS)
        with patch.object(Path, 'write_text', side_effect=OSError('denied')):
            config.save_settings({'recent': []})

    def test_glib_paths_initialization_keeps_historical_locations(self):
        config.initialize_paths(str(self.folder / 'config'), str(self.folder / 'data'))
        self.assertEqual(config.CFG_FILE, self.folder / 'config/calcpad-gui/settings.json')
        self.assertEqual(config.LANG_FILE, self.folder / 'data/gtksourceview-5/language-specs/calcpad.lang')
        self.assertTrue(config.CFG_DIR.is_dir())
        self.assertTrue(config.LANG_DIR.is_dir())


class DocxTests(unittest.TestCase):
    def setUp(self):
        self.domain = PureBehavior()

    def test_frozen_omml_units_colors_decimals_and_non_math_runs(self):
        for case in FIXTURES['ooxml']:
            data = case['in'].encode()
            self.assertEqual(self.domain._process_ooxml_formula_runs(data, case['comma']),
                             case['out'].encode())

    def test_zip_preserves_parts_metadata_omml_and_cleans_staging_file(self):
        with isolated_directory() as directory:
            path = directory / 'formula.docx'
            original = b'<m:oMath><m:r><m:t>1.25</m:t></m:r><m:r><m:t>V</m:t></m:r></m:oMath>'
            item = zipfile.ZipInfo('word/document.xml', (2020, 1, 2, 3, 4, 6))
            item.external_attr = 0o600 << 16
            untouched = {'[Content_Types].xml': b'<Types/>', 'word/media/picture.png': b'PNG\x00',
                         'customXml/item.xml': b'<m:r><m:t>1.25</m:t></m:r>'}
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(item, original)
                for name, data in untouched.items():
                    archive.writestr(name, data)
            self.domain._postprocess_docx(str(path), True)
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(set(archive.namelist()), set(untouched) | {'word/document.xml'})
                for name, data in untouched.items():
                    self.assertEqual(archive.read(name), data)
                result = archive.read(item.filename)
                self.assertIn(b'<m:oMath>', result)
                self.assertIn(b'1,25', result)
                self.assertIn(b'<w:color w:val="119911" />', result)
                stored = archive.getinfo(item.filename)
                self.assertEqual(stored.date_time, item.date_time)
                self.assertEqual(stored.external_attr, item.external_attr)
            self.assertFalse(Path(str(path) + '.tmp').exists())
            self.domain._apply_decimal_comma_docx(str(path))

    def test_postprocess_failure_preserves_original_and_removes_staging(self):
        with isolated_directory() as directory:
            path = directory / 'formula.docx'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml', '<m:r><m:t>1.25</m:t></m:r>')
            original = path.read_bytes()
            with patch.object(self.domain, '_process_ooxml_formula_runs', side_effect=ValueError('bad data')):
                with self.assertRaises(ValueError):
                    self.domain._postprocess_docx(str(path), True)
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(Path(str(path) + '.tmp').exists())
