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
from unittest.mock import MagicMock, patch


class ScriptsApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.scripts_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.scripts_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check):
        from gpoa_lib.frontend.scripts_applier import scripts_applier
        storage = MagicMock()
        storage.get_scripts.return_value = []
        applier = scripts_applier(storage)
        self.assertIs(applier.storage, storage)

    @patch('gpoa_lib.frontend.scripts_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.scripts_applier.log')
    def test_init_loads_startup_and_shutdown(self, mock_log, mock_check):
        from gpoa_lib.frontend.scripts_applier import scripts_applier
        storage = MagicMock()
        storage.get_scripts.return_value = ['script1']
        applier = scripts_applier(storage)
        storage.get_scripts.assert_any_call('STARTUP')
        storage.get_scripts.assert_any_call('SHUTDOWN')
        self.assertEqual(storage.get_scripts.call_count, 2)


class ScriptsApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.scripts_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.scripts_applier.log')
    def test_apply_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.scripts_applier import scripts_applier
        storage = MagicMock()
        storage.get_scripts.return_value = []
        applier = scripts_applier(storage)
        with patch.object(applier, 'cleaning_cache'):
            with patch.object(applier, 'run') as mock_run:
                applier.apply()
                mock_run.assert_not_called()

    @patch('gpoa_lib.frontend.scripts_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.scripts_applier.log')
    def test_apply_enabled_calls_run(self, mock_log, mock_check):
        from gpoa_lib.frontend.scripts_applier import scripts_applier
        storage = MagicMock()
        storage.get_scripts.return_value = []
        applier = scripts_applier(storage)
        with patch.object(applier, 'cleaning_cache'):
            with patch.object(applier, 'run') as mock_run:
                applier.apply()
                mock_run.assert_called_once()

    @patch('gpoa_lib.frontend.scripts_applier.remove_dir_tree')
    @patch('gpoa_lib.frontend.scripts_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.scripts_applier.log')
    def test_cleaning_cache_success(self, mock_log, mock_check, mock_remove):
        from gpoa_lib.frontend.scripts_applier import scripts_applier
        storage = MagicMock()
        storage.get_scripts.return_value = []
        applier = scripts_applier(storage)
        applier.cleaning_cache()
        mock_remove.assert_called_once()

    @patch('gpoa_lib.frontend.scripts_applier.remove_dir_tree', side_effect=FileNotFoundError)
    @patch('gpoa_lib.frontend.scripts_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.scripts_applier.log')
    def test_cleaning_cache_not_found(self, mock_log, mock_check, mock_remove):
        from gpoa_lib.frontend.scripts_applier import scripts_applier
        storage = MagicMock()
        storage.get_scripts.return_value = []
        applier = scripts_applier(storage)
        applier.cleaning_cache()
        mock_remove.assert_called_once()


class IniApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.ini_applier.GppStateManager')
    @patch('gpoa_lib.frontend.ini_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.ini_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check, mock_gpp):
        from gpoa_lib.frontend.ini_applier import ini_applier
        storage = MagicMock()
        storage.get_ini.return_value = []
        applier = ini_applier(storage)
        self.assertIs(applier.storage, storage)

    @patch('gpoa_lib.frontend.ini_applier.GppStateManager')
    @patch('gpoa_lib.frontend.ini_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.ini_applier.log')
    def test_init_loads_ini_files(self, mock_log, mock_check, mock_gpp):
        from gpoa_lib.frontend.ini_applier import ini_applier
        storage = MagicMock()
        storage.get_ini.return_value = ['ini1']
        applier = ini_applier(storage)
        storage.get_ini.assert_called_once()
        self.assertEqual(applier.inifiles_info, ['ini1'])

    @patch('gpoa_lib.frontend.ini_applier.GppStateManager')
    @patch('gpoa_lib.frontend.ini_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.ini_applier.log')
    def test_init_module_disabled(self, mock_log, mock_check, mock_gpp):
        from gpoa_lib.frontend.ini_applier import ini_applier
        storage = MagicMock()
        storage.get_ini.return_value = []
        applier = ini_applier(storage)
        self.assertFalse(applier._ini_applier__module_enabled)


class IniApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.ini_applier.GppStateManager')
    @patch('gpoa_lib.frontend.ini_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.ini_applier.log')
    def test_apply_disabled(self, mock_log, mock_check, mock_gpp):
        from gpoa_lib.frontend.ini_applier import ini_applier
        storage = MagicMock()
        storage.get_ini.return_value = []
        applier = ini_applier(storage)
        with patch.object(applier, 'run') as mock_run:
            applier.apply()
            mock_run.assert_not_called()

    @patch('gpoa_lib.frontend.ini_applier.GppStateManager')
    @patch('gpoa_lib.frontend.ini_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.ini_applier.log')
    def test_apply_enabled_calls_run(self, mock_log, mock_check, mock_gpp):
        from gpoa_lib.frontend.ini_applier import ini_applier
        storage = MagicMock()
        storage.get_ini.return_value = []
        applier = ini_applier(storage)
        with patch.object(applier, 'run') as mock_run:
            applier.apply()
            mock_run.assert_called_once()


class FileApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.file_applier.GppStateManager')
    @patch('gpoa_lib.frontend.file_applier.Execution_check')
    @patch('gpoa_lib.frontend.file_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.file_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check, mock_exe, mock_gpp):
        from gpoa_lib.frontend.file_applier import file_applier
        storage = MagicMock()
        storage.get_files.return_value = []
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.first.return_value = None
        file_cache = MagicMock()
        applier = file_applier(storage, file_cache)
        self.assertIs(applier.storage, storage)
        self.assertIs(applier.file_cache, file_cache)

    @patch('gpoa_lib.frontend.file_applier.GppStateManager')
    @patch('gpoa_lib.frontend.file_applier.Execution_check')
    @patch('gpoa_lib.frontend.file_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.file_applier.log')
    def test_init_loads_files(self, mock_log, mock_check, mock_exe, mock_gpp):
        from gpoa_lib.frontend.file_applier import file_applier
        storage = MagicMock()
        storage.get_files.return_value = ['file1', 'file2']
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.first.return_value = None
        file_cache = MagicMock()
        applier = file_applier(storage, file_cache)
        storage.get_files.assert_called_once()
        self.assertEqual(applier.files, ['file1', 'file2'])


class FileApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.file_applier.GppStateManager')
    @patch('gpoa_lib.frontend.file_applier.Execution_check')
    @patch('gpoa_lib.frontend.file_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.file_applier.log')
    def test_apply_disabled(self, mock_log, mock_check, mock_exe, mock_gpp):
        from gpoa_lib.frontend.file_applier import file_applier
        storage = MagicMock()
        storage.get_files.return_value = []
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.first.return_value = None
        file_cache = MagicMock()
        applier = file_applier(storage, file_cache)
        with patch.object(applier, 'run') as mock_run:
            applier.apply()
            mock_run.assert_not_called()

    @patch('gpoa_lib.frontend.file_applier.GppStateManager')
    @patch('gpoa_lib.frontend.file_applier.Execution_check')
    @patch('gpoa_lib.frontend.file_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.file_applier.log')
    def test_apply_enabled_calls_run(self, mock_log, mock_check, mock_exe, mock_gpp):
        from gpoa_lib.frontend.file_applier import file_applier
        storage = MagicMock()
        storage.get_files.return_value = []
        storage.filter_hklm_entries.return_value = MagicMock()
        storage.filter_hklm_entries.return_value.first.return_value = None
        file_cache = MagicMock()
        applier = file_applier(storage, file_cache)
        with patch.object(applier, 'run') as mock_run:
            applier.apply()
            mock_run.assert_called_once()
