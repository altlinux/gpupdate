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
from unittest.mock import MagicMock, patch

from gpoa_lib.frontend.appliers.envvar import Envvar


def _make_envvar_obj(action, name, value):
    obj = MagicMock()
    obj.action = action
    obj.name = name
    obj.value = value
    return obj


class EnvvarPathTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_root_user_selects_system_path(self, mock_homedir):
        envvar = Envvar([], username='root')
        self.assertEqual(envvar.envvar_file_path, '/etc/gpupdate/environment')
        mock_homedir.assert_not_called()

    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_non_root_user_selects_home_path(self, mock_homedir):
        mock_homedir.return_value = '/home/testuser'
        envvar = Envvar([], username='testuser')
        self.assertEqual(envvar.envvar_file_path, '/home/testuser/.gpupdate_environment')
        mock_homedir.assert_called_once_with('testuser')


class ClearEnvvarFileTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('gpoa_lib.frontend.appliers.envvar.log')
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_clear_creates_empty_file(self, mock_homedir, mock_log):
        mock_homedir.return_value = self.tmpdir
        env_file = os.path.join(self.tmpdir, '.gpupdate_environment')
        with open(env_file, 'w') as f:
            f.write('MYVAR DEFAULT="value"\n')
        Envvar.clear_envvar_file('testuser')
        with open(env_file, 'r') as f:
            self.assertEqual(f.read(), '')


class EnvvarActTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.env_file = os.path.join(self.tmpdir, '.gpupdate_environment')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read_env_file(self):
        with open(self.env_file, 'r') as f:
            return f.read()

    def _write_env_file(self, content):
        with open(self.env_file, 'w') as f:
            f.write(content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_create_new_var(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        envvar_obj = _make_envvar_obj('C', 'MYVAR', 'myvalue')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertIn('MYVAR', content)
        self.assertIn('myvalue', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_create_existing_var_no_change(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        self._write_env_file('MYVAR DEFAULT="oldvalue"\n')
        envvar_obj = _make_envvar_obj('C', 'MYVAR', 'newvalue')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertIn('oldvalue', content)
        self.assertNotIn('newvalue', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_update_existing_var(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        self._write_env_file('MYVAR DEFAULT="oldvalue"\n')
        envvar_obj = _make_envvar_obj('U', 'MYVAR', 'newvalue')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertNotIn('oldvalue', content)
        self.assertIn('newvalue', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_update_new_var_creates(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        envvar_obj = _make_envvar_obj('U', 'MYVAR', 'myvalue')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertIn('MYVAR', content)
        self.assertIn('myvalue', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_delete_existing_var(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        self._write_env_file('MYVAR DEFAULT="somevalue"\n')
        envvar_obj = _make_envvar_obj('D', 'MYVAR', 'ignored')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertNotIn('MYVAR', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_delete_missing_var_no_change(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        self._write_env_file('OTHER DEFAULT="value"\n')
        envvar_obj = _make_envvar_obj('D', 'MYVAR', 'ignored')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertIn('OTHER', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_replace_existing_var(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        self._write_env_file('MYVAR DEFAULT="oldvalue"\n')
        envvar_obj = _make_envvar_obj('R', 'MYVAR', 'newvalue')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertNotIn('oldvalue', content)
        self.assertIn('newvalue', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_replace_new_var_creates(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        envvar_obj = _make_envvar_obj('R', 'MYVAR', 'myvalue')
        envvar = Envvar([envvar_obj], username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertIn('MYVAR', content)
        self.assertIn('myvalue', content)

    @patch('gpoa_lib.frontend.appliers.envvar.expand_windows_var', side_effect=lambda v, u: v)
    @patch('gpoa_lib.frontend.appliers.envvar.get_homedir')
    def test_multiple_envvars(self, mock_homedir, mock_expand):
        mock_homedir.return_value = self.tmpdir
        objs = [
            _make_envvar_obj('C', 'VAR1', 'val1'),
            _make_envvar_obj('C', 'VAR2', 'val2'),
        ]
        envvar = Envvar(objs, username='testuser')
        envvar.act()
        content = self._read_env_file()
        self.assertIn('VAR1', content)
        self.assertIn('val1', content)
        self.assertIn('VAR2', content)
        self.assertIn('val2', content)
