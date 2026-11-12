"""CLI discovery/invocation via process doubles; no real Calcpad required."""
import html
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from calcpad_gui.services import cli
from tests.support import isolated_directory


class CliTests(unittest.TestCase):
    def setUp(self):
        self.context = isolated_directory()
        self.directory = self.context.__enter__()
        self.temp = patch.object(tempfile, 'tempdir', str(self.directory))
        self.temp.start()

    def tearDown(self):
        self.temp.stop()
        self.context.__exit__(None, None, None)

    def run_cli(self, fmt='html', body=True, source=None):
        return cli.run_cli(['calcpad', '--existing'], '<missing>', fmt, body,
                           lambda: '#round 3\nx=1', lambda s: 'WRAP:' + s,
                           html.escape, source)

    def test_environment_dll_binary_and_invalid_override_fallthrough(self):
        dll = self.directory / 'Cli.DLL'; dll.write_text('test')
        with patch.dict(os.environ, {'CALCPAD_CLI': str(dll)}):
            self.assertEqual(cli.discover_cli()[0], ['dotnet', str(dll)])
        binary = self.directory / 'custom'; binary.write_text('test'); binary.chmod(0o700)
        with patch.dict(os.environ, {'CALCPAD_CLI': str(binary)}):
            self.assertEqual(cli.discover_cli()[0], [str(binary)])
        with patch.dict(os.environ, {'CALCPAD_CLI': str(self.directory / 'missing')}), \
             patch.object(cli.shutil, 'which', return_value='/test/calcpad') as which:
            self.assertEqual(cli.discover_cli()[0], ['/test/calcpad'])
            which.assert_called_once_with('CalcpadCli')

    def test_path_alias_order_system_dll_local_build_and_missing_hint(self):
        with patch.dict(os.environ, {'CALCPAD_CLI': ''}), patch.object(cli.shutil, 'which', side_effect=[None, '/bin/fake']) as which:
            self.assertEqual(cli.discover_cli()[0], ['/bin/fake'])
            self.assertEqual([call.args[0] for call in which.call_args_list], ['CalcpadCli', 'calcpad-cli'])
        with patch.dict(os.environ, {'CALCPAD_CLI': ''}), patch.object(cli.shutil, 'which', return_value=None), \
             patch.object(Path, 'is_file', lambda p: str(p) == '/opt/CalcpadCE/Cli.dll'):
            self.assertEqual(cli.discover_cli()[0], ['dotnet', '/opt/CalcpadCE/Cli.dll'])
        local = self.directory / 'CalcpadCE/Calcpad.Cli/bin/Release/net9.0/Cli.dll'
        local.parent.mkdir(parents=True); local.write_text('test')
        with patch.dict(os.environ, {'CALCPAD_CLI': ''}), patch.object(cli.shutil, 'which', return_value=None), \
             patch.object(Path, 'home', return_value=self.directory):
            self.assertEqual(cli.discover_cli()[0], ['dotnet', str(local)])
            local.unlink()
            command, hint = cli.discover_cli()
            self.assertIsNone(command)
            self.assertIn('CalcpadCli not found.', hint)

    def test_success_argument_order_body_flag_env_source_and_input_cleanup(self):
        observed = []
        def process(args, **kwargs):
            observed.append((args, kwargs, Path(args[2]).read_text()))
            Path(args[3]).write_text('<p>42</p>')
            return SimpleNamespace(returncode=0, stderr='', stdout='')
        for fmt, body, expected_flag in [('html', True, True), ('htm', True, True),
                                          ('html', False, False), ('docx', True, False), ('pdf', False, False)]:
            with self.subTest(format=fmt, body=body), patch.object(cli.subprocess, 'run', side_effect=process):
                out, err = self.run_cli(fmt, body, 'explicit μF')
                args, kwargs, source = observed[-1]
                self.assertEqual(args[:2], ['calcpad', '--existing'])
                self.assertEqual(args[4:], ['-s', '-b'] if expected_flag else ['-s'])
                self.assertEqual(source, 'explicit μF')
                self.assertEqual(kwargs['timeout'], 60)
                self.assertEqual(kwargs['env']['DOTNET_CLI_UI_LANGUAGE'], 'en')
                self.assertTrue(kwargs['capture_output'] and kwargs['text'])
                self.assertFalse(Path(args[2]).exists())
                self.assertIsNone(err)
                self.assertEqual(Path(out).read_text(), '<p>42</p>')
                Path(out).unlink()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_missing_cli_does_not_evaluate_source_or_start_process(self):
        source, process = Mock(), Mock()
        with patch.object(cli.subprocess, 'run', process):
            out, error = cli.run_cli(None, '<missing>', 'html', True, source, lambda s: s, html.escape)
        self.assertIsNone(out)
        self.assertIn('&lt;missing&gt;', error)
        source.assert_not_called(); process.assert_not_called()

    def test_cli_errors_timeout_and_oserror_cleanup_inputs(self):
        errors = [SimpleNamespace(returncode=2, stderr='<bad>', stdout='details'),
                  SimpleNamespace(returncode=0, stderr='', stdout=''),
                  subprocess.TimeoutExpired('cli', 60), OSError('<denied>')]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                kwargs = {'side_effect': error} if isinstance(error, Exception) else {'return_value': error}
                with patch.object(cli.subprocess, 'run', **kwargs):
                    out, message = self.run_cli()
                self.assertIsNone(out)
                self.assertTrue(message.startswith('WRAP:'))
                self.assertNotIn('<bad>', message)
                self.assertNotIn('<denied>', message)
                if isinstance(error, subprocess.TimeoutExpired):
                    self.assertIn('Calculation timed out (60s).', message)
                self.assertEqual(list(self.directory.iterdir()), [])

    def test_default_source_and_temp_creation_error(self):
        def process(args, **kwargs):
            self.assertEqual(Path(args[2]).read_text(), '#round 3\nx=1')
            return SimpleNamespace(returncode=1, stderr='', stdout='')
        with patch.object(cli.subprocess, 'run', side_effect=process):
            self.assertIn('CLI exit code 1', self.run_cli()[1])
        with patch.object(cli.tempfile, 'NamedTemporaryFile', side_effect=OSError('denied')):
            self.assertIn('Cannot create temp file: denied', self.run_cli()[1])
