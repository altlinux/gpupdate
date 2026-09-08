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
import unittest
from unittest.mock import patch, mock_open, MagicMock
from types import SimpleNamespace

from gpoa_lib.frontend.appliers.polkit import polkit


class PolkitOutfileTestCase(unittest.TestCase):

    def test_outfile_with_username(self):
        p = polkit('myrule', {'User': 'testuser'}, username='testuser')
        expected = os.path.join('/etc/polkit-1/rules.d', 'myrule.testuser.rules')
        self.assertEqual(p.outfile, expected)

    def test_outfile_without_username(self):
        p = polkit('myrule', {'User': 'testuser'})
        expected = os.path.join('/etc/polkit-1/rules.d', 'myrule.rules')
        self.assertEqual(p.outfile, expected)


class PolkitIsEmptyTestCase(unittest.TestCase):

    def test_all_empty(self):
        p = polkit('myrule', {'User': 'u', 'key1': '', 'key2': None})
        self.assertTrue(p._is_empty())

    def test_has_values(self):
        p = polkit('myrule', {'User': 'u', 'key1': '', 'key2': 'value'})
        self.assertFalse(p._is_empty())


class PolkitGenerateTestCase(unittest.TestCase):

    @patch('builtins.open', mock_open())
    @patch('gpoa_lib.frontend.appliers.polkit.jinja2.Environment')
    def test_generate_creates_file(self, mock_env_cls):
        mock_template = MagicMock()
        mock_template.render.return_value = 'rendered content'
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_env_cls.return_value = mock_env

        p = polkit('myrule', {'User': 'u', 'action': 'allow'})
        p.__class__._polkit__template_environment = mock_env
        p.generate()

        mock_env.get_template.assert_called_once()
        mock_template.render.assert_called_once()

    @patch('os.path.isfile', return_value=True)
    @patch('os.remove')
    def test_generate_removes_file_when_empty(self, mock_remove, mock_isfile):
        p = polkit('myrule', {'User': 'u', 'key1': ''})
        p.generate()
        mock_remove.assert_called_once_with(p.outfile)


class PolkitErrorTestCase(unittest.TestCase):

    @patch('builtins.open', mock_open())
    @patch('gpoa_lib.frontend.appliers.polkit.jinja2.Environment')
    def test_generate_handles_template_exception(self, mock_env_cls):
        mock_env = MagicMock()
        mock_env.get_template.side_effect = Exception('template error')
        mock_env_cls.return_value = mock_env

        p = polkit('myrule', {'User': 'u', 'action': 'allow'})
        p.__class__._polkit__template_environment = mock_env
        p.generate()

        mock_env.get_template.assert_called_once()


def _entry(valuename, data):
    return SimpleNamespace(valuename=valuename, data=data)


def _make_storage(polkit_entries, deny_all=None):
    storage = MagicMock()
    polkit_result = MagicMock()
    polkit_result.__iter__ = lambda s: iter(polkit_entries)
    storage.filter_hkcu_entries.return_value = polkit_result
    storage.filter_hklm_entries.return_value = polkit_result
    deny_result = MagicMock()
    deny_result.first.return_value = deny_all
    storage.filter_hkcu_entries.side_effect = (
        lambda flt: polkit_result
        if 'Polkit' in flt else deny_result)
    storage.get_key_value.return_value = None
    return storage


class PolkitMachineDedupTestCase(unittest.TestCase):

    def _applier(self, entries):
        from gpoa_lib.frontend.polkit_applier import polkit_applier
        storage = _make_storage(entries)
        storage.filter_hklm_entries.side_effect = None
        polkit_res = MagicMock()
        polkit_res.__iter__ = lambda s: iter(entries)
        locks_res = MagicMock()
        locks_res.__iter__ = lambda s: iter([])
        storage.filter_hklm_entries.return_value = polkit_res
        storage.filter_hklm_entries.side_effect = (
            lambda flt: locks_res if 'Locks' in flt else polkit_res)
        return polkit_applier(storage)

    def test_conflicting_verdicts_deduplicated(self):
        entries = [
            _entry('org.test.action', 'Yes'),
            _entry('org.test.action', 'No'),
        ]
        appl = self._applier(entries)
        vars_map = appl.policies[1].args
        self.assertIn('org.test.action', vars_map['No'])
        self.assertNotIn('org.test.action', vars_map['Yes'])

    def test_last_merged_verdict_wins(self):
        entries = [
            _entry('org.test.action', 'No'),
            _entry('org.test.action', 'Yes'),
        ]
        appl = self._applier(entries)
        vars_map = appl.policies[1].args
        self.assertIn('org.test.action', vars_map['Yes'])
        self.assertNotIn('org.test.action', vars_map['No'])

    def test_unknown_verdict_skipped(self):
        entries = [
            _entry('org.test.action', 'Bogus'),
        ]
        appl = self._applier(entries)
        vars_map = appl.policies[1].args
        for verdict_list in vars_map.values():
            self.assertNotIn('org.test.action', verdict_list)


class PolkitUserMachinePrecedenceTestCase(unittest.TestCase):

    def _applier(self, entries, machine_dict, deny_all=None):
        from gpoa_lib.frontend.polkit_applier import polkit_applier_user
        from gpoa_lib.storage.dconf_registry import Dconf_registry
        storage = _make_storage(entries, deny_all=deny_all)
        with patch.object(Dconf_registry, 'get_dictionary_from_dconf_file_db',
                          return_value=machine_dict):
            return polkit_applier_user(storage, 'testuser')

    def test_machine_defined_action_excluded(self):
        entries = [
            _entry('org.test.machine-action', 'Yes'),
            _entry('org.test.user-action', 'No'),
        ]
        machine_dict = {
            'Software/BaseALT/Policies/Polkit': {
                'org.test.machine-action': 'No',
            }
        }
        appl = self._applier(entries, machine_dict)
        vars_map = appl.policies[1].args
        self.assertNotIn('org.test.machine-action', vars_map['Yes'])
        self.assertIn('org.test.user-action', vars_map['No'])

    def test_all_actions_machine_defined_yields_empty_file(self):
        entries = [
            _entry('org.test.machine-action', 'Yes'),
        ]
        machine_dict = {
            'Software/BaseALT/Policies/Polkit': {
                'org.test.machine-action': 'No',
            }
        }
        appl = self._applier(entries, machine_dict)
        self.assertTrue(appl.policies[1]._is_empty())

    def test_machine_deny_all_suppresses_user_deny_all(self):
        entries = []
        machine_dict = {
            'Software/Policies/Microsoft/Windows/RemovableStorageDevices': {
                'Deny_All': '1',
            }
        }
        deny_all = _entry('Deny_All', '1')
        appl = self._applier(entries, machine_dict, deny_all=deny_all)
        self.assertEqual(appl.policies[0].args['Deny_All'], 0)
