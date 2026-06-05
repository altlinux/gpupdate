#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gpoa_lib.frontend.appliers.ini_file import Ini_file, check_path


class MockConfigObj(dict):
    def write(self):
        pass


def _make_ini_obj(action='C', path='/some/path', section='sec', prop='key', value='val'):
    obj = MagicMock()
    obj.path = path
    obj.action = action
    obj.get_original_value = lambda k: {'section': section, 'property': prop, 'value': value}.get(k)
    return obj


class CheckPathTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_existing_file_returns_path(self):
        test_file = os.path.join(self.tmpdir, 'test.ini')
        Path(test_file).touch()
        result = check_path(test_file)
        self.assertEqual(result, Path(test_file))

    def test_parent_dir_exists_returns_path(self):
        test_file = os.path.join(self.tmpdir, 'nonexistent.ini')
        result = check_path(test_file)
        self.assertEqual(result, Path(test_file))

    def test_nonexistent_returns_false(self):
        result = check_path('/nonexistent_dir/nonexistent_file')
        self.assertFalse(result)

    @patch('gpoa_lib.frontend.appliers.ini_file.get_homedir')
    def test_with_username_joins_homedir(self, mock_homedir):
        mock_homedir.return_value = self.tmpdir
        test_file = os.path.join(self.tmpdir, 'test.ini')
        Path(test_file).touch()
        result = check_path('test.ini', username='testuser')
        self.assertEqual(result, Path(test_file))


class IniFileTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.tmpdir, 'test.ini')
        Path(self.test_file).touch()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_ini_with_mocks(self, ini_obj, config_data=None, **kwargs):
        config = MockConfigObj(config_data or {})
        patches = [
            patch('gpoa_lib.frontend.appliers.ini_file.log'),
            patch('gpoa_lib.frontend.appliers.ini_file.GpoaConfigObj', return_value=config),
            patch('gpoa_lib.frontend.appliers.ini_file.check_path', return_value=Path(self.test_file)),
            patch('gpoa_lib.frontend.appliers.ini_file.expand_windows_var', return_value=self.test_file),
        ]
        for p in patches:
            p.start()
        try:
            ini = Ini_file(ini_obj, **kwargs)
        finally:
            for p in patches:
                p.stop()
        return ini, config

    def test_bool_false_for_invalid_path(self):
        with patch('gpoa_lib.frontend.appliers.ini_file.log'), \
             patch('gpoa_lib.frontend.appliers.ini_file.expand_windows_var', return_value='/bad/path'), \
             patch('gpoa_lib.frontend.appliers.ini_file.check_path', return_value=False):
            ini = Ini_file(_make_ini_obj())
            self.assertFalse(bool(ini))

    def test_bool_true_for_valid_path(self):
        ini, _ = self._make_ini_with_mocks(_make_ini_obj())
        self.assertTrue(bool(ini))

    def test_create_action(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='C', section='sec', prop='key', value='val'))
        self.assertEqual(config.get('sec', {}).get('key'), 'val')
        self.assertTrue(ini.modified)

    def test_update_action(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='U', section='sec', prop='key', value='newval'))
        self.assertEqual(config.get('sec', {}).get('key'), 'newval')
        self.assertTrue(ini.modified)

    def test_delete_action(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='D', section='sec', prop='key', value='val'),
            config_data={'sec': {'key': 'val'}})
        self.assertNotIn('key', config.get('sec', {}))
        self.assertTrue(ini.modified)

    def test_delete_no_key_removes_section(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='D', section='sec', prop='', value=''),
            config_data={'sec': {'key': 'val'}})
        self.assertNotIn('sec', config)
        self.assertTrue(ini.modified)

    def test_skip_if_matches_skips(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='C', section='sec', prop='key', value='val'),
            config_data={'sec': {'key': 'val'}},
            skip_if_matches=True)
        self.assertFalse(ini.modified)

    def test_skip_if_matches_does_not_skip_when_value_differs(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='C', section='sec', prop='key', value='newval'),
            config_data={'sec': {'key': 'oldval'}},
            skip_if_matches=True)
        self.assertTrue(ini.modified)

    def test_allow_empty_sections_root_level(self):
        ini, config = self._make_ini_with_mocks(
            _make_ini_obj(action='C', section='', prop='key', value='val'),
            allow_empty_sections=True)
        self.assertEqual(config.get('key'), 'val')
        self.assertTrue(ini.modified)

    def test_is_empty_section(self):
        ini, _ = self._make_ini_with_mocks(_make_ini_obj(section=''))
        self.assertTrue(ini._is_empty_section())
        ini2, _ = self._make_ini_with_mocks(_make_ini_obj(section='mysec'))
        self.assertFalse(ini2._is_empty_section())
