"""Frozen source provenance, resource and method/callback contracts."""
import ast
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from tests.support import ROOT, Widget, install_gi, isolated_directory
from calcpad_gui.data import APP_TITLE, DEFAULT_SETTINGS
from calcpad_gui.resource_loader import read_resource

FIXTURES = ROOT / 'tests/fixtures'
MANIFEST = json.loads((FIXTURES / 'baseline.json').read_text())
INTENTIONAL_DATA_CHANGES = {
    'APP_TITLE': ('CalcpadCE — Wurzel-Fix 3', 'CalcpadCE'),
}


def digest(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def method_node(filename, cls, name):
    tree = ast.parse(filename.read_text())
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    return next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == name)


class ResourceConstants(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'read_resource':
            return ast.Constant(value=read_resource(node.args[0].value))
        return self.generic_visit(node)


class SourceInvariants(unittest.TestCase):
    def test_only_root_app_py_exists_and_historical_module_is_intentionally_removed(self):
        self.assertEqual(sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('app.py')), ['app.py'])
        for command in ([sys.executable, '-c', 'import calcpad_gui.app'],
                        [sys.executable, '-m', 'calcpad_gui.app']):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('No module named', result.stderr)
            self.assertIn('calcpad_gui.app', result.stderr)

    def test_console_script_targets_application_main(self):
        manifest = (ROOT / 'pyproject.toml').read_text()
        self.assertIn('calcpad-gui = "calcpad_gui.application:main"', manifest)
        self.assertNotIn('"calcpad_gui.app:main"', manifest)

    def test_release_title_is_neutral_without_changing_application_id(self):
        from calcpad_gui.data import APP_ID, APP_TITLE
        self.assertEqual(APP_TITLE, 'CalcpadCE')
        self.assertEqual(APP_ID, 'org.community.calcpadce.linuxgui')
        for path in (ROOT / 'calcpad_gui').rglob('*.py'):
            self.assertNotIn('Wurzel-Fix', path.read_text(), str(path))

    def test_all_121_window_methods_signatures_descriptors_and_mechanical_bodies(self):
        self.assertEqual(len(MANIFEST['window']), 121)
        for name, record in MANIFEST['window'].items():
            with self.subTest(method=name):
                node = method_node(ROOT / 'calcpad_gui' / record['module'], record['class'], name)
                self.assertEqual([ast.unparse(d) for d in node.decorator_list], record['descriptor'])
                if record['mechanical']:
                    self.assertEqual(digest(node), record['digest'])
                elif name in MANIFEST['resource_replacements']:
                    self.assertEqual(digest(ResourceConstants().visit(copy.deepcopy(node))), record['digest'])

    def test_all_app_methods_and_top_level_function_bodies_are_unchanged(self):
        package = ROOT / 'calcpad_gui'
        for name, expected in MANIFEST['app'].items():
            self.assertEqual(digest(method_node(package / 'application.py', 'CalcpadApp', name)), expected)
        modules = {'ensure_calcpad_language': 'language.py', 'load_settings': 'config.py',
                   'save_settings': 'config.py', 'discover_cli': 'services/cli.py',
                   'inject_output_scroll_restore': 'preview/scroll.py',
                   'run_doctor': 'doctor.py', 'main': 'application.py'}
        for name, module in modules.items():
            tree = ast.parse((package / module).read_text())
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertEqual(digest(node), MANIFEST['functions'][name])

    def test_bundled_literal_resource_bytes_match_baseline(self):
        for name, expected in MANIFEST['resources'].items():
            self.assertEqual(hashlib.sha256(read_resource(name).encode()).hexdigest(), expected, name)

    def test_every_source_parses_compiles_and_has_no_runtime_exec_eval_or_star_import(self):
        for file in ROOT.rglob('*.py'):
            source = file.read_text()
            tree = ast.parse(source, filename=str(file))
            compile(source, str(file), 'exec')
            if file.is_relative_to(ROOT / 'tests'):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, ('exec', 'eval'))
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(any(alias.name == '*' for alias in node.names))

    def test_pure_modules_import_without_GI_and_resources_ignore_cwd(self):
        code = '''import os, sys
os.chdir('/')
from calcpad_gui.domain.expressions import ExpressionTransforms
from calcpad_gui.domain.numbers import NumberFormatting
from calcpad_gui.domain.docx import DocxProcessing
from calcpad_gui.preview.html import PreviewRenderer
from calcpad_gui.preview.scroll import inject_output_scroll_restore
from calcpad_gui.services.cli import discover_cli, run_cli
from calcpad_gui.config import DEFAULT_SETTINGS
from calcpad_gui.resource_loader import read_resource
assert "gi" not in sys.modules
assert read_resource("calcpad.lang").startswith("<?xml")
assert "numericSpan" in read_resource("root-fix-v3.html")
'''
        with isolated_directory() as folder:
            env = __import__('os').environ.copy()
            env['PYTHONPATH'] = str(ROOT)
            env['HOME'] = str(folder)
            result = subprocess.run([sys.executable, '-c', code], cwd=folder,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(folder.iterdir()), [])


class DesktopContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = isolated_directory()
        cls.directory = cls.context.__enter__()
        cls.gi = install_gi(cls.directory / 'cfg', cls.directory / 'data')
        cls.app = importlib.import_module('calcpad_gui.application')

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def window(self):
        window = self.app.CalcpadWindow.__new__(self.app.CalcpadWindow)
        Widget.__init__(window)
        return window

    def test_method_inventory_no_missing_duplicate_or_shadowed_callbacks(self):
        window = self.app.CalcpadWindow
        owned = {}
        for owner in window.__mro__:
            if owner.__module__.startswith('calcpad_gui'):
                for name, value in owner.__dict__.items():
                    if callable(value) or isinstance(value, (classmethod, staticmethod)):
                        self.assertNotIn(name, owned, name)
                        owned[name] = value
        self.assertEqual(set(owned), set(MANIFEST['window']))
        for name, record in MANIFEST['window'].items():
            value = inspect.getattr_static(window, name)
            if record['descriptor']:
                self.assertEqual(type(value).__name__, record['descriptor'][0])
            source = method_node(ROOT / 'calcpad_gui' / record['module'], record['class'], name)
            for node in ast.walk(source):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'connect':
                    for arg in node.args[1:2]:
                        if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name) and arg.value.id == 'self':
                            self.assertTrue(callable(getattr(window, arg.attr)), arg.attr)

    def test_window_initializer_calls_same_setup_and_connects_bound_callbacks(self):
        window = self.window()
        window.buffer = Mock()
        setups = ['_build_headerbar', '_build_layout', '_apply_app_theme', '_start_with_empty_document',
                  '_setup_zoom_controls', '_setup_line_navigation_controls', '_setup_format_controls',
                  '_setup_autocomplete_controls', '_install_shortcuts', '_setup_editor_highlighting']
        order = []
        for name in setups:
            setattr(window, name, Mock(side_effect=lambda name=name: order.append(name)))
        with patch('calcpad_gui.window.load_settings', return_value={}), \
             patch('calcpad_gui.window.discover_cli', return_value=(None, 'missing')), \
             patch('calcpad_gui.window.ensure_calcpad_language', return_value=True):
            window.__init__(Mock())
        self.assertEqual(order, setups)
        self.assertEqual(window.values['title'], 'CalcpadCE')
        self.assertEqual(window.values['title'], APP_TITLE)
        window.buffer.connect.assert_any_call('modified-changed', window._on_modified_changed)
        window.buffer.connect.assert_any_call('notify::cursor-position', window._on_editor_cursor_position_changed)
        self.assertIn(('close-request', window._on_close_request, ()), window.signals)
        self.gi.GLib.timeout_add.assert_any_call(400, window._initial_run)

    def test_release_title_refresh_preserves_filename_and_dirty_marker(self):
        window = self.window()
        window.buffer = Mock()
        window.set_title = Mock()
        for filename, label in ((None, '[Untitled]'), ('worksheets/example.cpd', 'example.cpd')):
            for dirty, prefix in ((False, ''), (True, '• ')):
                with self.subTest(filename=filename, dirty=dirty):
                    window.current_file = filename
                    window.buffer.get_modified.return_value = dirty
                    window._refresh_title()
                    title = window.set_title.call_args.args[0]
                    self.assertEqual(title, f'{prefix}{label} - {APP_TITLE}')
                    self.assertEqual(title, f'{prefix}{label} - CalcpadCE')
                    self.assertNotIn('Wurzel-Fix', title)

    def test_new_document_title_uses_neutral_branding(self):
        window = self.window()
        window.buffer = Mock()
        window.buffer.set_modified.side_effect = lambda value: setattr(window.buffer.get_modified, 'return_value', value)
        window.set_title = Mock()
        window.on_run = Mock()
        window.current_file = 'previous.cpd'
        window._do_new()
        self.assertIsNone(window.current_file)
        window.buffer.set_modified.assert_called_once_with(False)
        window.set_title.assert_called_once_with('[Untitled] - CalcpadCE')
        window.on_run.assert_called_once_with(None)

    def test_headerbar_registers_export_actions_and_original_buttons(self):
        window = self.window()
        window.settings = dict(DEFAULT_SETTINGS)
        window._refresh_recent_menu = Mock()
        Widget.widgets.clear()
        window._build_headerbar()
        self.assertEqual(set(window.actions), {'export_html', 'export_pdf', 'export_docx', 'export_docx_as'})
        bound = [cb.__name__ for widget in Widget.widgets for _, cb, _ in widget.signals
                 if inspect.ismethod(cb) and cb.__self__ is window]
        for callback in ('on_new', 'on_open', 'on_save', 'on_save_as', 'on_run', '_format_current_line', '_on_toggle'):
            self.assertIn(callback, bound)
        with patch.object(window, '_quick_export_docx') as quick, patch.object(window, '_export') as export:
            for action, fmt in [('export_html', 'html'), ('export_pdf', 'pdf'), ('export_docx_as', 'docx')]:
                window.actions[action].signals[0][1](None, None)
                export.assert_called_with(fmt)
            window.actions['export_docx'].signals[0][1](None, None)
            quick.assert_called_once_with()

    def test_root_and_package_entrypoints_with_test_only_gi(self):
        code = '''from tests.support import install_gi, isolated_directory
import runpy, sys
with isolated_directory() as d:
    install_gi(d / 'config', d / 'data')
    target = sys.argv[1]
    sys.argv = [target, 'sample.cpd']
    if target.endswith('.py'):
        runpy.run_path(target, run_name='__main__')
    else:
        runpy.run_module(target, run_name='__main__', alter_sys=True)
'''
        for target in (str(ROOT / 'app.py'), 'calcpad_gui'):
            result = subprocess.run([sys.executable, '-c', code, target], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('TEST_GI_RUN', result.stdout)
            self.assertIn('sample.cpd', result.stdout)

    def test_cli_wrapper_preserves_lazy_source_escape_and_return_contract(self):
        window = self.window()
        window._cli_cmd, window._cli_hint = ['CalcpadCli'], 'hint'
        window._get_text_for_cli = Mock(return_value='x=1')
        window.settings = {'decimal_places': 4}
        with patch('calcpad_gui.ui.calculation.run_cli', return_value=('file', None)) as run:
            self.assertEqual(window._run_cli('html', True, 'explicit'), ('file', None))
            args = run.call_args.args
            self.assertEqual(args[:4], (['CalcpadCli'], 'hint', 'html', True))
            self.assertEqual(args[4](), '#round 4\nx=1')
            self.assertEqual(args[5], window._wrap_preview)
            self.assertEqual(args[6], self.gi.GLib.markup_escape_text)
            self.assertEqual(args[7], 'explicit')

class AdditionalSourceInvariants(unittest.TestCase):
    def test_every_window_signature_including_adapted_methods_is_unchanged(self):
        for name, record in MANIFEST['window'].items():
            node = method_node(ROOT / 'calcpad_gui' / record['module'], record['class'], name)
            self.assertEqual(digest(node.args), record['signature_digest'], name)

    def test_pure_cli_body_is_a_mechanical_parameterized_extraction(self):
        tree = ast.parse((ROOT / 'calcpad_gui/services/cli.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_cli')
        self.assertEqual(digest(ast.Module(body=node.body, type_ignores=[])), MANIFEST['cli_service_body_digest'])

    def test_data_only_allowlisted_title_change_and_desktop_version_gate(self):
        tree = ast.parse((ROOT / 'calcpad_gui/data.py').read_text())
        nodes = {n.targets[0].id: n for n in tree.body if isinstance(n, ast.Assign)}
        changed = {name for name, expected in MANIFEST['data_digests'].items()
                   if digest(nodes[name]) != expected}
        self.assertEqual(changed, set(INTENTIONAL_DATA_CHANGES))
        for name, expected in MANIFEST['data_digests'].items():
            node = copy.deepcopy(nodes[name])
            if name in INTENTIONAL_DATA_CHANGES:
                original, release = INTENTIONAL_DATA_CHANGES[name]
                self.assertEqual(ast.literal_eval(node.value), release, name)
                node.value = ast.Constant(value=original)
            self.assertEqual(digest(node), expected, name)
        tree = ast.parse((ROOT / 'calcpad_gui/bootstrap.py').read_text())
        start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Import) and n.names[0].name == 'gi')
        self.assertEqual(digest(ast.Module(body=tree.body[start:], type_ignores=[])), MANIFEST['desktop_version_gate_digest'])

    def test_existing_asset_roots_and_svg_png_priority(self):
        from calcpad_gui import assets
        with isolated_directory() as directory:
            project = directory / 'project'
            package = project / 'calcpad_gui'
            package.mkdir(parents=True)
            (project / 'assets').mkdir()
            (directory / 'assets').mkdir()
            png = project / 'assets/calcpadce-logo.png'
            svg = project / 'assets/calcpadce-logo.svg'
            legacy = directory / 'assets/calcpadce-logo.svg'
            with patch.object(assets, '__file__', str(package / 'assets.py')):
                self.assertIsNone(assets.find_logo())
                legacy.write_text('legacy')
                self.assertEqual(assets.find_logo(), legacy)
                png.write_bytes(b'png')
                self.assertEqual(assets.find_logo(), png)
                svg.write_text('svg')
                self.assertEqual(assets.find_logo(), svg)
                self.assertEqual(legacy.read_text(), 'legacy')
