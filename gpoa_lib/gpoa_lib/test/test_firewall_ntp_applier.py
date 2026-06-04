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


class FirewallApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.firewall_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check):
        from gpoa_lib.frontend.firewall_applier import firewall_applier
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = []
        storage.get_hklm_entry.return_value = None
        applier = firewall_applier(storage)
        self.assertIs(applier.storage, storage)

    @patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.firewall_applier.log')
    def test_init_loads_firewall_settings(self, mock_log, mock_check):
        from gpoa_lib.frontend.firewall_applier import firewall_applier
        storage = MagicMock()
        expected = [MagicMock(), MagicMock()]
        storage.filter_hklm_entries.return_value = expected
        storage.get_hklm_entry.return_value = None
        applier = firewall_applier(storage)
        storage.filter_hklm_entries.assert_called_once()
        self.assertEqual(applier.firewall_settings, expected)

    @patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.firewall_applier.log')
    def test_init_loads_firewall_enabled_flag(self, mock_log, mock_check):
        from gpoa_lib.frontend.firewall_applier import firewall_applier
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = []
        flag = MagicMock(data='1')
        storage.get_hklm_entry.return_value = flag
        applier = firewall_applier(storage)
        storage.get_hklm_entry.assert_called_once()
        self.assertEqual(applier.firewall_enabled, flag)

    @patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.firewall_applier.log')
    def test_init_module_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.firewall_applier import firewall_applier
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = []
        storage.get_hklm_entry.return_value = None
        applier = firewall_applier(storage)
        self.assertFalse(applier._firewall_applier__module_enabled)


class FirewallApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.firewall_applier.log')
    def _make_applier(self, storage, enabled, mock_log, mock_check):
        mock_check.return_value = enabled
        from gpoa_lib.frontend.firewall_applier import firewall_applier
        return firewall_applier(storage)

    @patch('gpoa_lib.frontend.firewall_applier.os')
    def test_apply_reset_cmd_not_found(self, mock_os):
        mock_os.path.exists.return_value = False
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = []
        storage.get_hklm_entry.return_value = MagicMock(data='1')
        with patch('gpoa_lib.frontend.firewall_applier.log'):
            with patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True):
                from gpoa_lib.frontend.firewall_applier import firewall_applier
                applier = firewall_applier(storage)
        applier.apply()
        mock_os.path.exists.assert_called_once_with('/usr/bin/alterator-net-iptables')

    @patch('gpoa_lib.frontend.firewall_applier.subprocess')
    @patch('gpoa_lib.frontend.firewall_applier.os')
    def test_apply_firewall_enabled_runs_rules(self, mock_os, mock_subprocess):
        mock_os.path.exists.return_value = True
        storage = MagicMock()
        rule_setting = MagicMock(data='v2.10|Action=Allow|Dir=In')
        storage.filter_hklm_entries.return_value = [rule_setting]
        storage.get_hklm_entry.return_value = '1'
        with patch('gpoa_lib.frontend.firewall_applier.log'):
            with patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True):
                from gpoa_lib.frontend.firewall_applier import firewall_applier
                applier = firewall_applier(storage)
        with patch('gpoa_lib.frontend.firewall_applier.log'):
            with patch('gpoa_lib.frontend.firewall_applier.FirewallRule') as MockRule:
                mock_rule_instance = MagicMock()
                MockRule.return_value = mock_rule_instance
                applier.apply()
                MockRule.assert_called_once_with('v2.10|Action=Allow|Dir=In')
                mock_rule_instance.apply.assert_called_once()

    @patch('gpoa_lib.frontend.firewall_applier.subprocess')
    @patch('gpoa_lib.frontend.firewall_applier.os')
    def test_apply_firewall_disabled_resets(self, mock_os, mock_subprocess):
        mock_os.path.exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.__enter__.return_value = mock_proc
        mock_subprocess.Popen.return_value = mock_proc
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = []
        storage.get_hklm_entry.return_value = '0'
        with patch('gpoa_lib.frontend.firewall_applier.log'):
            with patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=True):
                from gpoa_lib.frontend.firewall_applier import firewall_applier
                applier = firewall_applier(storage)
        with patch('gpoa_lib.frontend.firewall_applier.log'):
            applier.apply()
        mock_subprocess.Popen.assert_called_once_with(
            ['/usr/bin/alterator-net-iptables', 'reset']
        )
        mock_proc.wait.assert_called_once_with(timeout=30)

    @patch('gpoa_lib.frontend.firewall_applier.os')
    def test_apply_module_disabled_does_nothing(self, mock_os):
        mock_os.path.exists.return_value = True
        storage = MagicMock()
        storage.filter_hklm_entries.return_value = []
        storage.get_hklm_entry.return_value = MagicMock(data='1')
        with patch('gpoa_lib.frontend.firewall_applier.log'):
            with patch('gpoa_lib.frontend.firewall_applier.check_enabled', return_value=False):
                from gpoa_lib.frontend.firewall_applier import firewall_applier
                applier = firewall_applier(storage)
        applier.apply()
        mock_os.path.exists.assert_called_once()


class NTPApplierInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.ntp_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.ntp_applier.log')
    def test_init_stores_storage(self, mock_log, mock_check):
        from gpoa_lib.frontend.ntp_applier import ntp_applier
        storage = MagicMock()
        applier = ntp_applier(storage)
        self.assertIs(applier.storage, storage)

    @patch('gpoa_lib.frontend.ntp_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.ntp_applier.log')
    def test_init_builds_key_paths(self, mock_log, mock_check):
        from gpoa_lib.frontend.ntp_applier import ntp_applier
        storage = MagicMock()
        applier = ntp_applier(storage)
        self.assertIn('NtpServer', applier.ntp_server_address_key)
        self.assertIn('Type', applier.ntp_server_type)
        self.assertIn('Enabled', applier.ntp_client_enabled)
        self.assertIn('Enabled', applier.ntp_server_enabled)

    @patch('gpoa_lib.frontend.ntp_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.ntp_applier.log')
    def test_init_module_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.ntp_applier import ntp_applier
        storage = MagicMock()
        applier = ntp_applier(storage)
        self.assertFalse(applier._ntp_applier__module_enabled)


class NTPApplierApplyTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.ntp_applier.check_enabled', return_value=False)
    @patch('gpoa_lib.frontend.ntp_applier.log')
    def test_apply_disabled(self, mock_log, mock_check):
        from gpoa_lib.frontend.ntp_applier import ntp_applier
        storage = MagicMock()
        applier = ntp_applier(storage)
        applier.apply()
        storage.get_hklm_entry.assert_not_called()

    @patch('gpoa_lib.frontend.ntp_applier.check_enabled', return_value=True)
    @patch('gpoa_lib.frontend.ntp_applier.log')
    def test_apply_enabled_calls_run(self, mock_log, mock_check):
        from gpoa_lib.frontend.ntp_applier import ntp_applier
        storage = MagicMock()
        storage.get_hklm_entry.return_value = None
        applier = ntp_applier(storage)
        applier.run()
        self.assertEqual(storage.get_hklm_entry.call_count, 4)
