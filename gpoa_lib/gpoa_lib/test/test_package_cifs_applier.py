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

import unittest
from unittest.mock import MagicMock, patch, PropertyMock


class PackageApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.package_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.package_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check):
        from gpoa_lib.frontend.package_applier import package_applier
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.count.return_value = 0
        applier = package_applier(storage)
        self.assertIs(applier.storage, storage)

    @patch('gpoa_lib.frontend.package_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.package_applier.log')
    def test_init_builds_command(self, mock_log, mock_check):
        from gpoa_lib.frontend.package_applier import package_applier
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.count.return_value = 0
        applier = package_applier(storage)
        self.assertEqual(applier.fulcmd[0], '/usr/libexec/gpupdate/pkcon_runner')
        self.assertIn('--loglevel', applier.fulcmd)

    @patch('gpoa_lib.frontend.package_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.package_applier.log')
    def test_init_loads_package_settings(self, mock_log, mock_check):
        from gpoa_lib.frontend.package_applier import package_applier
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.count.return_value = 0
        applier = package_applier(storage)
        self.assertEqual(storage.filter_hklm_entries.call_count, 3)


class PackageApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.package_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.package_applier.log')
    def test_apply_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.package_applier import package_applier
        storage = MagicMock()
        install_setting = MagicMock()
        install_setting.count.return_value = 0
        remove_setting = MagicMock()
        remove_setting.count.return_value = 0
        storage.filter_hklm_entries.side_effect = [install_setting, remove_setting, MagicMock()]
        applier = package_applier(storage)
        with patch('gpoa_lib.frontend.package_applier.subprocess') as mock_sp:
            applier.apply()
            mock_sp.check_call.assert_not_called()
            mock_sp.Popen.assert_not_called()

    @patch('gpoa_lib.frontend.package_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.package_applier.log')
    def test_apply_enabled_sync(self, mock_log, mock_check):
        from gpoa_lib.frontend.package_applier import package_applier
        storage = MagicMock()
        install_setting = MagicMock()
        install_setting.count.return_value = 1
        install_setting.__iter__ = lambda self: iter([])
        remove_setting = MagicMock()
        remove_setting.count.return_value = 0
        remove_setting.__iter__ = lambda self: iter([])
        sync_setting = MagicMock()
        sync_setting.__iter__ = lambda self: iter([MagicMock(data=True)])
        storage.filter_hklm_entries.side_effect = [install_setting, remove_setting, sync_setting]
        applier = package_applier(storage)
        with patch('gpoa_lib.frontend.package_applier.subprocess') as mock_sp:
            applier.apply()
            mock_sp.check_call.assert_called_once()

    @patch('gpoa_lib.frontend.package_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.package_applier.log')
    def test_apply_enabled_async(self, mock_log, mock_check):
        from gpoa_lib.frontend.package_applier import package_applier
        storage = MagicMock()
        install_setting = MagicMock()
        install_setting.count.return_value = 1
        install_setting.__iter__ = lambda self: iter([])
        remove_setting = MagicMock()
        remove_setting.count.return_value = 0
        remove_setting.__iter__ = lambda self: iter([])
        sync_setting = MagicMock()
        sync_setting.__iter__ = lambda self: iter([MagicMock(data=False)])
        storage.filter_hklm_entries.side_effect = [install_setting, remove_setting, sync_setting]
        applier = package_applier(storage)
        with patch('gpoa_lib.frontend.package_applier.subprocess') as mock_sp:
            mock_proc = MagicMock()
            mock_proc.__enter__.return_value = mock_proc
            mock_sp.Popen.return_value = mock_proc
            applier.apply()
            mock_sp.Popen.assert_called_once()
            mock_proc.wait.assert_called_once_with(timeout=300)


class CIFSApplierHelperTestCase(unittest.TestCase):

    def test_remove_chars_before_colon_with_colon(self):
        from gpoa_lib.frontend.cifs_applier import remove_chars_before_colon
        self.assertEqual(remove_chars_before_colon('abc:def'), 'def')

    def test_remove_chars_before_colon_no_colon(self):
        from gpoa_lib.frontend.cifs_applier import remove_chars_before_colon
        self.assertEqual(remove_chars_before_colon('abcdef'), 'abcdef')

    def test_remove_escaped_quotes(self):
        from gpoa_lib.frontend.cifs_applier import remove_escaped_quotes
        self.assertEqual(remove_escaped_quotes('"hello"'), 'hello')
        self.assertEqual(remove_escaped_quotes("'world'"), 'world')
        self.assertEqual(remove_escaped_quotes("both\"'"), 'both')


class CIFSApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.cifs_applier.cifs_applier_user')
    @patch('gpoa_lib.frontend.cifs_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.cifs_applier.log')
    def test_init_creates_user_applier(self, mock_log, mock_check, mock_user_applier):
        from gpoa_lib.frontend.cifs_applier import cifs_applier
        storage = MagicMock()
        with patch.object(cifs_applier, 'clear_directory_auto_dir'):
            applier = cifs_applier(storage)
        mock_user_applier.assert_called_once_with(storage, None)

    @patch('gpoa_lib.frontend.cifs_applier.cifs_applier_user')
    @patch('gpoa_lib.frontend.cifs_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.cifs_applier.log')
    def test_init_module_disabled(self, mock_log, mock_check, mock_user_applier):
        from gpoa_lib.frontend.cifs_applier import cifs_applier
        storage = MagicMock()
        with patch.object(cifs_applier, 'clear_directory_auto_dir'):
            applier = cifs_applier(storage)
        self.assertFalse(applier._cifs_applier__module_enabled)


class CIFSApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.cifs_applier.cifs_applier_user')
    @patch('gpoa_lib.frontend.cifs_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.cifs_applier.log')
    def test_apply_disabled(self, mock_log, mock_check, mock_user_applier):
        from gpoa_lib.frontend.cifs_applier import cifs_applier
        storage = MagicMock()
        with patch.object(cifs_applier, 'clear_directory_auto_dir'):
            applier = cifs_applier(storage)
        mock_cifs_user = MagicMock()
        applier.applier_cifs = mock_cifs_user
        applier.apply()
        mock_cifs_user._admin_context_apply.assert_not_called()

    @patch('gpoa_lib.frontend.cifs_applier.cifs_applier_user')
    @patch('gpoa_lib.frontend.cifs_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.cifs_applier.log')
    def test_apply_enabled_calls_admin_context(self, mock_log, mock_check, mock_user_applier):
        from gpoa_lib.frontend.cifs_applier import cifs_applier
        storage = MagicMock()
        with patch.object(cifs_applier, 'clear_directory_auto_dir'):
            applier = cifs_applier(storage)
        mock_cifs_user = MagicMock()
        applier.applier_cifs = mock_cifs_user
        applier.apply()
        mock_cifs_user._admin_context_apply.assert_called_once()
