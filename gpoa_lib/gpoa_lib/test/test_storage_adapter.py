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

import unittest
from unittest.mock import patch, MagicMock

from gpoa_lib.storage.storage_adapter import StorageAdapter


class StorageAdapterTestCase(unittest.TestCase):

    def _make_control_data(self):
        return {
            'Software/BaseALT/Policies/Control': {
                'sshd-gssapi-auth': '1',
                'writeable': '0',
            }
        }

    def _make_multi_section_data(self):
        return {
            'Software/BaseALT/Policies/Control': {
                'sshd-gssapi-auth': '1',
            },
            'Software/BaseALT/Policies/SystemdUnits': {
                'sshd.service': '1',
                'cups.service': '0',
            },
        }

    def test_from_dict_basic(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entries = adapter.filter_hklm_entries('Software/BaseALT/Policies/Control')
        self.assertEqual(len(entries), 2)

    def test_from_dict_filter_returns_pregdconf(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entries = adapter.filter_hklm_entries('Software/BaseALT/Policies/Control')
        names = [e.valuename for e in entries]
        self.assertIn('sshd-gssapi-auth', names)
        self.assertIn('writeable', names)

    def test_from_dict_get_hklm_entry(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entry = adapter.get_hklm_entry('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.data, '1')

    def test_from_dict_get_hklm_entry_missing(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entry = adapter.get_hklm_entry('Software/BaseALT/Policies/Control/nonexistent')
        self.assertIsNone(entry)

    def test_from_dict_get_key_value(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        value = adapter.get_key_value('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
        self.assertEqual(value, '1')

    def test_from_dict_get_key_value_missing(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        value = adapter.get_key_value('Software/BaseALT/Policies/Control/nonexistent')
        self.assertIsNone(value)

    def test_filter_hkcu_same_as_hklm(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        hklm = adapter.filter_hklm_entries('Software/BaseALT/Policies/Control')
        hkcu = adapter.filter_hkcu_entries('Software/BaseALT/Policies/Control')
        self.assertEqual(len(hklm), len(hkcu))

    def test_filter_entries(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entries = adapter.filter_entries('Software/BaseALT/Policies/Control')
        self.assertEqual(len(entries), 2)

    def test_filter_hklm_with_percent_wildcard(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entries = adapter.filter_hklm_entries('Software/BaseALT/Policies/Control%')
        self.assertEqual(len(entries), 2)

    def test_filter_prefix_only_matching(self):
        data = self._make_multi_section_data()
        adapter = StorageAdapter.from_dict(data)
        entries = adapter.filter_hklm_entries('Software/BaseALT/Policies/SystemdUnits')
        self.assertEqual(len(entries), 2)

    def test_filter_prefix_no_match(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        entries = adapter.filter_hklm_entries('Software/NonExistent/Path')
        self.assertEqual(len(entries), 0)

    def test_init_with_prefix_filter(self):
        data = self._make_multi_section_data()
        adapter = StorageAdapter(data=data, prefix='Software/BaseALT/Policies/Control')
        entries = adapter.filter_hklm_entries('Software/BaseALT/Policies/Control')
        self.assertEqual(len(entries), 1)

    def test_init_with_keys_filter(self):
        data = self._make_multi_section_data()
        adapter = StorageAdapter(data=data, keys=[
            'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
        ])
        entries = adapter.filter_hklm_entries('Software/BaseALT/Policies/Control')
        self.assertEqual(len(entries), 1)

    def test_check_enable_key_true(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        self.assertTrue(adapter.check_enable_key('Software/BaseALT/Policies/Control/sshd-gssapi-auth'))

    def test_check_enable_key_false(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        self.assertFalse(adapter.check_enable_key('Software/BaseALT/Policies/Control/writeable'))

    def test_check_enable_key_missing(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        self.assertFalse(adapter.check_enable_key('Software/BaseALT/Policies/Control/nonexistent'))

    def test_get_entry_no_preg(self):
        data = self._make_control_data()
        adapter = StorageAdapter.from_dict(data)
        value = adapter.get_entry('Software/BaseALT/Policies/Control/sshd-gssapi-auth', preg=False)
        self.assertEqual(value, '1')

    def test_empty_adapter(self):
        adapter = StorageAdapter.from_dict({})
        entries = adapter.filter_hklm_entries('Software/Any/Path')
        self.assertEqual(len(entries), 0)

    def test_integer_value(self):
        data = {'Software/Test': {'count': 42}}
        adapter = StorageAdapter.from_dict(data)
        entry = adapter.get_hklm_entry('Software/Test/count')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.data, 42)
        self.assertEqual(entry.type, 4)

    def test_backslash_key_normalization(self):
        data = {'Software/Test': {'key': 'value'}}
        adapter = StorageAdapter.from_dict(data)
        entry = adapter.get_hklm_entry('Software\\Test\\key')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.data, 'value')

    def test_get_dict_returns_plain_dict(self):
        data = {
            'Software/BaseALT/Policies/Control': {
                'sshd-gssapi-auth': '1',
            }
        }
        adapter = StorageAdapter.from_dict(data)
        result = adapter.get_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['Software/BaseALT/Policies/Control']['sshd-gssapi-auth'], '1')

    def test_get_dict_returns_copy(self):
        data = {'Software/Test': {'key': 'value'}}
        adapter = StorageAdapter.from_dict(data)
        d1 = adapter.get_dict()
        d1['Software/Test']['key'] = 'changed'
        d2 = adapter.get_dict()
        self.assertEqual(d2['Software/Test']['key'], 'value')

    def test_get_dict_empty(self):
        adapter = StorageAdapter.from_dict({})
        self.assertEqual(adapter.get_dict(), {})

    @patch.object(StorageAdapter, '_load_from_db', return_value={})
    def test_from_dconf_db_no_uid_path(self, mock_load):
        StorageAdapter.from_dconf_db('policy')
        mock_load.assert_called_once_with('policy', None)

    @patch.object(StorageAdapter, '_load_from_db', return_value={})
    def test_from_dconf_db_with_uid_path(self, mock_load):
        StorageAdapter.from_dconf_db('policy', uid=1000)
        mock_load.assert_called_once_with('policy', 1000)

    def test_load_from_db_uid_constructs_binary_path(self):
        import inspect
        source = inspect.getsource(StorageAdapter._load_from_db)
        self.assertIn("'policy' + str(uid)", source)
        self.assertNotIn("get_dconf_config_path", source)
        self.assertIn("dconf_dir = '/etc/dconf/db/'", source)
