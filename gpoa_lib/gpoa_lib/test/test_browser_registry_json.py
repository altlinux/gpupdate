#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from gpoa_lib.frontend.chromium_applier import chromium_applier
from gpoa_lib.frontend.yandex_browser_applier import yandex_browser_applier
from gpoa_lib.storage.dconf_registry import (
    Dconf_registry, GLib, Gvdb, check_data, load_preg_dconf,
)
from gpoa_lib.util.browser_policy import is_browser_json_value
from gpoa_lib.util.ini_writer import write_ini_sections
from gpoa_lib.util.util import add_prefix_to_keys, clean_data


class BrowserRegistryJsonTest(unittest.TestCase):
    def setUp(self):
        state = patch.multiple(Dconf_registry, global_registry_dict={},
                               _dconf_db={}, _gpt_read_flag=True)
        state.start()
        self.addCleanup(state.stop)
        self.object = {
            '*': {'installation_mode': 'blocked'},
            'abcdefghijklmnopabcdefghijklmnop': {
                'file_url_navigation_allowed': True,
                'override_update_url': False,
                'blocked_install_message': 'L\'utilisateur "Тест" — C:\\dir\\file',
                'nested': [True, False, None, {'value': '\t\n\r"\\'}],
            },
        }
        self.text = json.dumps(self.object, ensure_ascii=False, indent=2)

    def test_preservation_is_scoped_to_browser_json(self):
        for branch in ('Software/Policies/Google/Chrome',
                       'Software/Policies/YandexBrowser'):
            for prefix in ('', 'Previous/', 'Previous/Source/'):
                for suffix in ('', '/Recommended'):
                    section = prefix + branch + suffix
                    self.assertTrue(is_browser_json_value(section, self.text))
                    self.assertTrue(is_browser_json_value(section, '[true, null]'))
                    self.assertEqual(self.text, check_data(self.text, 1, section))
        for branch in ('Software/BaseALT/Policies/Control',
                       'Software/Policies/Google/ChromeOther',
                       'Software/Policies/Google/Chrome/URLBlocklist'):
            self.assertFalse(is_browser_json_value(branch, self.text))
            self.assertEqual(clean_data(self.text), check_data(self.text, 1, branch))
        branch = 'Software/Policies/Google/Chrome'
        self.assertEqual(clean_data(self.text), check_data(self.text, 1))
        self.assertEqual(clean_data(self.text), check_data(self.text, 2, branch))
        for text in ('{broken}', "{'key': True}", 'https://example.org', 'true'):
            self.assertEqual(clean_data(text), check_data(text, 1, branch))

    def test_previous_and_legacy_ini_output(self):
        section = 'Software/Policies/Google/Chrome'
        data = {section: {'ExtensionSettings': self.text},
                'Software/Other': {'text': '"quote"', 'number': 42}}
        previous = add_prefix_to_keys(data)
        self.assertEqual(self.text, previous['Previous/' + section]['ExtensionSettings'])
        self.assertEqual("'quote'", previous['Previous/Software/Other']['text'])
        output = io.StringIO()
        write_ini_sections(output, {'Software/Other': {'text': 'plain', 'number': 42}})
        self.assertEqual('[Software/Other]\ntext = "plain"\nnumber = 42\n\n',
                         output.getvalue())

    def _load_registry(self, cls):
        branch = getattr(cls, f'_{cls.__name__}__registry_branch')
        entries = []
        for suffix in ('', '\\Recommended'):
            path = branch.replace('/', '\\') + suffix
            for name, value, regtype in (
                ('ExtensionSettings', self.text, 1),
                ('ArrayPolicy', '[true, false, null, {"key": "value"}]', 1),
                ('HomepageIsNewTabPage', 1, 4),
                ('DiskCacheSize', 1048576, 4),
                ('HomepageLocation', 'https://example.org', 1),
            ):
                entries.append(SimpleNamespace(keyname=path, valuename=name,
                                               data=value, type=regtype))
            for number in ('1', '2'):
                entries.append(SimpleNamespace(keyname=path + '\\URLBlocklist',
                                               valuename=number, type=1,
                                               data='https://example.org/' + number))
        load_preg_dconf(SimpleNamespace(entries=entries), 'fixture.pol',
                        'Test policy', None, None)
        return branch

    def _assert_browser_output(self, cls, root):
        applier = cls.__new__(cls)
        branch = getattr(cls, f'_{cls.__name__}__registry_branch')
        for scope in ('managed', 'recommended'):
            setattr(applier, f'_{cls.__name__}__{scope}_policies_path', str(root / scope))
        applier.create_dict(Dconf_registry.filter_hklm_entries(branch))
        applier.machine_apply()
        for scope in ('managed', 'recommended'):
            result = json.loads((root / scope / 'policies.json').read_text())
            self.assertEqual(self.object, result['ExtensionSettings'])
            self.assertEqual([True, False, None, {'key': 'value'}], result['ArrayPolicy'])
            self.assertIs(result['HomepageIsNewTabPage'], True)
            self.assertEqual(1048576, result['DiskCacheSize'])
            self.assertEqual('https://example.org', result['HomepageLocation'])
            self.assertEqual(['https://example.org/1', 'https://example.org/2'],
                             result['URLBlocklist'])

    def test_registry_load_to_both_browser_outputs(self):
        for cls in (chromium_applier, yandex_browser_applier):
            with self.subTest(browser=cls.__name__), tempfile.TemporaryDirectory() as tmp:
                Dconf_registry.global_registry_dict = {}
                self._load_registry(cls)
                self._assert_browser_output(cls, Path(tmp))

    @unittest.skipUnless(GLib and Gvdb and shutil.which('dconf'), 'dconf/GVDB unavailable')
    def test_real_dconf_compile_readback_and_browser_output(self):
        for cls in (chromium_applier, yandex_browser_applier):
            with self.subTest(browser=cls.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                Dconf_registry.global_registry_dict = {}
                branch = self._load_registry(cls)
                data = Dconf_registry.global_registry_dict
                data.update(add_prefix_to_keys(data))
                source = root / 'policy.d'
                source.mkdir()
                with (source / 'policy.ini').open('w') as stream:
                    write_ini_sections(stream, data)
                subprocess.run(['dconf', 'compile', str(root / 'policy'), str(source)],
                               check=True, capture_output=True, timeout=15)
                cached = Dconf_registry.get_dictionary_from_dconf_file_db(
                    path_bin=str(root / 'policy'), strict=True)
                for key in (branch, 'Previous/' + branch, branch + '/Recommended'):
                    self.assertEqual(self.text, cached[key]['ExtensionSettings'])
                Dconf_registry.global_registry_dict = cached
                self._assert_browser_output(cls, root)
