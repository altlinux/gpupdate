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

import configparser
import sys
import unittest
from unittest.mock import MagicMock, patch, call

_mock_gi = MagicMock()
_mock_gio = MagicMock()
_mock_glib = MagicMock()
_mock_gi.repository.Gio = _mock_gio
_mock_gi.repository.GLib = _mock_glib


def _import_gsettings():
    import importlib
    with patch.dict('sys.modules', {
        'gi': _mock_gi,
        'gi.repository': _mock_gi.repository,
        'gi.repository.Gio': _mock_gio,
        'gi.repository.GLib': _mock_glib,
    }):
        import gpoa_lib.frontend.appliers.gsettings as gs
        importlib.reload(gs)
        return gs


class GlibMapTestCase(unittest.TestCase):

    def test_glib_map_int_type(self):
        gs = _import_gsettings()
        result = gs.glib_map('42', 'i')
        _mock_glib.Variant.assert_called_with('i', 42)

    def test_glib_map_bool_type(self):
        gs = _import_gsettings()
        result = gs.glib_map('1', 'b')
        _mock_glib.Variant.assert_called_with('b', 1)

    def test_glib_map_string_type(self):
        gs = _import_gsettings()
        result = gs.glib_map('hello', 's')
        _mock_glib.Variant.assert_called_with('s', 'hello')


class DconfPathTestCase(unittest.TestCase):

    def test_dconf_path(self):
        gs = _import_gsettings()
        mock_settings = MagicMock()
        mock_settings.get_property.return_value = '/org/test/schema/'
        result = gs.dconf_path(mock_settings, 'some-key')
        self.assertEqual(result, '/org/test/schema/some-key')


class SystemGsettingApplyTestCase(unittest.TestCase):

    def test_apply_adds_section_to_config(self):
        gs = _import_gsettings()
        mock_settings = MagicMock()
        mock_key = MagicMock()
        mock_key.get_type_string.return_value = 's'
        mock_settings.get_value.return_value = mock_key
        _mock_glib.Variant.return_value = 'mocked_variant'

        config = configparser.ConfigParser()
        locks = []

        sg = gs.system_gsetting('org.test.schema', '/test/key', 'value', lock=False)
        sg.apply(mock_settings, config, locks)

        self.assertTrue(config.has_section('org.test.schema'))

    def test_apply_with_lock_appends_to_locks(self):
        gs = _import_gsettings()
        mock_settings = MagicMock()
        mock_key = MagicMock()
        mock_key.get_type_string.return_value = 's'
        mock_settings.get_value.return_value = mock_key
        mock_settings.get_property.return_value = '/org/test/schema/'
        _mock_glib.Variant.return_value = 'mocked_variant'

        config = configparser.ConfigParser()
        locks = []

        sg = gs.system_gsetting('org.test.schema', '/test/key', 'value', lock=True)
        sg.apply(mock_settings, config, locks)

        self.assertEqual(len(locks), 1)
        self.assertEqual(locks[0], '/org/test/schema//test/key')

    def test_apply_with_helper_function(self):
        gs = _import_gsettings()
        mock_settings = MagicMock()
        mock_key = MagicMock()
        mock_key.get_type_string.return_value = 's'
        mock_settings.get_value.return_value = mock_key
        _mock_glib.Variant.return_value = 'mocked_variant'

        config = configparser.ConfigParser()
        locks = []
        helper = MagicMock(return_value='helper_result')

        sg = gs.system_gsetting('org.test.schema', '/test/key', 'value', lock=False, helper_function=helper)
        sg.apply(mock_settings, config, locks)

        helper.assert_called_once_with('org.test.schema', '/test/key', 'value')


class SystemGsettingsAppendTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.gsettings.log')
    def test_append_checks_existing_true(self, mock_log):
        gs = _import_gsettings()
        with patch.object(gs, 'check_existing_gsettings', return_value=True):
            sgs = gs.system_gsettings('/tmp/test.override')
            sgs.append('org.test', '/key', 'val', lock=False, helper=None)

            self.assertEqual(len(sgs.gsettings), 1)

    @patch('gpoa_lib.frontend.appliers.gsettings.log')
    def test_append_checks_existing_false(self, mock_log):
        gs = _import_gsettings()
        with patch.object(gs, 'check_existing_gsettings', return_value=False):
            sgs = gs.system_gsettings('/tmp/test.override')
            sgs.append('org.test', '/key', 'val', lock=False, helper=None)

            self.assertEqual(len(sgs.gsettings), 0)


class UserGsettingApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.gsettings.log')
    def test_user_gsetting_apply_sets_value(self, mock_log):
        gs = _import_gsettings()
        with patch.object(gs, 'check_existing_gsettings', return_value=True):
            mock_settings = MagicMock()
            mock_key = MagicMock()
            mock_key.get_type_string.return_value = 's'
            mock_settings.get_value.return_value = mock_key
            _mock_glib.Variant.return_value = 'mocked_variant'

            _mock_gio.Settings.return_value = mock_settings

            ug = gs.user_gsetting('org.test.schema', '/test/key', 'value')
            ug.apply()

            mock_settings.set_value.assert_called_once_with('/test/key', 'mocked_variant')
