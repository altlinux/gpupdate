import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gpt.scriptsini import Script, read_scripts
from gpoa_lib.frontend.scripts_applier import install_script


class LocalScriptsTest(unittest.TestCase):
    def setUp(self):
        for name in ('logon', 'logoff', 'startup', 'shutdown'):
            counter = patch.object(Script, f'_Script__{name}_counter', 0)
            counter.start()
            self.addCleanup(counter.stop)

    def test_absolute_paths_keep_case_and_are_installed_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / 'Local Script.sh'
            source.write_text('#!/bin/sh\nprintf local\n')
            for action in ('Startup', 'Shutdown', 'Logon', 'Logoff'):
                with self.subTest(action=action):
                    script = Script(action, str(base / 'GPT'), str(source))
                    script.set_args('--option value')
                    self.assertEqual(script.path, str(source))
                    self.assertEqual(script.number, 0)
                    dest = base / 'cache' / action.upper()
                    mode = '700' if action in ('Startup', 'Shutdown') else '755'
                    install_script(script, str(dest), mode)
                    installed = dest / '00000_Local Script.sh'
                    self.assertEqual(installed.read_bytes(), source.read_bytes())
                    self.assertEqual(installed.stat().st_mode & 0o777, int(mode, 8))
                    self.assertEqual(Path(str(installed) + '.arg', 'arg').read_text(), '--option value')

    def test_ini_order_with_mixed_local_and_gpt_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'STARTUP').mkdir()
            (base / 'STARTUP' / 'DOMAIN.SH').write_text('domain')
            local = base / 'local.sh'
            local.write_text('local')
            ini = base / 'scripts.ini'
            ini.write_text(f'[Startup]\n1CmdLine=domain.sh\n1Parameters=domain arg\n'
                           f'0CmdLine={local}\n0Parameters=local arg\n', encoding='utf-16')
            scripts = read_scripts(str(ini)).get_startup_scripts()
            self.assertEqual([s.path for s in scripts], [str(local), str(base / 'STARTUP' / 'DOMAIN.SH')])
            self.assertEqual([s.args for s in scripts], ['local arg', 'domain arg'])

    def test_missing_local_script_keeps_existing_skip_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Script('Startup', directory, str(Path(directory, 'missing.sh')))
            self.assertIsNone(script.number)
            destination = Path(directory, 'out')
            install_script(script, str(destination), '700')
            self.assertEqual(list(destination.iterdir()), [])

    def test_unc_is_not_interpreted_as_a_local_absolute_path(self):
        with patch('gpt.scriptsini.os.path.isfile', return_value=False):
            script = Script('Startup', '/cache/GPO', '//server/share/test.sh')
            self.assertEqual(script.path, '/cache/GPO/STARTUP/TEST.SH')
