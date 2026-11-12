"""Filesystem, callbacks and mainloop/worker contracts using test-only GI.

No assertion here establishes actual GTK/WebKit layout or desktop integration.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests.support import ROOT, Widget, install_gi, isolated_directory
from calcpad_gui.data import DEFAULT_SETTINGS


class UiContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = isolated_directory()
        cls.directory = cls.context.__enter__()
        if 'calcpad_gui.bootstrap' not in sys.modules:
            install_gi(cls.directory / 'config', cls.directory / 'data')
        cls.app = importlib.import_module('calcpad_gui.application')
        cls.bootstrap = importlib.import_module('calcpad_gui.bootstrap')

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def setUp(self):
        self.local = isolated_directory()
        self.folder = self.local.__enter__()
        self.window = self.app.CalcpadWindow.__new__(self.app.CalcpadWindow)
        Widget.__init__(self.window)
        self.window.settings = copy.deepcopy(DEFAULT_SETTINGS)
        self.window.current_file = None
        self.window.buffer = Mock()
        self.window.webview = Mock()
        self.window.set_status = Mock()
        self.window._refresh_recent_menu = Mock()
        self.window._refresh_title = Mock()
        self.window.on_run = Mock()
        self.window._closing = False
        self.window._run_busy = False
        self.window._quick_docx_busy = False
        self.queue = []
        self.idle = patch.object(self.bootstrap.GLib, 'idle_add', side_effect=lambda callback, *args: self.queue.append((callback, args)))
        self.idle.start()
        self.config = importlib.import_module('calcpad_gui.config')
        self.config_patch = patch.object(self.config, 'CFG_FILE', self.folder / 'settings.json')
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.idle.stop()
        self.local.__exit__(None, None, None)

    def flush(self):
        while self.queue:
            callback, args = self.queue.pop(0)
            callback(*args)

    def immediate_thread(self, target, daemon):
        self.assertTrue(daemon)
        return SimpleNamespace(start=target)

    def test_recent_list_deduplicates_caps_persists_and_refreshes(self):
        self.window.settings['recent'] = [f'/test/{i}.cpd' for i in range(12)]
        self.window._add_recent('/test/5.cpd')
        recent = self.window.settings['recent']
        self.assertEqual(recent[0], '/test/5.cpd')
        self.assertEqual(len(recent), 10)
        self.assertEqual(recent.count('/test/5.cpd'), 1)
        self.assertEqual(json.loads(self.config.CFG_FILE.read_text())['recent'], recent)
        self.window._clear_recent()
        self.assertEqual(self.window.settings['recent'], [])
        self.window._refresh_recent_menu.assert_called()

    def test_favorites_clean_toggle_refresh_persist_and_row_size(self):
        self.window.settings['keyboard_favorites'] = [None, {}, {'label': 'Ω', 'action': 'Ω'},
            {'label': 'Ω', 'action': 'Ω'}, {'label': 'empty', 'action': ''}]
        self.assertEqual(self.window._get_keyboard_favorites(), [{'label': 'Ω', 'action': 'Ω'}])
        self.window._refresh_keyboard_favorites_page = Mock()
        button = SimpleNamespace(_favorite_label='Ω', _favorite_action='Ω')
        self.window._toggle_keyboard_favorite(button)
        self.assertEqual(self.window.settings['keyboard_favorites'], [])
        self.window._toggle_keyboard_favorite(button)
        self.assertEqual(self.window.settings['keyboard_favorites'], [{'label': 'Ω', 'action': 'Ω'}])
        self.window._refresh_keyboard_favorites_page.assert_called()
        self.window.settings['keyboard_favorites'] = [{'label': str(i), 'action': str(i)} for i in range(23)]
        self.assertEqual([len(row) for row in self.window._get_keyboard_favorite_rows()], [10, 10, 3])

    def test_options_persist_and_trigger_original_actions(self):
        button = Mock(); button.get_active.return_value = True
        self.window._apply_app_theme = Mock()
        self.window._on_toggle(button, 'dark_preview')
        self.window._apply_app_theme.assert_called_once_with()
        self.window._keyboard_revealer = Mock()
        self.window._on_keyboard_visible_toggled(button)
        self.window._keyboard_revealer.set_reveal_child.assert_called_once_with(True)
        spin = Mock(); spin.get_value.return_value = 6
        self.window._on_decimal_places_changed(spin)
        self.assertEqual(self.window.settings['decimal_places'], 6)
        self.window.on_run.assert_called_with(None)
        self.assertTrue(json.loads(self.config.CFG_FILE.read_text())['dark_preview'])

    def test_save_uses_raw_editor_not_normalized_cli_and_failure_keeps_dirty(self):
        target = self.folder / 'worksheet.cpd'
        self.window.current_file = str(target)
        self.window._get_buffer_text = Mock(return_value='C = 1 µF\nx = R1 || R2\nx₂=2²')
        self.window._get_text_for_cli = Mock(side_effect=AssertionError('must not normalize saved file'))
        done = Mock()
        self.window.on_save(None, done)
        self.assertEqual(target.read_text(), 'C = 1 µF\nx = R1 || R2\nx₂=2²')
        self.window.buffer.set_modified.assert_called_once_with(False)
        done.assert_called_once_with(True)
        self.window.buffer.reset_mock(); done.reset_mock()
        with patch.object(Path, 'write_text', side_effect=OSError('denied')):
            self.window.on_save(None, done)
        done.assert_called_once_with(False)
        self.window.buffer.set_modified.assert_not_called()
        self.assertIn('Save failed:', self.window.set_status.call_args.args[0])

    def test_save_as_cancellation_success_and_error_callback_contract(self):
        dialog = Mock(); done = Mock()
        target = self.folder / 'saved.cpd'
        dialog.save_finish.return_value.get_path.return_value = str(target)
        self.window._get_buffer_text = Mock(return_value='raw µF')
        self.window._save_done(dialog, None, done)
        self.assertEqual(target.read_text(), 'raw µF')
        self.assertEqual(self.window.current_file, str(target))
        done.assert_called_with(True)
        for error in (self.bootstrap.GLib.Error('cancelled'), OSError('denied')):
            done.reset_mock()
            dialog.save_finish.side_effect = error
            self.window._save_done(dialog, None, done)
            done.assert_called_once_with(False)

    def test_open_and_close_dirty_gates_and_failed_read_do_not_discard(self):
        self.window.is_dirty = Mock(return_value=True)
        self.window._confirm_discard = Mock()
        self.window._open_path = Mock()
        self.window.open_file_path('worksheet.cpd')
        gate = self.window._confirm_discard.call_args.args[0]
        gate(False); self.window._open_path.assert_not_called()
        gate(True); self.window._open_path.assert_called_once_with('worksheet.cpd')
        dialog = Mock()
        with patch.object(self.bootstrap.Gtk, 'AlertDialog', return_value=dialog):
            self.assertTrue(self.window._on_close_request(None))
            dialog.set_buttons.assert_called_once_with(['Discard', 'Cancel', 'Save'])
            dialog.choose.assert_called_once_with(self.window, None, self.window._on_close_response)
        dialog.choose_finish.return_value = 1
        self.window._on_close_response(dialog, None)
        self.assertFalse(self.window._closing)
        with patch.object(self.window, 'on_save') as save:
            dialog.choose_finish.return_value = 2
            self.window._on_close_response(dialog, None)
            save.assert_called_once_with(None, _on_done=self.window._close_after_save)
        self.window._close_after_save(False)
        self.assertFalse(self.window._closing)
        self.window.close = Mock()
        self.window._close_after_save(True)
        self.assertTrue(self.window._closing); self.window.close.assert_called_once_with()

    def test_open_success_and_read_failure_preserve_editor_and_state(self):
        path = self.folder / 'source.cpd'; path.write_text('C=1 µF')
        self.window._open_path(str(path))
        self.window.buffer.set_text.assert_called_once_with('C=1 µF')
        self.window.buffer.set_modified.assert_called_once_with(False)
        self.assertEqual(self.window.current_file, str(path))
        self.window.on_run.assert_called_once_with(None)
        self.window.buffer.reset_mock()
        self.window._open_path(str(self.folder / 'missing.cpd'))
        self.window.buffer.set_text.assert_not_called()
        self.assertEqual(self.window.current_file, str(path))

    def test_new_window_gtk_launch_and_module_fallback(self):
        with patch('calcpad_gui.ui.files.subprocess.Popen') as process:
            self.window.on_new()
            process.assert_called_once_with(['gtk-launch', 'calcpad-gui'])
        with patch('calcpad_gui.ui.files.subprocess.Popen', side_effect=[OSError('no desktop launcher'), Mock()]) as process:
            self.window.on_new()
            self.assertEqual(process.call_args.args[0], [sys.executable, '-m', 'calcpad_gui'])

    def test_quick_docx_names_exclusive_under_concurrent_reservations(self):
        with patch.object(self.bootstrap.GLib, 'get_user_special_dir', return_value=str(self.folder)):
            export_dir = self.folder / 'Calcpad Exports'; export_dir.mkdir()
            original = export_dir / 'worksheet_9.docx'; original.write_bytes(b'existing')
            (export_dir / 'worksheet_notes.docx').write_bytes(b'unrelated')
            with ThreadPoolExecutor(max_workers=6) as executor:
                paths = list(executor.map(lambda _: self.window._reserve_quick_docx(), range(12)))
            self.assertEqual(len(set(paths)), 12)
            self.assertEqual(original.read_bytes(), b'existing')
            self.assertTrue(all(path.exists() and path.stat().st_size == 0 for path in paths))
            self.assertTrue(all(int(path.stem.split('_')[1]) > 9 for path in paths))

    def test_quick_export_worker_success_and_mainloop_open(self):
        output = self.folder / 'calculated.docx'; output.write_bytes(b'docx fixture')
        target = self.folder / 'reserved.docx'; target.touch()
        self.window._reserve_quick_docx = Mock(return_value=target)
        self.window._get_text_for_cli = Mock(return_value='x=1')
        self.window._run_cli = Mock(return_value=(str(output), None))
        self.window._postprocess_docx = Mock()
        self.window._open_quick_docx = Mock()
        with patch('calcpad_gui.ui.exports.threading.Thread', side_effect=self.immediate_thread):
            self.window._quick_export_docx()
        self.window._run_cli.assert_called_once_with('docx', body_only=False, source_text='#round 3\nx=1')
        self.assertTrue(self.window._quick_docx_busy)
        self.assertEqual(target.read_bytes(), b'docx fixture')
        self.assertFalse(output.exists())
        self.window._open_quick_docx.assert_not_called()
        self.flush()
        self.assertFalse(self.window._quick_docx_busy)
        self.window._open_quick_docx.assert_called_once_with(target)

    def test_quick_export_errors_release_reservations_and_busy_state(self):
        for thread_failure in (False, True):
            target = self.folder / 'reserved.docx'; target.touch()
            self.window._reserve_quick_docx = Mock(return_value=target)
            self.window._get_text_for_cli = Mock(return_value='x=1')
            self.window._run_cli = Mock(return_value=(None, 'error'))
            effect = OSError('cannot start') if thread_failure else self.immediate_thread
            with patch('calcpad_gui.ui.exports.threading.Thread', side_effect=effect):
                self.window._quick_export_docx()
            self.flush()
            self.assertFalse(target.exists())
            self.assertFalse(self.window._quick_docx_busy)

    def test_quick_docx_open_prefers_native_then_desktop_association(self):
        target = self.folder / 'file.docx'
        with patch('calcpad_gui.ui.exports.shutil.which', side_effect=[None, '/bin/desktopeditors']), \
             patch('calcpad_gui.ui.exports.subprocess.Popen') as process:
            self.window._open_quick_docx(target)
            process.assert_called_once_with(['/bin/desktopeditors', str(target)])
        with patch('calcpad_gui.ui.exports.shutil.which', return_value=None), \
             patch.object(self.bootstrap.Gio.AppInfo, 'launch_default_for_uri') as launch:
            self.window._open_quick_docx(target)
            launch.assert_called_once_with(target.resolve().as_uri(), None)

    def test_standard_html_pdf_docx_exports_remain_format_specific_and_mainloop_dispatched(self):
        self.window._postprocess_docx = Mock()
        self.window.settings['decimal_comma'] = True
        for extension, data, expected in [('html', b'<p data-n="1.25">1.25</p>', b'<p data-n="1.25">1,25</p>'),
                                           ('pdf', b'PDF 1.25', b'PDF 1.25'), ('docx', b'DOCX fixture', b'DOCX fixture')]:
            with self.subTest(extension=extension):
                output = self.folder / ('source.' + extension); output.write_bytes(data)
                target = self.folder / ('target.' + extension)
                dialog = Mock(); dialog.save_finish.return_value.get_path.return_value = str(target)
                self.window._run_cli = Mock(return_value=(str(output), None))
                with patch('calcpad_gui.ui.exports.threading.Thread', side_effect=self.immediate_thread):
                    self.window._export_done(dialog, None, extension)
                self.assertFalse(target.exists())
                self.flush()
                self.assertEqual(target.read_bytes(), expected)
                self.assertFalse(output.exists())
                if extension == 'docx':
                    self.window._postprocess_docx.assert_called_once_with(str(target), True)

    def test_calculation_thread_finish_dispatch_output_cleanup_and_busy_guards(self):
        del self.window.on_run
        self.window._run_cli = Mock(return_value=('out', None))
        self.window._finish_run = Mock(return_value=False)
        with patch('calcpad_gui.ui.calculation.threading.Thread', side_effect=self.immediate_thread) as thread:
            self.window.on_run(None)
            self.assertTrue(self.window._run_busy)
            self.window._finish_run.assert_not_called()
            self.window.on_run(None)
            thread.assert_called_once()
        self.flush()
        self.window._finish_run.assert_called_once_with('out', None)
        self.window._closing = True; self.window._run_busy = False
        with patch('calcpad_gui.ui.calculation.threading.Thread') as thread:
            self.window.on_run(None)
            thread.assert_not_called()

    def test_finish_run_cleanup_success_read_error_error_and_closing(self):
        self.window._load_preview_preserving_scroll = Mock()
        for mode in ('success', 'error', 'missing', 'closing'):
            output = self.folder / 'preview.html'
            if mode != 'missing': output.write_text('<p>1.25</p>')
            self.window._run_busy = True
            self.window._closing = mode == 'closing'
            self.assertFalse(self.window._finish_run(str(output), 'error' if mode == 'error' else None))
            self.assertFalse(output.exists())
            self.assertFalse(self.window._run_busy)
        self.window._load_preview_preserving_scroll.assert_called_once()

    def test_preview_bridge_scroll_click_navigation_and_js_fallback(self):
        webview = Mock(); webview.get_title.return_value = '__calcpad_scroll__:123'
        self.window._on_preview_title_changed(webview, None)
        self.assertEqual(self.window._preview_scroll_y, 123.0)
        self.window._jump_editor_to_line = Mock()
        webview.get_title.return_value = '__calcpad_jump__:7'
        self.window._on_preview_title_changed(webview, None)
        self.window._jump_editor_to_line.assert_called_once_with(7)
        self.window._load_preview_preserving_scroll('<body>x</body>', 'file:///')
        html, base = self.window.webview.load_html.call_args.args
        self.assertEqual(base, 'file:///')
        self.assertIn('const initialY = 123.0;', html)
        self.assertIn('calcpad-clickable-line-script', html)
        if shutil.which('node'):
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
            self.assertEqual(len(scripts), 2)
            for script in scripts:
                result = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
        callback = Mock()
        self.window.webview.evaluate_javascript.side_effect = TypeError('older API')
        self.window._eval_webview_js('x()', callback)
        self.window.webview.run_javascript.assert_called_once_with('x()', None, callback, None)
        self.window._eval_webview_js = Mock()
        self.window._on_preview_load_changed(webview, SimpleNamespace(value_nick='finished'))
        self.assertIn('const y = 123.0;', self.window._eval_webview_js.call_args.args[0])

    def test_autocomplete_completion_case_dedup_and_exact_name_suppression(self):
        self.window._autocomplete_items = ['sin(', 'asin(', 'SIN(', 'sqrt(', 'I_spark_permitted']
        self.window._get_document_symbols_above_cursor = Mock(return_value=['I_spark', 'I_spark', 'sin('])
        self.assertEqual(self.window._get_autocomplete_suggestions('si'), ['sin(', 'asin('])
        self.assertEqual(self.window._get_autocomplete_suggestions('I_spark'), [])
        self.assertEqual(self.window._get_autocomplete_suggestions('I_'), ['I_spark', 'I_spark_permitted'])

    def test_language_resource_never_overwrites_existing_user_language(self):
        language = importlib.import_module('calcpad_gui.language')
        directory = self.folder / 'language'; directory.mkdir()
        target = directory / 'calcpad.lang'
        manager = Mock(); manager.get_search_path.return_value = ['/other/language']
        manager.get_language.return_value = object()
        with patch.object(language, 'LANG_DIR', directory), patch.object(language, 'LANG_FILE', target), \
             patch.object(language.GtkSource.LanguageManager, 'get_default', return_value=manager):
            self.assertTrue(language.ensure_calcpad_language())
            self.assertEqual(target.read_bytes(), language.CALCPAD_LANG.encode())
            manager.set_search_path.assert_called_once_with([str(directory), '/other/language'])
            target.write_text('custom language')
            self.assertTrue(language.ensure_calcpad_language())
            self.assertEqual(target.read_text(), 'custom language')

    def test_doctor_roundtrip_is_isolated_and_uses_30s_timeout(self):
        doctor = importlib.import_module('calcpad_gui.doctor')
        import tempfile
        def process(command, **kwargs):
            self.assertEqual(kwargs['timeout'], 30)
            self.assertEqual(command[-2:], ['-s', '-b'])
            self.assertEqual(kwargs['env']['DOTNET_CLI_UI_LANGUAGE'], 'en')
            Path(command[2]).write_text('<p>42</p>')
            return SimpleNamespace(returncode=0, stderr='')
        with patch.object(tempfile, 'tempdir', str(self.folder)), \
             patch.object(doctor, 'discover_cli', return_value=(['fake-cli'], 'test')), \
             patch.object(doctor.subprocess, 'run', side_effect=process), patch('builtins.print'):
            self.assertEqual(doctor.run_doctor(), 0)
        self.assertEqual(list(self.folder.iterdir()), [])
