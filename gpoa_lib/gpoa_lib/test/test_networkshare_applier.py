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


class NetworkshareApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        self.assertIs(applier.storage, storage)

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_init_with_username(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage, username='testuser')
        self.assertEqual(applier.username, 'testuser')
        storage.get_networkshare.assert_called_once_with('testuser')

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_init_without_username(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        self.assertIsNone(applier.username)
        storage.get_networkshare.assert_called_once_with(None)

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_init_module_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        self.assertFalse(applier._networkshare_applier__module_enabled)


class NetworkshareApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_apply_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        with patch.object(applier, 'run') as mock_run:
            applier.apply()
            mock_run.assert_not_called()

    @patch('gpoa_lib.frontend.networkshare_applier.Networkshare')
    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_apply_enabled_processes_shares(self, mock_log, mock_check, mock_ns_cls):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        share1 = MagicMock()
        share1.disabled = False
        share2 = MagicMock()
        share2.disabled = False
        storage.get_networkshare.return_value = [share1, share2]
        applier = networkshare_applier(storage)
        applier.run()
        self.assertEqual(mock_ns_cls.call_count, 2)

    @patch('gpoa_lib.frontend.networkshare_applier.Networkshare')
    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_run_skips_disabled_shares(self, mock_log, mock_check, mock_ns_cls):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        share1 = MagicMock()
        share1.disabled = False
        share2 = MagicMock()
        share2.disabled = True
        storage.get_networkshare.return_value = [share1, share2]
        applier = networkshare_applier(storage)
        applier.run()
        mock_ns_cls.assert_called_once_with(share1, None)

    @patch('gpoa_lib.frontend.networkshare_applier.Networkshare')
    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_run_empty_shares(self, mock_log, mock_check, mock_ns_cls):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        applier.run()
        mock_ns_cls.assert_not_called()


class NetworkshareApplierUserContextTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_user_context_apply_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        with patch.object(applier, 'run') as mock_run:
            applier.user_context_apply()
            mock_run.assert_not_called()

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_user_context_apply_enabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        with patch.object(applier, 'run') as mock_run:
            applier.user_context_apply()
            mock_run.assert_called_once()

    @patch('gpoa_lib.frontend.networkshare_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.networkshare_applier.log')
    def test_admin_context_apply_does_nothing(self, mock_log, mock_check):
        from gpoa_lib.frontend.networkshare_applier import networkshare_applier
        storage = MagicMock()
        storage.get_networkshare.return_value = []
        applier = networkshare_applier(storage)
        result = applier.admin_context_apply()
        self.assertIsNone(result)
